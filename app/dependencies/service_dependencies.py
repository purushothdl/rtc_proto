from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.globals import websocket_manager 
from app.utils.websocket_manager import WebsocketManager

from app.database.postgres import get_db_session
from app.services.auth_service import AuthService
from app.services.room_service import RoomService
from app.services.chat_service import ChatService
from app.services.notification_service import NotificationService

def get_websocket_manager() -> WebsocketManager:
    """
    Dependency that provides the singleton WebsocketManager instance.
    """
    return websocket_manager

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

def get_notification_service(db: AsyncSession = Depends(get_db_session)) -> NotificationService:
    """
    Dependency that provides an instance of NotificationService with an active database session.
    """
    return NotificationService(db)

def get_chat_service(
    room_service: RoomService = Depends(get_room_service),
    db: AsyncSession = Depends(get_db_session),
    ws_manager: WebsocketManager = Depends(get_websocket_manager),
    notification_service: NotificationService = Depends(get_notification_service)
) -> ChatService:
    """
    Dependency that provides an instance of ChatService with required dependencies.
    """
    return ChatService(
        room_service=room_service, 
        db=db, 
        websocket_manager=ws_manager,
        notification_service=notification_service
    )