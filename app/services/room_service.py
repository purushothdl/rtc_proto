from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, distinct
from sqlalchemy.orm import selectinload
from typing import List
from sqlalchemy.orm import contains_eager

from app.schemas.message import MessageStatus
from ..models.message import Message
from ..models.room import Room, RoomType
from ..models.room_membership import RoomMembership
from ..models.user import User
from ..schemas.room import RoomMemberResponse, RoomResponse, CreateRoomRequest, CreatePrivateRoomRequest
from ..database.postgres import get_db_session
from ..core.exceptions import (
    UserNotFoundException,
    RoomNotFoundException,
    RoomAlreadyExistsException,
    UnauthorizedAccessException,
    InternalServerErrorException,
)

class RoomService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_room(
        self,
        user_id: UUID,
        request: CreateRoomRequest,
    ) -> RoomResponse:
        """
        Create a new room (group only).

        Args:
            user_id: ID of the creator
            request: Room creation request

        Returns:
            RoomResponse with created room details

        Raises:
            RoomAlreadyExistsException: If a room with the same name already exists
            InternalServerErrorException: If room creation fails
        """
        # Check if a room with the same name already exists
        existing_room = await self.db.execute(
            select(Room).filter(Room.name == request.name)
        )
        if existing_room.scalar():
            raise RoomAlreadyExistsException(detail="Room with this name already exists")

        room = Room(
            name=request.name,
            created_by=user_id,
            room_type=RoomType.GROUP
        )
        self.db.add(room)
        try:
            await self.db.commit()
            await self.db.refresh(room)
        except Exception as e:
            raise InternalServerErrorException(detail="Failed to create room") from e

        # Add creator as a member
        membership = RoomMembership(
            user_id=user_id,
            room_id=room.id
        )
        self.db.add(membership)
        try:
            await self.db.commit()
        except Exception as e:
            raise InternalServerErrorException(detail="Failed to add user to room") from e

        return RoomResponse(
            id=room.id,
            name=room.name,
            room_type=room.room_type.value,
            created_by=room.created_by,
            created_at=room.created_at
        )

    async def create_private_room(
        self,
        user1_id: UUID,
        user2_id: UUID,
    ) -> Room:
        """
        Create or get an existing private room between two users.

        Args:
            user1_id: ID of the first user
            user2_id: ID of the second user

        Returns:
            Room object representing the private room

        Raises:
            UserNotFoundException: If user2_id doesn't exist
            InternalServerErrorException: If room creation fails
        """

        if user1_id == user2_id:
            
            # We need to find if this user already has a special "self-chat" room.
            # A correct self-chat room is private and has ONLY ONE member.
            self_chat_query = (
                select(Room)
                .join(RoomMembership)
                .filter(
                    and_(
                        Room.room_type == RoomType.PRIVATE,
                        RoomMembership.user_id == user1_id
                    )
                )
                .group_by(Room.id)
                .having(func.count(RoomMembership.user_id) == 1) # Crucial: ensures it's not a broken 2-person room
            )
            
            # Execute the query. .scalar_one_or_none() safely gets the result
            # if there's one room, or None if there are zero.
            existing_self_chat = await self.db.execute(self_chat_query)
            room = existing_self_chat.scalar_one_or_none()

            # If we found the existing "self-chat" room, we're done. Return it.
            if room:
                return room
            
            # If no "self-chat" room exists, we create one now.
            room = Room(name=None, created_by=user1_id, room_type=RoomType.PRIVATE)
            self.db.add(room)
            await self.db.flush() # This sends the INSERT to the DB and gets us the new room.id
            
            # IMPORTANT: We add only ONE membership record for the user.
            membership = RoomMembership(user_id=user1_id, room_id=room.id)
            self.db.add(membership)
            
            await self.db.commit() # Save everything
            return room

        # Check if user2 exists
        user2 = await self.db.execute(select(User).filter(User.id == user2_id))
        if not user2.scalar():
            raise UserNotFoundException(detail="Target user not found")

        # Check if private room already exists
        existing_room = await self.db.execute(
            select(Room)
            .join(RoomMembership)
            .filter(
                and_(
                    Room.room_type == RoomType.PRIVATE,
                    RoomMembership.user_id.in_([user1_id, user2_id]),
                    RoomMembership.room_id == Room.id
                )
            )
            .group_by(Room.id)
            .having(func.count(distinct(RoomMembership.user_id)) == 2)
        )
        room = existing_room.scalar_one_or_none()
        if room:
            return room

        # Create new private room
        room = Room(
            name=None, 
            created_by=user1_id,
            room_type=RoomType.PRIVATE
        )
        self.db.add(room)
        try:
            await self.db.flush()
        except Exception as e:
            raise InternalServerErrorException(detail="Failed to create private room") from e

        # Add both users to the room
        memberships = [
            RoomMembership(user_id=user1_id, room_id=room.id),
            RoomMembership(user_id=user2_id, room_id=room.id)
        ]
        self.db.add_all(memberships)
        try:
            await self.db.commit()
        except Exception as e:
            raise InternalServerErrorException(detail="Failed to add users to private room") from e

        return room

    async def join_room(self, user_id: UUID, room_id: UUID) -> None:
        """
        Add a user to a room (group only).

        Args:
            user_id: ID of the user
            room_id: ID of the room

        Raises:
            RoomNotFoundException: If room doesn't exist
            UnauthorizedAccessException: If room is private
            RoomAlreadyExistsException: If user is already a member
            InternalServerErrorException: If joining fails
        """
        # Check if room exists and is a group room
        room = await self.db.execute(
            select(Room).filter(Room.id == room_id)
        )
        room = room.scalar_one_or_none()
        if not room:
            raise RoomNotFoundException(detail="Room not found")
        if room.room_type == RoomType.PRIVATE:
            raise UnauthorizedAccessException(detail="Cannot join private rooms")

        # Check if user is already a member
        membership = await self.db.execute(
            select(RoomMembership).filter(
                and_(
                    RoomMembership.room_id == room_id,
                    RoomMembership.user_id == user_id
                )
            )
        )
        if membership.scalar():
            raise RoomAlreadyExistsException(detail="User is already a member of the room")

        # Add user to room
        membership = RoomMembership(
            user_id=user_id,
            room_id=room_id
        )
        self.db.add(membership)
        try:
            await self.db.commit()
        except Exception as e:
            raise InternalServerErrorException(detail="Failed to join room") from e


    async def get_user_rooms_with_details(self, user_id: UUID) -> List[RoomResponse]:
        """
        Gets all rooms a user is a member of, enriched with member details,
        the last message, and the count of unread messages.
        """
        # Query 1: Get rooms and members (no change here)
        rooms_query = (
            select(Room)
            .join(Room.memberships)
            .where(RoomMembership.user_id == user_id)
            .options(selectinload(Room.memberships).selectinload(RoomMembership.user))
            .distinct()
        )
        result = await self.db.execute(rooms_query)
        rooms = result.scalars().all()

        if not rooms:
            return []

        room_ids = [room.id for room in rooms]

        # Query 2: Get last messages (no change here)
        last_message_subquery = (
            select(Message, func.row_number().over(
                partition_by=Message.room_id,
                order_by=Message.created_at.desc()
            ).label("row_num"))
            .where(Message.room_id.in_(room_ids))
            .subquery()
        )
        last_messages_query = select(last_message_subquery).where(last_message_subquery.c.row_num == 1)
        last_messages_result = await self.db.execute(last_messages_query)
        last_messages_map = {msg.room_id: msg for msg in last_messages_result.all()}

        # --- NEW QUERY 3: Get unread counts for all rooms at once ---
        unread_counts_query = (
            select(
                Message.room_id,
                func.count(Message.id).label("unread_count")
            )
            .where(
                Message.room_id.in_(room_ids),
                Message.sender_id != user_id,
                Message.status != MessageStatus.SEEN
            )
            .group_by(Message.room_id)
        )
        unread_counts_result = await self.db.execute(unread_counts_query)
        # Create a dictionary for fast lookups: {room_id: count}
        unread_counts_map = {room_id: count for room_id, count in unread_counts_result.all()}

        # Combine all data in Python
        response_list = []
        for room in rooms:
            last_msg = last_messages_map.get(room.id)
            unread_count = unread_counts_map.get(room.id, 0) # Default to 0 if no unread messages
            response_list.append(
                RoomResponse(
                    id=room.id,
                    name=room.name,
                    room_type=room.room_type,
                    created_by=room.created_by,
                    created_at=room.created_at,
                    members=[
                        RoomMemberResponse(
                            user_id=member.user.id,
                            username=member.user.username
                        ) for member in room.memberships
                    ],
                    last_message=last_msg.content if last_msg else None,
                    last_message_timestamp=last_msg.created_at if last_msg else None,
                    unread_count=unread_count # Pass the count to the response
                )
            )
        
        return response_list
    
    async def get_room_member_ids(self, room_id: UUID) -> list[UUID]:
        """Fetches a list of all user IDs in a given room."""
        result = await self.db.execute(
            select(RoomMembership.user_id).filter(RoomMembership.room_id == room_id)
        )
        return result.scalars().all()