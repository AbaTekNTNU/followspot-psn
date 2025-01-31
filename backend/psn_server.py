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


# Internal state is a list of TrackerData objects
@dataclass
class TrackerData:
    id: int
    x: float
    y: float
    z: float

    # Convert from internal coordinates to actual scene coordinates
    # Internal representation is float values from 0 to 1 for x and y
    # Thus we need to know the max size and aspect ratio of the scene
    # x is the width of the scene, y is the depth, z is the height
    def pic_to_scene_coords_3d(x, y, z) -> tuple[float, float, float]:
        scene_width = 8.0
        scene_depth = 6.3
        scene_height = 0.8
        person_height = 1.5

        x_val = x * scene_width - (scene_width / 2)
        y_val = y * scene_depth
        z_val = scene_height + person_height
        return x_val, y_val, z_val

    def to_tracker(self):
        tracker = psn.Tracker(self.id, f"Tracker {self.id}")
        x, y, z = self.pic_to_scene_coords_3d(self.x, self.y, self.z)
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


async def update_all_clients(app: web.Application, ws: web.WebSocketResponse = None):
    for ws_send in app["ws_clients"]:
        if ws_send == ws:
            continue
        await ws_send.send_str(trackers_to_json(app))


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
                await update_all_clients(request.app, ws)

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


def filter_handler(address, *args) -> None:
    tracker_id = int(address.split("/")[-1])
    x, y, z = args
    logging.debug(f"id: {tracker_id} | x: {x}, y: {y}, z: {z}")

async def receive_osc_data(app):
    dispatcher = Dispatcher()
    dispatcher.map("/Tracker*", filter_handler)
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
        app["trackers"][i] = TrackerData(i, 0, 0, 0)

    app.on_shutdown.append(on_shutdown)
    app.cleanup_ctx.append(background_tasks)
    app.cleanup_ctx.append(receive_osc_data)

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    app = create_app()
    web.run_app(app, host=IP, port=WEB_SERVER_PORT)
