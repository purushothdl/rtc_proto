from fastapi import Depends, HTTPException, status, Query, WebSocket
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.postgres import get_db_session
from app.models.user import User
from app.core.security import verify_token
from app.core.exceptions import UnauthorizedAccessException, InvalidTokenException

security = HTTPBearer()

async def _get_user_from_token(token: str, db: AsyncSession) -> User:
    """
    Internal helper to verify a token and fetch the corresponding user.
    This contains the core logic shared by HTTP and WebSocket auth.
    """
    if not token:
        raise InvalidTokenException(detail="Token not provided")
        
    try:
        payload = verify_token(token)
        user_id = payload.get("user_id")
        if user_id is None:
            raise InvalidTokenException()
    except InvalidTokenException:
        raise InvalidTokenException()
    
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise UnauthorizedAccessException(detail="User not found")
    
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """
    Dependency for standard HTTP routes to get the current user from a Bearer token.
    """
    return await _get_user_from_token(credentials.credentials, db)


async def get_current_user_from_websocket(
    websocket: WebSocket,
    token: str = Query(...), 
    db: AsyncSession = Depends(get_db_session)
) -> User | None:
    """
    Dependency for WebSocket routes to get the current user from a token
    in the query parameters. Returns None on failure to allow the endpoint
    to close the connection gracefully.
    """
    try:
        return await _get_user_from_token(token, db)
    except (InvalidTokenException, UnauthorizedAccessException):
        return None