from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.exceptions import InvalidCredentialsException, UserAlreadyExistsException
from app.models.user import User
from app.core.security import hash_password, verify_password, create_access_token
from app.schemas.auth import RegisterRequest, LoginRequest
from fastapi import HTTPException, status


class AuthService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def register_user(self, request: RegisterRequest):
        """
        Handles the logic for registering a user.
        
        Args:
            request: Registration data
            
        Returns:
            A tuple (user, access_token)
        """
        existing_user = await self.db_session.execute(
            select(User).filter(
                (User.username == request.username) | (User.email == request.email)
            )
        )
        if existing_user.scalar():
            raise UserAlreadyExistsException()
        
        user = User(
            username=request.username,
            display_name=request.display_name,
            email=request.email,
            hashed_password=hash_password(request.password)
        )
        self.db_session.add(user)
        await self.db_session.commit()
        await self.db_session.refresh(user)

        access_token = create_access_token(
            data={
                "user_id": str(user.id),
                "username": user.username,
                "display_name": user.display_name
            }
        )

        return user, access_token

    async def login_user(self, request: LoginRequest):
        """
        Handles the logic for logging in a user.
        
        Args:
            request: Login credentials
            
        Returns:
            A tuple (user, access_token)
        """
        user = await self.db_session.execute(
            select(User).filter(User.username == request.username)
        )
        user = user.scalar_one_or_none()
        
        if not user or not verify_password(request.password, user.hashed_password):
            raise InvalidCredentialsException()
        
        access_token = create_access_token(
            data={
                "user_id": str(user.id),
                "username": user.username,
                "display_name": user.display_name
            }
        )

        return user, access_token
