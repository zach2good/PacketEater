import os
import datetime
import typing

from datetime import datetime, timedelta
from contextlib import contextmanager

import packets

from sqlalchemy import (
    Column as Col,
    Integer,
    String,
    Boolean,
    LargeBinary,
    DateTime,
    ForeignKey,
    Enum,
)
from sqlalchemy import create_engine
from sqlalchemy.types import VARCHAR
from sqlalchemy.orm import relationship, load_only
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.sql import func


def get_database_url():
    user = os.environ.get("MYSQL_USER", "default_user")
    password = os.environ.get("MYSQL_PASSWORD", "default_user")
    host = os.environ.get("MYSQL_HOST", "mysql")
    port = os.environ.get("MYSQL_PORT", "3306")
    database = os.environ.get("MYSQL_DATABASE", "default_database")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"


engine = create_engine(
    get_database_url(),
    pool_pre_ping=True,
    pool_size=16,
    max_overflow=8,
    pool_recycle=300,
    pool_timeout=30,
)

SessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)
DatabaseSession = typing.NewType("DatabaseSession", Session)

Base = declarative_base()


@contextmanager
def get_cached_db_session():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()


#
# Column Helpers
#


def Column(*args, **kwargs):
    kwargs.setdefault("nullable", False)
    return Col(*args, **kwargs)


class HashColumn(Integer):

    def bind_expression(self, bindvalue):
        return func.HEX(bindvalue)

    def column_expression(self, col):
        return func.UNHEX(col)


#
# Database Models
#


class Submitter(Base):
    __tablename__ = "submitters"

    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String(255), unique=True, index=True)
    whitelisted = Column(Boolean, default=False)
    banned = Column(Boolean, default=False)

    # A submitter has many sessions, cascade delete when submitter is deleted
    sessions = relationship(
        "CaptureSession", back_populates="submitter", cascade="all, delete-orphan"
    )


class CaptureSession(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to the submitter this session belongs to
    submitter_id = Column(Integer, ForeignKey("submitters.id"), nullable=False)

    # Relationship to Submitter
    submitter = relationship("Submitter", back_populates="sessions")

    # A session has many packets, cascade delete when session is deleted
    packets = relationship(
        "PacketData", back_populates="session", cascade="all, delete-orphan"
    )

    start_time = Column(DateTime, default=datetime.now)
    last_update_time = Column(DateTime, default=datetime.now)
    client_version = Column(String(255), nullable=False)


class PacketData(Base):
    __tablename__ = "packet_data"

    id = Column(Integer, primary_key=True, index=True)
    data = Column(LargeBinary)
    timestamp = Column(DateTime)
    type = Column(Integer)  # Extracted from data
    size = Column(Integer)  # Extracted from data / actual size of data
    direction = Column(Enum(packets.PacketDirection))
    zone_id = Column(Integer)

    # Foreign key to the session this packet belongs to
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)

    # Define the relationship to CaptureSession
    session = relationship("CaptureSession", back_populates="packets")


#
# Table Management
#


def create_tables():
    Base.metadata.create_all(bind=engine)


def drop_tables():
    Base.metadata.drop_all(bind=engine)


#
# Getters
#


def get_submitter_thin(submitter_orm_obj: Submitter):
    return {
        "id": submitter_orm_obj.id,
        "identifier": submitter_orm_obj.identifier,
        "whitelisted": submitter_orm_obj.whitelisted,
        "banned": submitter_orm_obj.banned,
    }


def get_submitter_thin_map(db: DatabaseSession):
    submitter_map = {}

    # Query only the columns you care about and exclude relationships
    submitters = (
        db.query(Submitter)
        .options(
            load_only(
                Submitter.id,
                Submitter.identifier,
                Submitter.whitelisted,
                Submitter.banned,
            )
        )
        .all()
    )

    # Convert to dictionary
    for submitter_orm_obj in submitters:
        submitter_map[submitter_orm_obj.identifier] = get_submitter_thin(
            submitter_orm_obj
        )

    return submitter_map


