# app/api/websocket.py
from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
import json
import logging
from typing import List, Optional

from app.database.postgres import get_db_session
from app.dependencies.auth_dependencies import get_current_user_websocket
from app.dependencies.service_dependencies import get_chat_service
from app.utils.websocket_manager import websocket_manager
from app.services.chat_service import ChatService
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# You'll need to create this dependency for WebSocket auth
async def get_current_user_websocket(
    websocket: WebSocket,
    token: Optional[str] = None
) -> User:
    """
    WebSocket authentication dependency
    Token can be passed as query parameter: ws://localhost:8000/ws?token=your_jwt_token
    """
    if not token:
        token = websocket.query_params.get("token")
    
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Use your existing token validation logic here
    # This is a placeholder - implement based on your auth system
    try:
        # Decode and validate token, return user
        # user = await validate_token_and_get_user(token)
        # return user
        pass
    except Exception as e:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        raise HTTPException(status_code=401, detail="Invalid token")

def get_chat_service_websocket(db: AsyncSession = Depends(get_db_session)) -> ChatService:
    """WebSocket-compatible chat service dependency"""
    return ChatService(db)

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user: User = Depends(get_current_user_websocket),
    chat_service: ChatService = Depends(get_chat_service_websocket)
):
    """
    Main WebSocket endpoint for real-time chat
    """
    # Get user's rooms for initialization
    # You'll need to implement this based on your room membership logic
    user_rooms = []  # TODO: Get user's room IDs from database
    
    # Connect user
    connection_id = await websocket_manager.connect(websocket, user, user_rooms)
    
    try:
        while True:
            # Receive message from WebSocket
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Handle different message types
            await handle_websocket_message(message_data, user, chat_service)
            
    except WebSocketDisconnect:
        logger.info(f"User {user.id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for user {user.id}: {e}")
    finally:
        await websocket_manager.disconnect(user.id)

async def handle_websocket_message(message_data: dict, user: User, chat_service: ChatService):
    """
    Handle different types of WebSocket messages
    """
    message_type = message_data.get("type")
    data = message_data.get("data", {})
    
    try:
        if message_type == "send_room_message":
            await handle_room_message(data, user, chat_service)
        
        elif message_type == "send_private_message":
            await handle_private_message(data, user, chat_service)
        
        elif message_type == "join_room":
            await handle_join_room(data, user)
        
        elif message_type == "leave_room":
            await handle_leave_room(data, user)
        
        elif message_type == "typing_start":
            await handle_typing_indicator(data, user, True)
        
        elif message_type == "typing_stop":
            await handle_typing_indicator(data, user, False)
        
        elif message_type == "ping":
            await handle_ping(user)
        
        else:
            logger.warning(f"Unknown message type: {message_type}")
            await send_error_to_user(user.id, "Unknown message type")
    
    except Exception as e:
        logger.error(f"Error handling WebSocket message: {e}")
        await send_error_to_user(user.id, "Failed to process message")

async def handle_room_message(data: dict, user: User, chat_service: ChatService):
    """Handle room message sending"""
    room_id = data.get("room_id")
    content = data.get("content")
    message_type = data.get("message_type", "text")
    
    if not room_id or not content:
        await send_error_to_user(user.id, "Room ID and content are required")
        return
    
    try:
        result = await chat_service.send_message(user, room_id, content, message_type)
        
        # Send confirmation back to sender
        confirmation = {
            "type": "message_sent",
            "data": {
                "message_id": result["message_id"],
                "room_id": room_id,
                "status": result["status"]
            }
        }
        await websocket_manager.send_personal_message(confirmation, user.id)
        
    except Exception as e:
        await send_error_to_user(user.id, f"Failed to send room message: {str(e)}")

async def handle_private_message(data: dict, user: User, chat_service: ChatService):
    """Handle private message sending"""
    recipient_id = data.get("recipient_id")
    content = data.get("content")
    message_type = data.get("message_type", "text")
    
    if not recipient_id or not content:
        await send_error_to_user(user.id, "Recipient ID and content are required")
        return
    
    try:
        result = await chat_service.send_private_message(user, recipient_id, content, message_type)
        
        # Send confirmation back to sender
        confirmation = {
            "type": "private_message_sent",
            "data": {
                "message_id": result["message_id"],
                "recipient_id": recipient_id,
                "status": result["status"]
            }
        }
        await websocket_manager.send_personal_message(confirmation, user.id)
        
    except Exception as e:
        await send_error_to_user(user.id, f"Failed to send private message: {str(e)}")

async def handle_join_room(data: dict, user: User):
    """Handle user joining a room"""
    room_id = data.get("room_id")
    
    if not room_id:
        await send_error_to_user(user.id, "Room ID is required")
        return
    
    try:
        await websocket_manager.join_room(user.id, room_id)
        
        # Notify room members about new user
        notification = {
            "type": "user_joined",
            "data": {
                "room_id": room_id,
                "user": {
                    "id": user.id,
                    "username": user.username
                }
            }
        }
        await websocket_manager.send_room_message(notification, room_id, exclude_user_id=user.id)
        
        # Send confirmation to user
        confirmation = {
            "type": "room_joined",
            "data": {"room_id": room_id}
        }
        await websocket_manager.send_personal_message(confirmation, user.id)
        
    except Exception as e:
        await send_error_to_user(user.id, f"Failed to join room: {str(e)}")

async def handle_leave_room(data: dict, user: User):
    """Handle user leaving a room"""
    room_id = data.get("room_id")
    
    if not room_id:
        await send_error_to_user(user.id, "Room ID is required")
        return
    
    try:
        await websocket_manager.leave_room(user.id, room_id)
        
        # Notify room members about user leaving
        notification = {
            "type": "user_left",
            "data": {
                "room_id": room_id,
                "user": {
                    "id": user.id,
                    "username": user.username
                }
            }
        }
        await websocket_manager.send_room_message(notification, room_id, exclude_user_id=user.id)
        
    except Exception as e:
        await send_error_to_user(user.id, f"Failed to leave room: {str(e)}")

async def handle_typing_indicator(data: dict, user: User, is_typing: bool):
    """Handle typing indicators"""
    room_id = data.get("room_id")
    recipient_id = data.get("recipient_id")
    
    typing_message = {
        "type": "typing_indicator",
        "data": {
            "user": {
                "id": user.id,
                "username": user.username
            },
            "is_typing": is_typing,
            "room_id": room_id,
            "recipient_id": recipient_id
        }
    }
    
    if room_id:
        # Send to room
        await websocket_manager.send_room_message(typing_message, room_id, exclude_user_id=user.id)
    elif recipient_id:
        # Send to specific user
        await websocket_manager.send_personal_message(typing_message, recipient_id)

async def handle_ping(user: User):
    """Handle ping for connection health check"""
    pong_message = {
        "type": "pong",
        "data": {"timestamp": __import__('time').time()}
    }
    await websocket_manager.send_personal_message(pong_message, user.id)

async def send_error_to_user(user_id: int, error_message: str):
    """Send error message to user"""
    error_msg = {
        "type": "error",
        "data": {"message": error_message}
    }
    await websocket_manager.send_personal_message(error_msg, user_id)