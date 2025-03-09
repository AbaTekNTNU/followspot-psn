import asyncio
import json
import logging
import os
import socket
import time
import weakref
from dataclasses import dataclass

import psn
from aiohttp import WSCloseCode, web
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer

PSN_DEFAULT_UDP_PORT = os.getenv("PSN_DEFAULT_UDP_PORT", 56565)
PSN_DEFAULT_UDP_MCAST_ADDRESS = os.getenv(
    "PSN_DEFAULT_UDP_MCAST_ADDRESS", "236.10.10.10"
)
WEB_SERVER_PORT = int(os.getenv("WEB_SERVER_PORT", 8000))
IP = "0.0.0.0"
OSC_SERVER_PORT = int(os.getenv("OSC_SERVER_PORT", 9000))
NUM_TRACKERS = int(os.getenv("NUM_TRACKERS", 3))


class SceneDimensions:
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    z_min: float
    z_max: float

    dimension_name: str

    dimension_map = {
        "scene_only": (-13 / 2, 13 / 2, 0, 6.3, 0, 4),
        "full_arena": (-13 / 2, 13 / 2, -9.7, 6.3, 0, 4),
    }

    def __init__(self):
        self.set_scene_only_dimensions()

    def _set_new_dimensions(self, x_min, x_max, y_min, y_max, z_min, z_max):
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self.z_min = z_min
        self.z_max = z_max

    def set_scene_only_dimensions(self):
        self._set_new_dimensions(*SceneDimensions.dimension_map["scene_only"])
        self.dimension_name = "scene_only"

    def set_full_arena_dimensions(self):
        self._set_new_dimensions(*SceneDimensions.dimension_map["full_arena"])
        self.dimension_name = "full_arena"


START_POSITION_INTERNAL = (0.5, 0.5, 2)


def map_range(
    value: float, in_min: float, in_max: float, out_min: float, out_max: float
) -> float:
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


# Internal state is a list of TrackerData objects
@dataclass
class TrackerData:
    id: int
    x: float
    y: float
    z: float

    @staticmethod
    def internal_to_scene_coords_3d(
        x: float, y: float, z: float, dim: SceneDimensions
    ) -> tuple[float, float, float]:
        """
        Convert internal coordinates to scene coordinates

        Internal coordinates are in the range [0, 1] for x and y with (0,0) at the top left
        Scene coordinates are in the range [X_MIN, X_MAX] for x and [Y_MIN, YMAX] for y
        """
        x_val = map_range(x, 0, 1, dim.x_min, dim.x_max)
        y_val = map_range(y, 0, 1, dim.y_max, dim.y_min)  # Invert y axis
        z_val = z

        return x_val, y_val, z_val

    @staticmethod
    def scene_to_internal_coords_3d(
        x: float, y: float, z: float, dim: SceneDimensions
    ) -> tuple[float, float, float]:
        x_val = map_range(x, dim.x_min, dim.x_max, 0, 1)
        y_val = map_range(y, dim.y_max, dim.y_min, 0, 1)  # Invert y axis
        z_val = z

        return x_val, y_val, z_val

    def to_tracker(self, dim: SceneDimensions) -> psn.Tracker:
        tracker = psn.Tracker(self.id, f"Tracker {self.id}")
        x, y, z = TrackerData.internal_to_scene_coords_3d(self.x, self.y, self.z, dim)
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


async def update_all_other_clients(
    app: web.Application, ws: web.WebSocketResponse = None
):
    for ws_send in app["ws_clients"]:
        if ws_send == ws:
            continue
        await ws_send.send_str(trackers_to_json(app))


async def update_all_clients(app: web.Application):
    for ws in app["ws_clients"]:
        await ws.send_str(trackers_to_json(app))


async def update_all_clients_bg(app: web.Application):
    for ws in app["ws_clients"]:
        await ws.send_str(json.dumps({"refresh": True}))


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


