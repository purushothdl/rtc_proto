from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, distinct
from sqlalchemy.orm import selectinload
from typing import List
from ..models.room import Room, RoomType
from ..models.room_membership import RoomMembership
from ..models.user import User
from ..schemas.room import RoomResponse, CreateRoomRequest, CreatePrivateRoomRequest
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

    async def get_user_rooms(self, user_id: UUID) -> List[RoomResponse]:
        """
        Get all rooms a user is a member of.

        Args:
            user_id: ID of the user

        Returns:
            List of RoomResponse objects
        """
        rooms = await self.db.execute(
            select(Room)
            .join(RoomMembership)
            .filter(RoomMembership.user_id == user_id)
            .options(selectinload(Room.memberships))
        )
        rooms = rooms.scalars().all()

        return [
            RoomResponse(
                id=room.id,
                name=room.name,
                room_type=room.room_type.value,
                created_by=room.created_by,
                created_at=room.created_at
            )
            for room in rooms
        ]