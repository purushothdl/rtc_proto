# app/utils/websocket_manager.py
from fastapi import WebSocket
from typing import Dict, List, Optional
import json
import logging
import uuid
from app.database.redis import redis_manager
from app.models.user import User

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        # In-memory storage for active WebSocket connections
        # Key: connection_id, Value: WebSocket instance
        self.active_connections: Dict[str, WebSocket] = {}
        # Key: user_id, Value: connection_id
        self.user_connections: Dict[int, str] = {}
    
    def generate_connection_id(self) -> str:
        """Generate unique connection ID"""
        return str(uuid.uuid4())
    
    async def connect(self, websocket: WebSocket, user: User, room_ids: List[int] = None) -> str:
        """Accept WebSocket connection and register user"""
        await websocket.accept()
        
        connection_id = self.generate_connection_id()
        
        # Store connection locally
        self.active_connections[connection_id] = websocket
        self.user_connections[user.id] = connection_id
        
        # Store in Redis for multi-server scenarios
        await redis_manager.set_user_connection(user.id, connection_id, room_ids or [])
        
        # Add user to their rooms
        if room_ids:
            for room_id in room_ids:
                await redis_manager.add_user_to_room(room_id, user.id)
        
        logger.info(f"User {user.id} connected with connection_id: {connection_id}")
        return connection_id
    
    async def disconnect(self, user_id: int):
        """Disconnect user and cleanup"""
        connection_id = self.user_connections.get(user_id)
        if not connection_id:
            return
        
        # Get user's room info before cleanup
        user_connection_info = await redis_manager.get_user_connection(user_id)
        room_ids = user_connection_info.get("room_ids", []) if user_connection_info else []
        
        # Remove from local storage
        self.active_connections.pop(connection_id, None)
        self.user_connections.pop(user_id, None)
        
        # Remove from Redis
        await redis_manager.remove_user_connection(user_id)
        await redis_manager.cleanup_user_rooms(user_id, room_ids)
        
        logger.info(f"User {user_id} disconnected")
    
    async def send_personal_message(self, message: dict, user_id: int):
        """Send message to a specific user"""
        connection_id = self.user_connections.get(user_id)
        if connection_id and connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(json.dumps(message))
                return True
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {e}")
                # Connection might be broken, cleanup
                await self.disconnect(user_id)
                return False
        return False
    
    async def send_room_message(self, message: dict, room_id: int, exclude_user_id: Optional[int] = None):
        """Send message to all users in a room"""
        room_users = await redis_manager.get_room_users(room_id)
        
        sent_count = 0
        for user_id in room_users:
            if exclude_user_id and user_id == exclude_user_id:
                continue
            
            if await self.send_personal_message(message, user_id):
                sent_count += 1
        
        logger.info(f"Sent room message to {sent_count} users in room {room_id}")
        return sent_count
    
    async def send_private_message(self, message: dict, sender_id: int, recipient_id: int):
        """Send private message between two users"""
        # Send to both sender and recipient
        results = []
        for user_id in [sender_id, recipient_id]:
            result = await self.send_personal_message(message, user_id)
            results.append(result)
        
        return all(results)
    
    async def join_room(self, user_id: int, room_id: int):
        """Add user to a room"""
        await redis_manager.add_user_to_room(room_id, user_id)
        
        # Update user's room list in Redis
        user_connection_info = await redis_manager.get_user_connection(user_id)
        if user_connection_info:
            room_ids = user_connection_info.get("room_ids", [])
            if room_id not in room_ids:
                room_ids.append(room_id)
                await redis_manager.set_user_connection(
                    user_id, 
                    user_connection_info["connection_id"], 
                    room_ids
                )
        
        logger.info(f"User {user_id} joined room {room_id}")
    
    async def leave_room(self, user_id: int, room_id: int):
        """Remove user from a room"""
        await redis_manager.remove_user_from_room(room_id, user_id)
        
        # Update user's room list in Redis
        user_connection_info = await redis_manager.get_user_connection(user_id)
        if user_connection_info:
            room_ids = user_connection_info.get("room_ids", [])
            if room_id in room_ids:
                room_ids.remove(room_id)
                await redis_manager.set_user_connection(
                    user_id, 
                    user_connection_info["connection_id"], 
                    room_ids
                )
        
        logger.info(f"User {user_id} left room {room_id}")
    
    async def get_active_users_count(self) -> int:
        """Get count of active users"""
        return len(self.user_connections)
    
    async def get_room_users_count(self, room_id: int) -> int:
        """Get count of active users in a room"""
        room_users = await redis_manager.get_room_users(room_id)
        return len(room_users)
    
    def is_user_connected(self, user_id: int) -> bool:
        """Check if user is currently connected"""
        return user_id in self.user_connections

# Global WebSocket manager instance
websocket_manager = WebSocketManager()