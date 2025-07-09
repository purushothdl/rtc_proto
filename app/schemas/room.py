from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from enum import Enum
from typing import List, Optional

class RoomType(str, Enum):
    GROUP = "group"
    PRIVATE = "private"

class CreateRoomRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Room name")

class CreatePrivateRoomRequest(BaseModel):
    user_id: UUID = Field(..., description="ID of the other user for private chat")

class RoomMemberResponse(BaseModel):
    user_id: UUID
    username: str

    class Config:
        from_attributes = True

class RoomResponse(BaseModel):
    id: UUID
    name: Optional[str] = None
    room_type: RoomType
    created_by: UUID
    created_at: datetime
    members: List[RoomMemberResponse] = []
    last_message: Optional[str] = None
    last_message_timestamp: Optional[datetime] = None
    unread_count: int = 0

    class Config:
        from_attributes = True