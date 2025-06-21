from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

from app.dependencies.auth_dependencies import get_current_user
from app.dependencies.service_dependencies import get_chat_service
from app.models.user import User
from ..schemas.message import MessageCreateRequest, MessageResponse, PrivateMessageCreateRequest
from ..services.chat_service import ChatService

router = APIRouter(prefix="/api/messages", tags=["messages"])

@router.post("", response_model=MessageResponse)
async def send_message(
    request: MessageCreateRequest,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Send a message to a room.

    Args:
        request: Message creation request
        current_user: Authenticated user details
        chat_service: Chat service instance

    Returns:
        MessageResponse with created message details
    """
    return await chat_service.send_message(
        user_id=current_user.id,
        request=request,
    )

@router.post("/private", response_model=MessageResponse)
async def send_private_message(
    request: PrivateMessageCreateRequest,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Send a private message to another user, creating a room if needed.

    Args:
        request: Private message creation request
        current_user: Authenticated user details
        chat_service: Chat service instance

    Returns:
        MessageResponse with created message details
    """
    return await chat_service.send_private_message(
        sender_id=current_user.id,
        target_user_id=request.target_user_id,
        content=request.content,
        message_type=request.message_type,
    )

@router.get("/rooms/{room_id}", response_model=List[MessageResponse])
async def get_room_messages(
    room_id: UUID,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
    limit: int = Query(50, ge=1, le=100, description="Number of messages to return"),
    offset: int = Query(0, ge=0, description="Number of messages to skip")
):
    """
    Retrieve message history for a room.

    Args:
        room_id: ID of the room
        current_user: Authenticated user details
        chat_service: Chat service instance
        limit: Number of messages to return
        offset: Number of messages to skip

    Returns:
        List of MessageResponse objects
    """
    return await chat_service.get_room_messages(
        user_id=current_user.id,
        room_id=room_id,
        limit=limit,
        offset=offset,
    )