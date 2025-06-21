from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from enum import Enum

class RoomType(str, Enum):
    GROUP = "group"
    PRIVATE = "private"

class CreateRoomRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Room name (for group rooms)")
    room_type: RoomType = Field(default=RoomType.GROUP, description="Type of room")

class CreatePrivateRoomRequest(BaseModel):
    user_id: UUID = Field(..., description="ID of the other user for private chat")

class RoomResponse(BaseModel):
    id: UUID
    name: str | None
    room_type: RoomType
    created_by: UUID
    created_at: datetime

    class Config:
        from_attributes = True