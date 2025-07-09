from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from uuid import UUID
from typing import List

from app.models.room import Room
from ..schemas.room import CreateRoomRequest, CreatePrivateRoomRequest, RoomResponse
from ..services.room_service import RoomService
from app.dependencies.service_dependencies import get_room_service
from app.dependencies.auth_dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/rooms", tags=["rooms"])

@router.post("", response_model=RoomResponse)
async def create_room(
    request: CreateRoomRequest,
    current_user: User = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """
    Create a new group room.

    Args:
        request: Room creation request
        current_user: Authenticated user details
        room_service: Room service instance

    Returns:
        RoomResponse with created room details
    """
    return await room_service.create_room(
        user_id=current_user.id,
        request=request
    )

@router.post("/private", response_model=RoomResponse)
async def create_private_room(
    request: CreatePrivateRoomRequest,
    current_user: User = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """
    Create or get a private room with another user.

    Args:
        request: Private room creation request
        current_user: Authenticated user details
        room_service: Room service instance

    Returns:
        RoomResponse with private room details
    """
    room = await room_service.create_private_room(
        user1_id=current_user.id,
        user2_id=request.user_id
    )
    return RoomResponse(
        id=room.id,
        name=room.name,
        room_type=room.room_type.value,
        created_by=room.created_by,
        created_at=room.created_at
    )

@router.post("/{room_id}/join")
async def join_room(
    room_id: UUID,
    current_user: User = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """
    Join a group room.

    Args:
        room_id: ID of the room
        current_user: Authenticated user details
        room_service: Room service instance
    """
    await room_service.join_room(
        user_id=current_user.id,
        room_id=room_id
    )
    return {"message": "Successfully joined room"}

@router.get("", response_model=List[RoomResponse])
async def get_user_rooms(
    current_user: User = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service)
):
    """
    Gets all rooms the user is a member of, including member details
    and the last message.
    """
    return await room_service.get_user_rooms_with_details(current_user.id)