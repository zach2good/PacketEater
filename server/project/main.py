import os

from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_utils.tasks import repeat_every
from pydantic import BaseModel
from typing import Optional

import database
import worker
import utils

import random

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


class RequestPayload(BaseModel):
    name: str
    zone_id: int
    version: Optional[str] = "Unknown"
    payload: str  # Base64 encoded data
    timestamp: float
    direction: int
    origin: int


submitter_thin_map = {}

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
    with database.get_cached_db_session() as db:
        packet_count = database.get_packet_count(db)
        submitter_count = database.get_submitter_count(db)
        packets_bytes = database.get_packet_size_bytes(db)
        packets_bytes_str = utils.human_readable_size_str(packets_bytes)
        plural_packets = "s" if packet_count > 1 else ""
        plural_submitters = "s" if submitter_count > 1 else ""
        random_valediction = random.choice(exclamations)

        stat_str = f"I have eaten { packet_count } packet{plural_packets} from { submitter_count } submitter{plural_submitters} ({ packets_bytes_str }), {random_valediction}!"

        if submitter_count == 0 or packet_count == 0:
            stat_str = "No packets have been submitted yet! :("

        get_uint16 = lambda offset: packet.data[offset] | packet.data[offset + 1] << 8

        event_packet_string = ""
        for packet in (
            db.query(database.PacketData)
            .filter(database.PacketData.type == 0x34)
            .limit(1)
            .all()
        ):
            type = packet.data[0] & 0xFF | packet.data[1] & 0x01
            size = packet.data[1] & 0xFE

            npcLocalID = get_uint16(0x28)
            zone = get_uint16(0x2A)
            long_id = 0x01000000 | (zone << 0x0C) | npcLocalID

            event_packet_string += f"Packet type: {type}, size: {size}, npcLocalID: {npcLocalID}, zone: {zone}, long_id: {long_id}\n"

        return templates.TemplateResponse(
            "home.html",
            context={
                "request": request,
                "stat_str": stat_str,
                "event_packet_string": event_packet_string,
            },
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
def on_startup_and_periodic_update() -> None:
    with database.get_cached_db_session() as db:
        global submitter_thin_map
        submitter_thin_map = database.get_submitter_thin_map(db)
        database.combine_and_prune_capture_sessions_by_start_time(db)


@app.put("/upload")
@app.post("/upload")
async def home(request: Request, request_payload: RequestPayload):
    # !!! This is the only time we handle the IP address !!!
    ip_address = request.client.host
    is_local = (
        ip_address.startswith("127.")
        or ip_address.startswith("192.")
        or ip_address.startswith("172.")
    )
    identifier = utils.generate_identifier(ip_address)
    # !!! This is the only time we handle the IP address !!!

    with database.get_cached_db_session() as db:
        global submitter_thin_map
        if identifier not in submitter_thin_map:
            print(
                f"Creating submitter information for new identifier: {identifier[:8]}..."
            )
            identifier = utils.generate_identifier(ip_address)
            submitter = database.create_submitter(db, identifier)

            if is_local:
                submitter.whitelisted = True
                db.add(submitter)
                db.commit()
                print(f"Whitelisted local submitter: {identifier[:8]}...")

            submitter_thin_map[identifier] = database.get_submitter_thin(submitter)

        submitter = submitter_thin_map[identifier]

        if submitter["banned"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Submitter is banned."
            )

        if not submitter["whitelisted"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Submitter is not whitelisted.",
            )

        # TODO: Check/create capture sessions here, before we get into the worker(s) - they will fight and create multiple
        #     : capture sessions that we will then neeed to combine.

        # TODO: Once we have the capture session information here, we should send it in the JSONResponse so the client can
        #     : display the submitter identifier and capture session identifier to the user.
        capture_session_identifier = 1

        # TODO: Give the user some way of requesting that their current capture session be closed and a new one started.

        try:
            worker.process_payload.delay(
                identifier,
                request_payload.dict(),  # Convert Pydantic model to a dictionary for transport
            )

            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "status": "queued",
                    "submitter_identifier": identifier,
                    "capture_session_identifier": capture_session_identifier,
                    "should_log": True,
                },
            )
        except Exception as e:
            print(f"Error processing payload: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing payload.",
            )
