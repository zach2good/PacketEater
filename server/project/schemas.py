from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class PacketBase(BaseModel):
    type: Optional[int]
    size: Optional[int]


class PacketCreate(PacketBase):
    data: bytes



class Packet(PacketBase):
    id: int
    timestamp: datetime
    submitter_id: int
