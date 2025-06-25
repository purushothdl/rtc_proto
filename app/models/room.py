from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, func, select
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, column_property
from app.models.base import Base
from app.schemas.room import RoomType
from .message import Message

class Room(Base):
    __tablename__ = "rooms"
    
    name = Column(String(100), nullable=True)  
    room_type = Column(Enum(RoomType), default=RoomType.GROUP)  
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    messages = relationship("Message", back_populates="room")
    memberships = relationship("RoomMembership", back_populates="room")
    
    def __repr__(self):
        return f"<Room(id={self.id}, name='{self.name}', type='{self.room_type}')>"