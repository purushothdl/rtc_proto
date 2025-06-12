import uuid
import enum
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import Column, UUID, ForeignKey, Text, DateTime, Enum

from .base import Base
from app.schemas.message import MessageStatus

class Message(Base):
    __tablename__ = "messages"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    room_id = Column(PG_UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(Enum(MessageStatus), nullable=False, default=MessageStatus.SENT)

    sender = relationship("User")
    room = relationship("Room")