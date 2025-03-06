import asyncio
import json
import logging
import socket
import time
import weakref
from dataclasses import dataclass

import psn
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.dispatcher import Dispatcher
from aiohttp import web, WSCloseCode

PSN_DEFAULT_UDP_PORT = 56565
PSN_DEFAULT_UDP_MCAST_ADDRESS = "236.10.10.10"
WEB_SERVER_PORT = 8000
IP = "0.0.0.0"
OSC_SERVER_PORT = 6969
NUM_TRACKERS = 3

FULL_SCENE_WIDTH = 13.46
INNER_SCENE_WIDTH = 8.0

ONLY_SCENE_DEPTH = 6.3
FULL_ARENA_DEPTH = 16.0

SCENE_WIDTH = FULL_SCENE_WIDTH
SCENE_DEPTH = ONLY_SCENE_DEPTH

X_MIN = -SCENE_WIDTH / 2
X_MAX = SCENE_WIDTH / 2
Y_MIN = 0.0
Y_MAX = SCENE_DEPTH
Z_MIN = 0.0
Z_MAX = 4.0

START_POSITION = (0.5, 0.5, 2)

def map_range(value: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


# Internal state is a list of TrackerData objects
@dataclass
class TrackerData:
    id: int
    x: float
    y: float
    z: float

    @staticmethod
    def internal_to_scene_coords_3d(x: float, y: float, z: float) -> tuple[float, float, float]:
        """
        Convert internal coordinates to scene coordinates

        Internal coordinates are in the range [0, 1] for x and y with (0,0) at the top left
        Scene coordinates are in the range [X_MIN, X_MAX] for x and [Y_MIN, YMAX] for y
        """
        x_val = map_range(x, 0, 1, X_MIN, X_MAX)
        y_val = map_range(y, 0, 1, Y_MAX, Y_MIN) # Invert y axis
        z_val = z

        return x_val, y_val, z_val

    @staticmethod
    def scene_to_internal_coords_3d(x: float, y: float, z: float) -> tuple[float, float, float]:
        x_val = map_range(x, X_MIN, X_MAX, 0, 1)
        y_val = map_range(y, Y_MAX, Y_MIN, 0, 1) # Invert y axis
        z_val = z

        return x_val, y_val, z_val

    def to_tracker(self) -> psn.Tracker:
        tracker = psn.Tracker(self.id, f"Tracker {self.id}")
        x, y, z = TrackerData.internal_to_scene_coords_3d(self.x, self.y, self.z)
        logging.debug(f"Tracker {self.id} at {x}, {y}, {z}")
        tracker.set_pos(psn.Float3(x, y, z))
        return tracker


def update_tracker(tracker_data_json: str, app: web.Application):
    tracker = TrackerData(**json.loads(tracker_data_json))
    app["trackers"][tracker.id] = tracker


def trackers_to_json(app: web.Application):
    return json.dumps([tracker.__dict__ for tracker in app["trackers"].values()])


def get_time_ms():
    return int(time.time() * 1000)


START_TIME = get_time_ms()


def get_elapsed_time_ms():
    return get_time_ms() - START_TIME


async def update_all_other_clients(app: web.Application, ws: web.WebSocketResponse = None):
    for ws_send in app["ws_clients"]:
        if ws_send == ws:
            continue
        await ws_send.send_str(trackers_to_json(app))

async def update_all_clients(app: web.Application):
    for ws in app["ws_clients"]:
        await ws.send_str(trackers_to_json(app))


async def handle_websocket(request):
    ws = web.WebSocketResponse()
    logging.debug("Websocket connection starting")
    await ws.prepare(request)
    logging.debug("Websocket connection ready")

    request.app["ws_clients"].add(ws)

    await ws.send_str(trackers_to_json(request.app))

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                # Each message is a single tracker object
                logging.debug(f"Received ws update: {msg.data}")
                update_tracker(msg.data, request.app)
                await update_all_other_clients(request.app, ws)

            elif msg.type == web.WSMsgType.ERROR:
                logging.error("ws connection closed with exception %s" % ws.exception())

    except Exception as e:
        logging.error(f"Websocket exception: {e}")

    finally:
        logging.debug("Websocket connection closing")
        request.app["ws_clients"].discard(ws)

    return ws

async def on_shutdown(app):
    for ws in set(app["ws_clients"]):
        await ws.close(code=WSCloseCode.GOING_AWAY, message="Server shutdown")


async def handle_root(request):
    return web.FileResponse("./static/index.html")


async def broadcast_psn_data(app):
    encoder = psn.Encoder("Server 1")
    while True:
        trackers = {}
        for tracker_data in app["trackers"].values():
            trackers[tracker_data.id] = tracker_data.to_tracker()
        packets = encoder.encode_data(trackers, get_elapsed_time_ms())
        for packet in packets:
            app["sock"].sendto(
                packet, (PSN_DEFAULT_UDP_MCAST_ADDRESS, PSN_DEFAULT_UDP_PORT)
            )
        await asyncio.sleep(0.033)  # ~30fps


async def background_tasks(app: web.Application):
    app["broadcast_psn_data"] = asyncio.create_task(broadcast_psn_data(app))
    yield
    app["broadcast_psn_data"].cancel()
    await app["broadcast_psn_data"]


def filter_handler(address, fixed_args, *args) -> None:
    tracker_id = int(address.split("/")[-1])
    x, y, z = TrackerData.scene_to_internal_coords_3d(*args)
    logging.debug(f"OSC received: id: {tracker_id} at {x}, {y}, {z}")
    app = fixed_args[0]
    tracker = TrackerData(tracker_id, x, y, z)
    app["trackers"][tracker_id] = tracker

    asyncio.ensure_future(update_all_clients(app))


async def receive_osc_data(app):
    dispatcher = Dispatcher()
    dispatcher.map("/Tracker*", filter_handler, app)
    server = AsyncIOOSCUDPServer((IP, OSC_SERVER_PORT), dispatcher, asyncio.get_event_loop())
    transport, protocol = await server.create_serve_endpoint()
    app["osc_transport"] = transport
    yield
    await transport.close()


def create_app():
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/ws", handle_websocket)
    app.router.add_static("/", "./static")

    # Setup app state
    app["ws_clients"] = weakref.WeakSet()
    app["trackers"] = {}
    app["sock"] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    for i in range(NUM_TRACKERS):
        app["trackers"][i] = TrackerData(i, *START_POSITION)

    app.on_shutdown.append(on_shutdown)
    app.cleanup_ctx.append(background_tasks)
    app.cleanup_ctx.append(receive_osc_data)

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    web.run_app(app, host=IP, port=WEB_SERVER_PORT)
