import json
from uuid import UUID
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status, HTTPException

from app.dependencies.auth_dependencies import get_current_user_from_websocket
from app.dependencies.service_dependencies import get_chat_service, get_websocket_manager
from app.models.user import User
from app.core.log_config import logger
from app.services.chat_service import ChatService
from app.utils.websocket_manager import WebsocketManager
from app.schemas.message import MessageCreateRequest, MessageType

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("")
async def websocket_endpoint(
    websocket: WebSocket,
    user: User = Depends(get_current_user_from_websocket),
    manager: WebsocketManager = Depends(get_websocket_manager),
    chat_service: ChatService = Depends(get_chat_service),
):
    if user is None:
        logger.warning("WebSocket connection rejected: invalid token provided.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return

    await manager.connect(websocket, user.id)
    logger.info(f"User {user.username} ({user.id}) connected via WebSocket.")
    joined_rooms = set()

    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Data received from {user.username} ({user.id}): {data}")
            
            try:
                message_data = json.loads(data)
                msg_type = message_data.get("type")
                if not msg_type:
                    logger.warning(f"Message from {user.username} is missing 'type' field: {data}")
                    continue
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from {user.username}: {data}")
                continue

            if msg_type == "send_message":
                content = message_data.get("content")
                if not content:
                    continue

                logger.info(f"Processing 'send_message' from {user.username}")
                room_id_str = message_data.get("room_id")
                target_user_id_str = message_data.get("target_user_id")
                msg_type_enum = MessageType(message_data.get("message_type", "text"))

                try:
                    if room_id_str:
                        create_request = MessageCreateRequest(
                            room_id=UUID(room_id_str), content=content, message_type=msg_type_enum
                        )
                        await chat_service.send_message(user, create_request)
                    elif target_user_id_str:
                        await chat_service.send_private_message(
                            sender=user,
                            target_user_id=UUID(target_user_id_str),
                            content=content,
                            message_type=msg_type_enum,
                        )
                except HTTPException as e:
                    logger.warning(f"HTTPException while sending message for {user.username}: {e.detail}")
                    error_payload = {"type": "error", "data": {"detail": e.detail, "status_code": e.status_code}}
                    await websocket.send_text(json.dumps(error_payload))

            elif msg_type == "messages_delivered":
                message_ids = [UUID(mid) for mid in message_data.get("message_ids", [])]
                logger.debug(f"User {user.username} marked messages as delivered: {message_ids}")
                if message_ids:
                    await chat_service.mark_messages_as_delivered(message_ids, user.id)

            elif msg_type == "messages_seen":
                message_ids = [UUID(mid) for mid in message_data.get("message_ids", [])]
                logger.debug(f"User {user.username} marked messages as seen: {message_ids}")
                if message_ids:
                    await chat_service.mark_messages_as_seen(message_ids, user.id)

            elif msg_type == "join_room":
                room_id = UUID(message_data.get("room_id"))
                logger.info(f"User {user.username} joining room {room_id}")
                await manager.join_room(user.id, room_id)
                joined_rooms.add(room_id)
                join_payload = {
                    "type": "user_joined_room",
                    "data": {"room_id": str(room_id), "user_id": str(user.id), "username": user.username},
                }
                await manager.broadcast_to_room(room_id, json.dumps(join_payload))

            elif msg_type == "leave_room":
                room_id = UUID(message_data.get("room_id"))
                if room_id in joined_rooms:
                    logger.info(f"User {user.username} leaving room {room_id}")
                    await manager.leave_room(user.id, room_id)
                    joined_rooms.discard(room_id)
                    leave_payload = {
                        "type": "user_left_room",
                        "data": {"room_id": str(room_id), "user_id": str(user.id), "username": user.username},
                    }
                    await manager.broadcast_to_room(room_id, json.dumps(leave_payload))

            elif msg_type == "typing":
                room_id = UUID(message_data.get("room_id"))
                logger.debug(f"User {user.username} is typing in room {room_id}")
                typing_payload = {
                    "type": "typing_indicator",
                    "data": {
                        "room_id": str(room_id),
                        "user_id": str(user.id),
                        "username": user.username,
                        "is_typing": message_data.get("is_typing", True),
                    },
                }
                await manager.broadcast_to_room(room_id, json.dumps(typing_payload))

    except WebSocketDisconnect as e:
        logger.info(f"User {user.username} disconnected. Code: {e.code}, Reason: {e.reason}")
        for room_id in joined_rooms:
            await manager.leave_room(user.id, room_id)
            leave_payload = {
                "type": "user_left_room",
                "data": {"room_id": str(room_id), "user_id": str(user.id), "username": user.username},
            }
            await manager.broadcast_to_room(room_id, json.dumps(leave_payload))
        await manager.disconnect(user.id)

    except Exception as e:
        logger.error(f"An unhandled error occurred in websocket for {user.username} ({user.id}): {e}", exc_info=True)
        for room_id in joined_rooms:
            await manager.leave_room(user.id, room_id)
        await manager.disconnect(user.id)