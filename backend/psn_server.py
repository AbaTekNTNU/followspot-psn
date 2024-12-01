import psn
import time
import socket
import json
from aiohttp import web
import logging
from dataclasses import dataclass, make_dataclass

PSN_DEFAULT_UDP_PORT = 56565
PSN_DEFAULT_UDP_MCAST_ADDRESS = "236.10.10.10"
PORT = 8000
IP = "0.0.0.0"
NUM_TRACKERS = 3

@dataclass
class TrackerData:
    id: int
    x: float
    y: float


trackers = {}


for i in NUM_TRACKERS:
    trackers[i] = psn.Tracker(i, f"Tracker {i}")
    trackers[i].set_pos(psn.Float3(0, 0, 0))

def update_trackers(tracker_data_json: str):
    global trackers
    tracker_data = [TrackerData(**data) for data in json.loads(tracker_data_json)]

    for tracker in tracker_data:
        trackers[tracker.id].set_pos(psn.Float3(tracker.x, tracker.y, 0))

def trackers_to_json():
    return json.dumps([{"id": tracker.id, "x": tracker.pos.x, "y": tracker.pos.y} for tracker in trackers.values()])

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def get_time_ms():
    return int(time.time() * 1000)


START_TIME = get_time_ms()


def get_elapsed_time_ms():
    return get_time_ms() - START_TIME


def pic_to_scene_coords(x, y):
    return x / 200, y / 200


def send_positions():
    encoder = psn.Encoder("Server 1")

    packets = encoder.encode_data(trackers, get_elapsed_time_ms())
    for packet in packets:
        sock.sendto(packet, (PSN_DEFAULT_UDP_MCAST_ADDRESS, PSN_DEFAULT_UDP_PORT))


async def handle_websocket(request):
    ws = web.WebSocketResponse()
    logging.debug("Websocket connection starting")
    await ws.prepare(request)
    logging.debug("Websocket connection ready")

    ws.send_str(trackers_to_json())

    try:
        async for msg in ws:
            logging.debug(f"Websocket data: {msg}")
            if msg.type == web.WSMsgType.TEXT:
                logging.debug("Received message: %s" % msg.data)
                update_trackers(msg.data)
                send_positions()

            elif msg.type == web.WSMsgType.ERROR:
                logging.error("ws connection closed with exception %s" % ws.exception())
                print("ws connection closed with exception %s" % ws.exception())
    except Exception as e:
        logging.error(f"Websocket exception: {e}")

    finally:
        logging.debug("Websocket connection closing")
        await ws.close()

    return ws




async def handle_root(request):
    return web.FileResponse("./static/index.html")


def create_app():
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_static("/", "./static")
    app.router.add_get("/ws", handle_websocket)
    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    web.run_app(create_app(), host=IP, port=PORT)
