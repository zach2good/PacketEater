import os

from celery import Celery

import database
import packets

import base64
from datetime import datetime

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
celery.conf.result_backend = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379"
)


@celery.task(name="process_payload")
def process_payload(
    identifier: str,
    request_payload: dict,
):
    with database.get_cached_db_session() as db:
        data = base64.b64decode(request_payload["payload"])

        packet_type, packet_size = packets.get_packet_type_and_size(data)

        packet_direction = packets.PacketDirection(request_payload["direction"])

        zone_id = int(request_payload["zone_id"])

        timestamp = datetime.fromtimestamp(float(request_payload["timestamp"]) / 1000)

        client_version = request_payload["version"]

        origin = request_payload["origin"] # TODO: Hook this up

        submitter = database.get_submitter_by_identifier(db, identifier)
        capture_session = database.update_or_create_capture_session(
            db, submitter, client_version
        )

        database.create_packet_data(
            db,
            capture_session,
            data,
            packet_type,
            packet_size,
            packet_direction,
            zone_id,
            timestamp,
        )
