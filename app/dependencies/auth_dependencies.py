# app/dependencies/auth_dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.postgres import get_db_session
from app.models.user import User
from app.core.security import verify_token
from app.core.exceptions import UnauthorizedAccessException, InvalidTokenException
from app.services.auth_service import AuthService

security = HTTPBearer()

def get_auth_service(db: AsyncSession = Depends(get_db_session)) -> AuthService:
    """
    Dependency that provides an instance of AuthService with an active database session.
    """
    return AuthService(db)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """
    Dependency to get the current authenticated user from the JWT token.
    
    Args:
        credentials: HTTP Bearer token credentials
        db: Database session
        
    Returns:
        The authenticated User object
        
    Raises:
        UnauthorizedAccessException: If the user is not found
        InvalidTokenException: If the token is invalid
    """
    try:
        payload = verify_token(credentials.credentials)
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

