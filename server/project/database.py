import os
import datetime
import enum
from datetime import datetime, timedelta
from contextlib import contextmanager

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
from sqlalchemy.orm import relationship
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

Base = declarative_base()


@contextmanager
def get_cached_session():
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()


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
# Enums
#


class PacketDirection(int, enum.Enum):
    S2C = 0
    C2S = 1

    @staticmethod
    def from_str(label):
        if label.upper() in ("S2C", "SERVER_TO_CLIENT"):
            return PacketDirection.S2C
        elif label.upper() in ("C2S", "CLIENT_TO_SERVER"):
            return PacketDirection.C2S
        else:
            raise NotImplementedError


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
    direction = Column(Enum(PacketDirection))
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


def get_submitter_map(session: Session):
    submitter_map = {}
    for submitter in session.query(Submitter).all():
        submitter_map[submitter.identifier] = submitter
    return submitter_map


def get_submitter_count(session: Session) -> int:
    return session.query(Submitter).count()


def get_packet_count(session: Session) -> int:
    return session.query(PacketData).count()


def get_packet_size_bytes(session: Session) -> int:
    return session.query(func.sum(PacketData.size)).scalar()


def get_submitter_by_identifier(session: Session, identifier: str) -> Submitter:
    return session.query(Submitter).filter(Submitter.identifier == identifier).first()


#
# Create <x>
#


def create_submitter(session: Session, identifier: str) -> Submitter:
    submitter = Submitter(identifier=identifier)
    session.add(submitter)
    session.commit()
    return submitter


def create_capture_session(
    session: Session, submitter: Submitter, client_version: str
) -> CaptureSession:
    print(f"Creating capture session for: {submitter.identifier[:8]}...")
    capture_session = CaptureSession(submitter=submitter)
    capture_session.client_version = client_version
    session.add(capture_session)
    session.commit()
    return capture_session


def create_packet_data(
    session: Session,
    capture_session: CaptureSession,
    data: bytes,
    packet_type: int,
    packet_size: int,
    packet_direction: PacketDirection,
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

    session.add(packet)
    session.commit()

    return packet


#
# Session Management
#


# TODO: Add some caching here so we're not so reliant on constantly querying the database
def update_or_create_capture_session(
    session: Session, submitter: Submitter, client_version: str
) -> CaptureSession:
    capture_session = (
        session.query(CaptureSession)
        .filter(CaptureSession.submitter_id == submitter.id)
        .order_by(CaptureSession.start_time.desc())
        .first()
    )

    if capture_session is None:
        capture_session = create_capture_session(session, submitter, client_version)
    elif capture_session.last_update_time < datetime.now() - timedelta(
        seconds=10
    ):  # TODO: Is 10 seconds a good threshold?
        capture_session = create_capture_session(session, submitter, client_version)
    else:
        capture_session.last_update_time = datetime.now()
        session.add(capture_session)
        session.commit()

    return capture_session


# TODO: Does this even work?
def combine_capture_sessions_by_start_time(session: Session):
    sessions = (
        session.query(CaptureSession).order_by(CaptureSession.start_time.desc()).all()
    )

    for i in range(1, len(sessions)):
        time_a = sessions[i].start_time
        time_b = sessions[i - 1].start_time

        # If they are within 10 seconds of each other, combine them
        if abs((time_a - time_b).total_seconds()) < 10:
            for packet in sessions[i].packets:
                packet.session = sessions[i - 1]
            session.delete(sessions[i])

    session.commit()
    return sessions
