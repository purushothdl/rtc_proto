import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.auth_service import AuthService
from app.schemas.auth import RegisterRequest, LoginRequest
from app.models.user import User
from app.core.exceptions import UserAlreadyExistsException, InvalidCredentialsException

@pytest.mark.asyncio
async def test_register_user(test_db: AsyncSession):
    auth_service = AuthService(test_db)
    request = RegisterRequest(
        username="testuser",
        display_name="Test User",
        email="test@example.com",
        password="password123"
    )
    user, token = await auth_service.register_user(request)
    assert user.username == "testuser"
    assert token is not None

@pytest.mark.asyncio
async def test_login_user(test_db: AsyncSession, test_user: User):
    auth_service = AuthService(test_db)
    request = LoginRequest(
        username=test_user.username,
        password="password123"
    )
    user, token = await auth_service.login_user(request)
    assert user.id == test_user.id
    assert token is not None 