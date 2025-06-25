from collections import defaultdict
import json
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from sqlalchemy.orm import selectinload
from typing import List

from app.schemas.room import RoomType
from app.services.notification_service import NotificationService
from ..models.message import Message, MessageStatus
from ..models.room_membership import RoomMembership
from ..models.room import Room
from ..models.user import User
from ..schemas.message import MessageCreateRequest, MessageResponse, MessageType
from ..database.postgres import get_db_session
from .room_service import RoomService
from .notification_service import NotificationService
from app.core.exceptions import (
    RoomNotFoundException,
    UnauthorizedAccessException,
    MessageNotSentException,
    UserNotFoundException
)
from ..utils.websocket_manager import WebsocketManager

class ChatService:
    def __init__(
        self, 
        room_service: RoomService, 
        db: AsyncSession, 
        websocket_manager: WebsocketManager,
        notification_service: NotificationService 
    ):
        self.room_service = room_service
        self.db = db
        self.websocket_manager = websocket_manager
        self.notification_service = notification_service 

    async def _validate_and_send_message(
        self,
        user_id: UUID,
        room_id: UUID,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        recipient_id: UUID = None,
        is_private: bool = False,
    ) -> MessageResponse:
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
        sender: User,
        request: MessageCreateRequest,
    ) -> MessageResponse:
        """
        Send a message to a group room, saves it, and broadcasts it, and sends push notifications.
        """
        room = await self.db.execute(select(Room).filter(Room.id == request.room_id))
        room = room.scalar_one_or_none()
        if not room:
            raise RoomNotFoundException(detail="Room not found")
        if room.room_type == RoomType.PRIVATE:
            raise UnauthorizedAccessException(detail="Cannot send group messages to private rooms")

        message_response = await self._validate_and_send_message(
            user_id=sender.id,
            room_id=request.room_id,
            content=request.content,
            message_type=request.message_type,
            is_private=False,
        )

        all_member_ids = await self.room_service.get_room_member_ids(request.room_id)
        
        smart_event_payload = {
            "type": "new_message",
            "data": message_response.model_dump()
        }
        json_payload = json.dumps(smart_event_payload, default=str)

        for member_id in all_member_ids:
            await self.websocket_manager.send_personal_message(
                user_id=member_id,
                message=json_payload
            )
        
        # TODO: Add logic here later for push notifications to offline users
        online_user_ids = await self.websocket_manager.get_globally_online_users()

        for member_id in all_member_ids:
            if str(member_id) not in online_user_ids and member_id != sender.id:
                await self.notification_service.send_notification_to_user(
                    user_id=member_id,
                    title=f"New message in {room.name}",
                    body=request.content, 
                    data={"room_id": str(request.room_id)}
                )

        return message_response

    async def send_private_message(
        self,
        sender: User,
        target_user_id: UUID,
        content: str,
        message_type: MessageType = MessageType.TEXT,
    ) -> MessageResponse:
        """
        Send a private message, saves it, broadcasts it, and sends push notifications.
        """
        room = await self.room_service.create_private_room(
            user1_id=sender.id,
            user2_id=target_user_id,
        )

        message_response = await self._validate_and_send_message(
            user_id=sender.id,
            room_id=room.id,
            content=content,
            message_type=message_type,
            is_private=True,
            recipient_id=target_user_id
        )

        recipients = [sender.id, target_user_id]

        smart_event_payload = {
            "type": "new_message", 
            "data": message_response.model_dump()
        }
        json_payload = json.dumps(smart_event_payload, default=str)

        for user_id in set(recipients): 
            await self.websocket_manager.send_personal_message(
                user_id=user_id,
                message=json_payload
            )

        # TODO: Add logic here later for push notifications to offline users   
        online_user_ids = await self.websocket_manager.get_globally_online_users()

        if str(target_user_id) not in online_user_ids:
            await self.notification_service.send_notification_to_user(
                user_id=target_user_id,
                title=f"New message from {sender.username}",
                body=content,
                data={"room_id": str(room.id)} 
            )
            
        return message_response
            
    async def get_room_messages(
        self,
        user_id: UUID,
        room_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[MessageResponse]:
        """
        Retrieve message history for a room.
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
    
    async def _update_message_status(
        self,
        message_ids: list[UUID],
        new_status: MessageStatus,
        requesting_user_id: UUID,
    ):
        """
        Internal helper to update the status of a list of messages.
        It handles authorization, database updates, and broadcasting the change.
        """
        if not message_ids:
            return

        # 1. Fetch messages and their room memberships to authorize the request
        query = (
            select(Message)
            .options(selectinload(Message.room).joinedload(Room.memberships))
            .filter(Message.id.in_(message_ids))
        )
        result = await self.db.execute(query)
        messages_to_update = result.scalars().all()

        if not messages_to_update:
            return

        # 2. Authorization and Filtering
        # A user can only update status for messages they are a recipient of.
        # We also respect the status progression: sent -> delivered -> seen.
        
        valid_message_ids_to_update = []
        # Group messages by room to broadcast updates efficiently
        room_updates = defaultdict(list) 

        allowed_previous_statuses = {
            MessageStatus.DELIVERED: [MessageStatus.SENT],
            MessageStatus.SEEN: [MessageStatus.SENT, MessageStatus.DELIVERED],
        }

        for msg in messages_to_update:
            is_recipient = False
            if msg.is_private:
                # For DMs, the user must be the designated recipient
                if msg.recipient_id == requesting_user_id:
                    is_recipient = True
            else:
                # For group chats, the user must be a member of the room
                if any(m.user_id == requesting_user_id for m in msg.room.memberships):
                    is_recipient = True
            
            # Check if the user is authorized AND the status update is valid
            if is_recipient and msg.status in allowed_previous_statuses.get(new_status, []):
                valid_message_ids_to_update.append(msg.id)
                room_updates[msg.room_id].append(str(msg.id))

        if not valid_message_ids_to_update:
            return

        # 3. Update the database
        stmt = (
            update(Message)
            .where(Message.id.in_(valid_message_ids_to_update))
            .values(status=new_status)
        )
        await self.db.execute(stmt)
        await self.db.commit()

        # 4. Broadcast the status update to all members of the affected rooms
        for room_id, updated_ids in room_updates.items():
            all_member_ids = await self.room_service.get_room_member_ids(room_id)
            
            status_update_payload = {
                "type": "message_status_update",
                "data": {
                    "room_id": str(room_id),
                    "message_ids": updated_ids,
                    "status": new_status.value
                }
            }
            json_payload = json.dumps(status_update_payload)

            for member_id in all_member_ids:
                await self.websocket_manager.send_personal_message(member_id, json_payload)

    async def mark_messages_as_delivered(self, message_ids: list[UUID], requesting_user_id: UUID):
        """Marks a list of messages as DELIVERED for a given user."""
        await self._update_message_status(message_ids, MessageStatus.DELIVERED, requesting_user_id)

    async def mark_messages_as_seen(self, message_ids: list[UUID], requesting_user_id: UUID):
        """Marks a list of messages as SEEN for a given user."""
        await self._update_message_status(message_ids, MessageStatus.SEEN, requesting_user_id)