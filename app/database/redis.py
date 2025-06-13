# app/database/redis.py
import redis.asyncio as redis
from typing import Optional
import json
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisManager:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
    
    async def connect(self):
        """Initialize Redis connection"""
        try:
            self.redis = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30,
            )
            # Test connection
            await self.redis.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")
    
    async def set_user_connection(self, user_id: int, connection_id: str, room_ids: list = None):
        """Store user's WebSocket connection info"""
        connection_data = {
            "connection_id": connection_id,
            "room_ids": room_ids or [],
            "connected_at": str(int(__import__('time').time()))
        }
        await self.redis.hset(
            f"user_connections", 
            str(user_id), 
            json.dumps(connection_data)
        )
    
    async def remove_user_connection(self, user_id: int):
        """Remove user's WebSocket connection info"""
        await self.redis.hdel("user_connections", str(user_id))
    
    async def get_user_connection(self, user_id: int) -> Optional[dict]:
        """Get user's WebSocket connection info"""
        data = await self.redis.hget("user_connections", str(user_id))
        return json.loads(data) if data else None
    
    async def add_user_to_room(self, room_id: int, user_id: int):
        """Add user to a room's active users set"""
        await self.redis.sadd(f"room:{room_id}:users", str(user_id))
    
    async def remove_user_from_room(self, room_id: int, user_id: int):
        """Remove user from a room's active users set"""
        await self.redis.srem(f"room:{room_id}:users", str(user_id))
    
    async def get_room_users(self, room_id: int) -> list:
        """Get all active users in a room"""
        users = await self.redis.smembers(f"room:{room_id}:users")
        return [int(user_id) for user_id in users]
    
    async def get_all_connected_users(self) -> dict:
        """Get all connected users"""
        users_data = await self.redis.hgetall("user_connections")
        return {
            int(user_id): json.loads(data) 
            for user_id, data in users_data.items()
        }
    
    async def cleanup_user_rooms(self, user_id: int, room_ids: list):
        """Remove user from all rooms they were in"""
        for room_id in room_ids:
            await self.remove_user_from_room(room_id, user_id)

# Global Redis manager instance
redis_manager = RedisManager()