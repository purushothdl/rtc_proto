import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from app.dependencies.auth_dependencies import get_current_user
from app.core.exceptions import InvalidTokenException, UnauthorizedAccessException
from app.models.user import User

@pytest.mark.asyncio
async def test_get_current_user_valid_token(test_db, test_user, test_token):
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=test_token)
    user = await get_current_user(credentials, test_db)
    assert user.id == test_user.id

@pytest.mark.asyncio
async def test_get_current_user_invalid_token(test_db):
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid_token")
    with pytest.raises(InvalidTokenException):
        await get_current_user(credentials, test_db) 