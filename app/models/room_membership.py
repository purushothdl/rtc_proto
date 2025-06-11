from sqlalchemy import Column, UUID, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from .base import Base

class RoomMembership(Base):
    __tablename__ = "room_memberships"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(PG_UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=False)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    room = relationship("Room", backref="memberships")
    user = relationship("User", backref="memberships")