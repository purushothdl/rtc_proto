from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.postgres import get_db_session
from app.services.auth_service import AuthService
from app.services.room_service import RoomService
from app.services.chat_service import ChatService

def get_auth_service(db: AsyncSession = Depends(get_db_session)) -> AuthService:
    """
    Dependency that provides an instance of AuthService with an active database session.
    """
    return AuthService(db)

def get_room_service(db: AsyncSession = Depends(get_db_session)) -> RoomService:
    """
    Dependency that provides an instance of RoomService with an active database session.
    """
    return RoomService(db)

def get_chat_service(
    room_service: RoomService = Depends(get_room_service),
    db: AsyncSession = Depends(get_db_session)
) -> ChatService:
    """
    Dependency that provides an instance of ChatService with required dependencies.
    """
    return ChatService(room_service, db)