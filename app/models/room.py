from sqlalchemy import Column, UUID, String, ForeignKey, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid
import enum
from datetime import datetime
from .base import Base

class RoomType(enum.Enum):
    GROUP = "group"
    PRIVATE = "private"

class Room(Base):
    __tablename__ = "rooms"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=True)  # Nullable for private rooms
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    room_type = Column(Enum(RoomType), nullable=False, default=RoomType.GROUP)