def get_submitter_count(db: DatabaseSession) -> int:
    return db.query(Submitter).count()


def get_packet_count(db: DatabaseSession) -> int:
    return db.query(PacketData).count()


def get_packet_size_bytes(db: DatabaseSession) -> int:
    return db.query(func.sum(PacketData.size)).scalar()


def get_submitter_by_identifier(db: DatabaseSession, identifier: str) -> Submitter:
    return db.query(Submitter).filter(Submitter.identifier == identifier).first()


#
# Create <x>
#


def create_submitter(db: DatabaseSession, identifier: str) -> Submitter:
    submitter = Submitter(identifier=identifier)
    db.add(submitter)
    db.commit()
    return submitter


def create_capture_session(
    db: DatabaseSession, submitter: Submitter, client_version: str
) -> CaptureSession:
    print(f"Creating capture session for: {submitter.identifier[:8]}...")
    capture_session = CaptureSession(submitter=submitter)
    capture_session.client_version = client_version
    db.add(capture_session)
    db.commit()
    return capture_session


def create_packet_data(
    db: DatabaseSession,
    capture_session: CaptureSession,
    data: bytes,
    packet_type: int,
    packet_size: int,
    packet_direction: packets.PacketDirection,
    zone_id: int,
    timestamp: datetime,
):
    packet = PacketData(
        data=data,
        session=capture_session,
        type=packet_type,
        size=packet_size,
        direction=packet_direction,
        zone_id=zone_id,
        timestamp=timestamp,
    )

    db.add(packet)
    db.commit()

    return packet


#
# Session Management
#


# TODO: Add some caching here so we're not so reliant on constantly querying the database
def update_or_create_capture_session(
    db: DatabaseSession, submitter: Submitter, client_version: str
) -> CaptureSession:
    capture_session = (
        db.query(CaptureSession)
        .filter(CaptureSession.submitter_id == submitter.id)
        .order_by(CaptureSession.start_time.desc())
        .first()
    )

    if capture_session is None:
        capture_session = create_capture_session(db, submitter, client_version)
    elif capture_session.last_update_time < datetime.now() - timedelta(
        seconds=10
    ):  # TODO: Is 10 seconds a good threshold?
        capture_session = create_capture_session(db, submitter, client_version)
    else:
        capture_session.last_update_time = datetime.now()
        db.add(capture_session)
        db.commit()

    return capture_session


def combine_and_prune_capture_sessions_by_start_time(db: DatabaseSession):
    print("Combining and pruning capture sessions by start time...")
    # TODO: This doesn't seem to work reliably yet. Do we even need this?
    return

    # Get all capture sessions ordered by start time (latest first)
    capture_sessions = (
        db.query(CaptureSession).order_by(CaptureSession.start_time.desc()).all()
    )

    capture_sessions_to_delete = []
    try:
        for i in range(1, len(capture_sessions)):
            time_a = capture_sessions[i].start_time
            time_b = capture_sessions[i - 1].start_time

            # If they are within 60 seconds of each other, combine them
            if abs((time_a - time_b).total_seconds()) < 60:
                # Move packets to the previous capture session
                for packet in capture_sessions[i].packets:
                    try:
                        packet.capture_session = capture_sessions[i - 1]
                    except Exception as e:
                        print(f"Error reassigning packet {packet.id}: {e}")
                        raise

                capture_sessions_to_delete.append(capture_sessions[i])

        # After combining, remove any capture sessions that don't have any packets
        for capture_session_obj in capture_sessions:
            if (
                not capture_session_obj.packets
                and capture_session_obj not in capture_sessions_to_delete
            ):
                capture_sessions_to_delete.append(capture_session_obj)

        # Delete all marked capture sessions in a single batch
        for capture_session_to_delete in capture_sessions_to_delete:
            try:
                db.delete(capture_session_to_delete)
            except Exception as e:
                print(
                    f"Error deleting capture session {capture_session_to_delete.id}: {e}"
                )
                raise

        db.commit()
    except Exception as e:
        print(f"Error during capture session combining: {e}")
        db.rollback()
        raise
