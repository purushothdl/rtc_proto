import asyncio
from typing import Dict, Set
from uuid import UUID
from fastapi import WebSocket
import redis.asyncio as redis

# This channel is used to keep the pubsub connection alive and listening.
DUMMY_CHANNEL = "server-control-channel"


def get_room_channel(room_id: str) -> str:
    """Returns the Redis channel name for a specific room."""
    return f"room:{room_id}"

def get_user_channel(user_id: str) -> str:
    """Returns the Redis channel name for a specific user."""
    return f"user:{user_id}"

class WebsocketManager:
    """
    Manages WebSocket connections, room memberships, and Redis Pub/Sub messaging
    for real-time communication. This class is designed to be a singleton
    instance within the FastAPI application.
    """

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis_client: redis.Redis = None
        self.pubsub = None
        self.listener_task: asyncio.Task = None

        self.ONLINE_USERS_KEY = "online_users"

        self.active_connections: Dict[str, WebSocket] = {}
        self.local_room_members: Dict[str, Set[str]] = {}

    async def init_redis(self):
        """Initializes Redis client and starts the Pub/Sub listener task."""
        try:
            print(f"Attempting to connect to Redis at {self.redis_url}")
            self.redis_client = redis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )
            await self.redis_client.ping()
            print("Redis connection successful.")
        except Exception as e:
            print(f"!!! CRITICAL: FAILED TO CONNECT TO REDIS: {e}")
            raise e

        self.pubsub = self.redis_client.pubsub()
        await self.pubsub.subscribe(DUMMY_CHANNEL)
        self.listener_task = asyncio.create_task(self._pubsub_listener())

    async def close(self):
        """Closes all connections and stops the listener task."""
        if self.listener_task:
            self.listener_task.cancel()
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        if self.redis_client:
            await self.redis_client.close()
        print("WebsocketManager resources closed.")

    async def connect(self, websocket: WebSocket, user_id: UUID):
        """Accepts a new WebSocket connection for a user."""
        await websocket.accept()
        user_id_str = str(user_id)
        self.active_connections[user_id_str] = websocket

        await self.pubsub.subscribe(get_user_channel(user_id_str))
        print(f"User {user_id_str} connected. Subscribed to personal channel.")

        await self.redis_client.sadd(self.ONLINE_USERS_KEY, str(user_id))
        print(f"User {user_id_str} added to global online set.")

    async def disconnect(self, user_id: UUID):
        """Handles a user's disconnection, cleaning up all memberships."""
        user_id_str = str(user_id)
        if user_id_str in self.active_connections:
            del self.active_connections[user_id_str]
            await self.pubsub.unsubscribe(get_user_channel(user_id_str))
        
        # Clean up local room tracking
        rooms_to_unsubscribe = []
        for room_id, members in self.local_room_members.items():
            if user_id_str in members:
                members.discard(user_id_str)
                if not members:
                    rooms_to_unsubscribe.append(room_id)
        
        for room_id in rooms_to_unsubscribe:
            del self.local_room_members[room_id]
            await self.pubsub.unsubscribe(get_room_channel(room_id))
            print(f"Unsubscribed from room {room_id} channel (no local members left).")

        print(f"User {user_id_str} disconnected.")

        await self.redis_client.srem(self.ONLINE_USERS_KEY, str(user_id))
        print(f"User {user_id_str} removed from global online set.")

    async def get_globally_online_users(self) -> set[str]:
        """Returns a set of user IDs that are currently connected via WebSocket."""
        return await self.redis_client.smembers(self.ONLINE_USERS_KEY)

    async def join_room(self, user_id: UUID, room_id: UUID):
        """Adds a user to a room's local tracking and subscribes to the room channel if necessary."""
        user_id_str, room_id_str = str(user_id), str(room_id)
        if room_id_str not in self.local_room_members or not self.local_room_members[room_id_str]:
            await self.pubsub.subscribe(get_room_channel(room_id_str))
            print(f"This instance subscribed to room {room_id_str} channel.")
        
        self.local_room_members.setdefault(room_id_str, set()).add(user_id_str)
        print(f"User {user_id_str} joined room {room_id_str}.")

    async def leave_room(self, user_id: UUID, room_id: UUID):
        """Removes a user from a room's local tracking and unsubscribes if they were the last one."""
        user_id_str, room_id_str = str(user_id), str(room_id)
        if room_id_str in self.local_room_members:
            self.local_room_members[room_id_str].discard(user_id_str)
            if not self.local_room_members[room_id_str]:
                del self.local_room_members[room_id_str]
                await self.pubsub.unsubscribe(get_room_channel(room_id_str))
                print(f"This instance unsubscribed from room {room_id_str} channel.")
        print(f"User {user_id_str} left room {room_id_str}.")

    async def broadcast_to_room(self, room_id: UUID, message: str):
        """Publishes a message to a room's Redis channel for all instances to hear."""
        await self.redis_client.publish(get_room_channel(str(room_id)), message)

    async def send_personal_message(self, user_id: UUID, message: str):
        """Publishes a message to a specific user's Redis channel."""
        await self.redis_client.publish(get_user_channel(str(user_id)), message)

    async def _send_to_local_websocket(self, user_id: str, message: str):
        """Sends a message directly to a websocket connected to this instance."""
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            try:
                await websocket.send_text(message)
            except Exception:
                pass

    async def _pubsub_listener(self):
        """Listens for messages on Redis and routes them to the correct local clients."""
        print("Pub/Sub listener started.")
        try:
            async for message in self.pubsub.listen():
                if message["type"] != "message" or message["channel"] == DUMMY_CHANNEL:
                    continue

                channel = message["channel"]
                data = message["data"]
                
                if channel.startswith("room:"):
                    room_id = channel.split(":", 1)[1]
                    if room_id in self.local_room_members:
                        # Broadcast to all users in the room connected to THIS instance
                        tasks = [
                            self._send_to_local_websocket(user_id, data)
                            for user_id in self.local_room_members[room_id]
                        ]
                        await asyncio.gather(*tasks)

                elif channel.startswith("user:"):
                    user_id = channel.split(":", 1)[1]
                    await self._send_to_local_websocket(user_id, data)

        except asyncio.CancelledError:
            print("Pub/Sub listener task cancelled.")
        except Exception as e:
            print(f"!!! CRITICAL: Pub/Sub listener crashed: {e}")
        finally:
            print("Pub/Sub listener stopped.")