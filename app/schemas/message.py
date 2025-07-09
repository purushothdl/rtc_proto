from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Literal

class MessageStatus(str, Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    SEEN = "seen"

class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    VIDEO = "video"

class MessageCreateRequest(BaseModel):
    room_id: UUID = Field(..., description="ID of the room where the message is sent")
    content: str = Field(..., min_length=1, max_length=2000, description="Message content")
    message_type: MessageType = Field(default=MessageType.TEXT, description="Type of message")

class PrivateMessageCreateRequest(BaseModel):
    target_user_id: UUID = Field(..., description="ID of the recipient")
    content: str = Field(..., min_length=1, max_length=2000)
    message_type: MessageType = Field(default=MessageType.TEXT)

class MessageResponse(BaseModel):
    id: UUID
    room_id: UUID
    sender_id: UUID
    sender_username: str
    sender_display_name: str
    content: str
    status: MessageStatus
    timestamp: datetime
    message_type: MessageType
    is_edited: bool
    is_deleted: bool

    class Config:
        from_attributes = True