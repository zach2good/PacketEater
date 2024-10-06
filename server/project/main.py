import os

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_utils.tasks import repeat_every

import database
import worker
import utils

import json
import base64
import random
from datetime import datetime

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

submitter_map = {}

exclamations = [
    "yum",
    "delicious",
    "tasty",
    "scrumptious",
    "nice",
    "delectable",
    "cool",
    "awesome",
    "neat",
    "rad",
    "fantastic",
    "amazing",
    "wonderful",
    "superb",
    "excellent",
    "terrific",
    "outstanding",
    "marvelous",
    "fabulous",
    "splendid",
    "magnificent",
    "phenomenal",
    "remarkable",
    "incredible",
    "unbelievable",
    "extraordinary",
    "spectacular",
    "stupendous",
    "egad",
    "golly",
    "gosh",
    "gee",
    "wow",
    "holy cow",
    "holy moly",
    "holy guacamole",
    "holy smokes",
    "phwoar",
    "blimey",
    "crikey",
    "cor",
    "flippin' heck",
    "chunky" "funky",
    "groovy",
    "far out",
    "hooray",
    "ohohohoho",
]


@app.get("/", response_class=RedirectResponse)
def redirect_to_packets():
    return RedirectResponse(url="/packets")


@app.get("/packets")
def home(request: Request):
    with database.get_cached_session() as session:
        packet_count = database.get_packet_count(session)
        submitter_count = database.get_submitter_count(session)
        packets_bytes = database.get_packet_size_bytes(session)
        packets_bytes_str = utils.human_readable_size_str(packets_bytes)
        plural_packets = "s" if packet_count > 1 else ""
        plural_submitters = "s" if submitter_count > 1 else ""
        random_valediction = random.choice(exclamations)

        stat_str = f"I have eaten { packet_count } packet{plural_packets} from { submitter_count } submitter{plural_submitters} ({ packets_bytes_str }), {random_valediction}!"

        if submitter_count == 0 or packet_count == 0:
            stat_str = "No packets have been submitted yet! :("


        get_uint16 = lambda offset: packet.data[offset] | packet.data[offset + 1] << 8

        event_packet_string = ""
        for packet in session.query(database.PacketData).filter(database.PacketData.type == 0x34).limit(1).all():
            type = packet.data[0] & 0xFF | packet.data[1] & 0x01
            size = packet.data[1] & 0xFE

            npcLocalID = get_uint16(0x28)
            zone       = get_uint16(0x2A)
            long_id    = 0x01000000 | (zone << 0x0C) | npcLocalID

            event_packet_string += f"Packet type: {type}, size: {size}, npcLocalID: {npcLocalID}, zone: {zone}, long_id: {long_id}\n"

        return templates.TemplateResponse(
            "home.html", context={"request": request, "stat_str": stat_str, "event_packet_string": event_packet_string}
        )


@app.on_event("startup")
def on_startup():
    print("Starting up...")

    # DEBUG: Drop and recreate tables
    # print("DEBUG: Dropping and recreating tables...")
    # database.drop_tables()
    # database.create_tables()


@app.on_event("startup")
@repeat_every(seconds=60)
def refresh_submitter_map() -> None:
    with database.get_cached_session() as session:
        global submitter_map
        submitter_map = database.get_submitter_map(session)
        database.combine_capture_sessions_by_start_time(session)


@app.put("/upload")
@app.post("/upload")
async def home(request: Request):
    # !!! This is the only time we handle the IP address !!!
    ip_address = request.client.host
    is_local = (
        ip_address.startswith("127.")
        or ip_address.startswith("192.")
        or ip_address.startswith("172.")
    )
    identifier = utils.generate_identifier(ip_address)
    # !!! This is the only time we handle the IP address !!!

    with database.get_cached_session() as session:
        if identifier not in submitter_map:
            print(
                f"Creating submitter information for new identifier: {identifier[:8]}..."
            )
            identifier = utils.generate_identifier(ip_address)
            submitter = database.create_submitter(session, identifier)

            if is_local:
                submitter.whitelisted = True
                session.add(submitter)
                session.commit()
                print(f"Whitelisted local submitter: {identifier[:8]}...")

            submitter_map[identifier] = submitter

        submitter = session.merge(submitter_map.get(identifier))

        if submitter.banned:
            return JSONResponse(
                content={"status": "banned"},
                status_code=status.HTTP_403_FORBIDDEN,
            )

        if not submitter.whitelisted:
            return JSONResponse(
                content={"status": "not yet whitelisted"},
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # TODO: Check capture session status here, before we get into the worker(s)

        try:
            # TODO: This isn't ideal. Do this in a more FastAPI way.
            json_bytes = await request.body()

            # TODO: All of this processing should be happening on the worker
            json_obj = json.loads(json_bytes)

            data = base64.b64decode(json_obj["payload"])

            # Of the first 2 bytes, the first 9-bits of the payload are the packet type
            packet_type = data[0] & 0xFF | data[1] & 0x01

            # the remaining 7-bits are the packet size
            packet_size = data[1] & 0xFE

            packet_direction = database.PacketDirection(json_obj["direction"])

            zone_id = int(json_obj["zoneId"])

            timestamp = datetime.fromtimestamp(float(json_obj["timestamp"]) / 1000)

            client_version = json_obj.get("version", "Unknown")

            worker.process_payload.delay(
                identifier, data, packet_type, packet_size, packet_direction, zone_id, timestamp, client_version
            )
            return JSONResponse(
                content={"status": "queued"},
                status_code=status.HTTP_202_ACCEPTED,
            )
        except Exception as e:
            print(f"Error processing payload: {e}")
            return JSONResponse(
                content={"status": "error"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
