import os

from celery import Celery

import database

from datetime import datetime

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
celery.conf.result_backend = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379"
)


@celery.task(name="process_payload")
def process_payload(
    identifier: str,
    data: bytes,
    packet_type: int,
    packet_size: int,
    packet_direction: int,
    zone_id: int,
    timestamp: datetime,
    client_version: str,
):
    with database.get_cached_session() as session:
        submitter = database.get_submitter_by_identifier(session, identifier)
        capture_session = database.update_or_create_capture_session(session, submitter, client_version)
        packet_direction = database.PacketDirection(packet_direction)

        database.create_packet_data(
            session,
            capture_session,
            data,
            packet_type,
            packet_size,
            packet_direction,
            zone_id,
            timestamp,
        )
