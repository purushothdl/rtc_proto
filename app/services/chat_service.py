from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from typing import List

from app.schemas.room import RoomType
from ..models.message import Message, MessageStatus
from ..models.room_membership import RoomMembership
from ..models.room import Room
from ..models.user import User
from ..schemas.message import MessageCreateRequest, MessageResponse, MessageType
from ..database.postgres import get_db_session
from .room_service import RoomService
from app.core.exceptions import (
    RoomNotFoundException,
    UnauthorizedAccessException,
    MessageNotSentException,
    UserNotFoundException
)

class ChatService:
    def __init__(self, room_service: RoomService, db: AsyncSession):
        self.room_service = room_service
        self.db = db

    async def _validate_and_send_message(
        self,
        user_id: UUID,
        room_id: UUID,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        recipient_id: UUID = None,
        is_private: bool = False,
    ) -> MessageResponse:
        """
        Helper method to validate and send a message.

        Args:
            user_id: ID of the sender
            room_id: ID of the room
            content: Message content
            message_type: Type of message (text, image, file, etc.)
            recipient_id: ID of the recipient (for private messages)
            is_private: Whether the message is private
        """
        # Check if room exists and user is a member
        room = await self.db.execute(
            select(Room)
            .join(RoomMembership)
            .filter(
                and_(
                    Room.id == room_id,
                    RoomMembership.room_id == Room.id,
                    RoomMembership.user_id == user_id
                )
            )
        )
        room = room.scalar_one_or_none()
        if not room:
            raise RoomNotFoundException(detail="Room not found or user is not a member")

        # Get sender details
        sender = await self.db.execute(select(User).filter(User.id == user_id))
        sender = sender.scalar_one_or_none()
        if not sender:
            raise UserNotFoundException(detail="Sender not found")

        message = Message(
            room_id=room_id,
            sender_id=user_id,
            content=content,
            message_type=message_type,
            status=MessageStatus.SENT,
            recipient_id=recipient_id,
            is_private=is_private,
        )
        self.db.add(message)
        try:
            await self.db.commit()
            await self.db.refresh(message)
        except Exception as e:
            raise MessageNotSentException(detail="Failed to send message") from e

        return MessageResponse(
            id=message.id,
            room_id=message.room_id,
            sender_id=message.sender_id,
            sender_username=sender.username,
            sender_display_name=sender.display_name,
            content=message.content,
            status=message.status,
            timestamp=message.created_at,
            message_type=message.message_type,
            is_edited=message.is_edited,
            is_deleted=message.is_deleted,
        )

    async def send_message(
        self,
        user_id: UUID,
        request: MessageCreateRequest,
    ) -> MessageResponse:
        """
        Send a message to an existing group room.

        Args:
            user_id: ID of the sender
            request: Message creation request with room_id
        """
        room = await self.db.execute(select(Room).filter(Room.id == request.room_id))
        room = room.scalar_one_or_none()
        if not room:
            raise RoomNotFoundException(detail="Room not found")
        if room.room_type == RoomType.PRIVATE:
            raise UnauthorizedAccessException(detail="Cannot send group messages to private rooms")

        return await self._validate_and_send_message(
            user_id=user_id,
            room_id=request.room_id,
            content=request.content,
            message_type=request.message_type,
            is_private=False,
        )

    async def send_private_message(
        self,
        sender_id: UUID,
        target_user_id: UUID,
        content: str,
        message_type: MessageType = MessageType.TEXT,
    ) -> MessageResponse:
        """
        Send a message to another user, creating a private room if needed.

        Args:
            sender_id: ID of the sender
            target_user_id: ID of the recipient
            content: Message content
        """
        room = await self.room_service.create_private_room(
            user1_id=sender_id,
            user2_id=target_user_id,
        )

        return await self._validate_and_send_message(
            user_id=sender_id,
            room_id=room.id,
            content=content,
            message_type=message_type,
            is_private=True,
        )

    async def get_room_messages(
        self,
        user_id: UUID,
        room_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[MessageResponse]:
        """
        Retrieve message history for a room.

        Args:
            user_id: ID of the requesting user
            room_id: ID of the room
            limit: Number of messages to return
            offset: Number of messages to skip
        """
        # Check if user is a member of the room
        membership = await self.db.execute(
            select(RoomMembership).filter(
                and_(
                    RoomMembership.room_id == room_id,
                    RoomMembership.user_id == user_id
                )
            )
        )
        if not membership.scalar():
            raise UnauthorizedAccessException(detail="User is not a member of the room")

        # Fetch messages with sender details
        messages = await self.db.execute(
            select(Message)
            .options(selectinload(Message.sender))
            .filter(Message.room_id == room_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        messages = messages.scalars().all()

        return [
            MessageResponse(
                id=msg.id,
                room_id=msg.room_id,
                sender_id=msg.sender_id,
                sender_username=msg.sender.username,
                sender_display_name=msg.sender.display_name,
                content=msg.content,
                status=msg.status,
                timestamp=msg.created_at,
                message_type=msg.message_type,
                is_edited=msg.is_edited,
                is_deleted=msg.is_deleted,
            )
            for msg in reversed(messages)
        ]