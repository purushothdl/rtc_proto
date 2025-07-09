from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from .base import Base

class RoomMembership(Base):
    __tablename__ = "room_memberships"
    
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    room_id = Column(PG_UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="room_memberships")
    room = relationship("Room", back_populates="memberships")
    
    def __repr__(self):
        return f"<RoomMembership(id={self.id}, user_id={self.user_id}, room_id={self.room_id})>"