async def handle_background_image(request):
    if request.app["scene_dimensions"].dimension_name == "full_arena":
        return web.FileResponse("./static/scene_and_crowd.png")
    elif request.app["scene_dimensions"].dimension_name == "scene_only":
        return web.FileResponse("./static/scene_only.png")
    return web.Response(text="Incorrect server scende dimension state", status=500)


async def handle_set_mode(request):
    try:
        data = request.data = await request.json()
        mode = data["mode"]
        if mode == "full_arena":
            request.app["scene_dimensions"].set_full_arena_dimensions()
        elif mode == "scene_only":
            request.app["scene_dimensions"].set_scene_only_dimensions()
        else:
            return web.Response(text="Invalid mode", status=400)

        await update_all_clients_bg(request.app)

        return web.Response(text="OK")
    except Exception as e:
        return web.Response(text=f"Error: {e}", status=400)


async def handlet_get_mode(request):
    return web.json_response({"mode": request.app["scene_dimensions"].dimension_name})


async def broadcast_psn_data(app):
    encoder = psn.Encoder("Server 1")
    while True:
        trackers = {}
        for tracker_data in app["trackers"].values():
            trackers[tracker_data.id] = tracker_data.to_tracker(app["scene_dimensions"])
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


def osc_tracker_updater(address, fixed_args, *args) -> None:
    app = fixed_args[0]
    tracker_id = int(address.split("/")[-1])
    x, y, z = TrackerData.scene_to_internal_coords_3d(*args, app["scene_dimensions"])
    logging.debug(f"OSC received: id: {tracker_id} at {x}, {y}, {z}")
    tracker = TrackerData(tracker_id, x, y, z)
    app["trackers"][tracker_id] = tracker

    asyncio.ensure_future(update_all_clients(app))

async def handle_add_tracker(request):
    # Add tracker with id from request
    try:
        trackers = request.app["trackers"]
        request_data = await request.json()
        tracker_id = request_data["id"]
        if tracker_id in trackers:
            return web.Response(text="Tracker already exists", status=400)

        trackers[tracker_id] = TrackerData(tracker_id, *START_POSITION_INTERNAL)
        await update_all_clients(request.app)

        return web.Response(text="OK", status=200)
    except Exception as e:
        return web.Response(text=f"Error: {e}", status=400)



async def handler_delete_tracker(request):
    # Delete tracker with id from request
    try:
        trackers = request.app["trackers"]
        request_data = await request.json()
        tracker_id = request_data["id"]
        if tracker_id not in trackers:
            return web.Response(text="Tracker does not exist", status=400)

        del trackers[tracker_id]
        await update_all_clients(request.app)

        return web.Response(text="OK", status=200)
    except Exception as e:
        return web.Response(text=f"Error: {e}", status=400)

async def receive_osc_data(app):
    dispatcher = Dispatcher()
    dispatcher.map("/Tracker*", osc_tracker_updater, app)
    server = AsyncIOOSCUDPServer(
        (IP, OSC_SERVER_PORT), dispatcher, asyncio.get_event_loop()
    )
    transport, protocol = await server.create_serve_endpoint()
    app["osc_transport"] = transport
    yield
    await transport.close()


def create_app():
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/ws", handle_websocket)
    app.router.add_get("/background_image", handle_background_image)

    app.router.add_post("/mode", handle_set_mode)
    app.router.add_get("/mode", handlet_get_mode)

    app.router.add_post("/tracker", handle_add_tracker)
    app.router.add_delete("/tracker", handler_delete_tracker)

    app.router.add_static("/", "./static")

    # Setup app state
    # All app state needs to be mutable as changing state variables directly while running is not supported
    app["ws_clients"] = weakref.WeakSet()
    app["trackers"] = {}
    app["sock"] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    app["scene_dimensions"] = SceneDimensions()

    for i in range(NUM_TRACKERS):
        app["trackers"][i] = TrackerData(i, *START_POSITION_INTERNAL)

    app.on_shutdown.append(on_shutdown)
    app.cleanup_ctx.append(background_tasks)
    app.cleanup_ctx.append(receive_osc_data)

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    app = create_app()
    web.run_app(app, host=IP, port=WEB_SERVER_PORT)
