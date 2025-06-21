from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import Column, ForeignKey, Text, DateTime, Enum, Integer, String, Boolean
from sqlalchemy.sql import func

from .base import Base
from app.schemas.message import MessageStatus, MessageType

class Message(Base):
    __tablename__ = "messages"
    
    content = Column(Text, nullable=False)
    message_type = Column(Enum(MessageType), default=MessageType.TEXT)  # text, image, file, etc.
    status = Column(Enum(MessageStatus), default=MessageStatus.SENT)  # sent, delivered, read, etc.
    
    # Sender information
    sender_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    sender = relationship("User", foreign_keys=[sender_id])
    
    # Room information (for group messages)
    room_id = Column(PG_UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=True)
    room = relationship("Room", back_populates="messages")
    
    # Private message information
    recipient_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    recipient = relationship("User", foreign_keys=[recipient_id])
    is_private = Column(Boolean, default=False)
    
    # Metadata
    is_edited = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Message(id={self.id}, sender_id={self.sender_id}, content='{self.content[:50]}...')>"