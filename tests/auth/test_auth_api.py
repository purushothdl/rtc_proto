import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database.postgres import get_db_session
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.core.security import create_access_token

@pytest.fixture(autouse=True)
def override_get_db_session(async_session):
    async def _override():
        yield async_session
    app.dependency_overrides[get_db_session] = _override
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.fixture
async def async_test_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_register_user_success(async_test_client):
    response = await async_test_client.post(
        "/api/auth/register",
        json={
            "username": "newuser",
            "display_name": "New User",
            "email": "new@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["username"] == "newuser"
    assert data["display_name"] == "New User"

@pytest.mark.asyncio
async def test_register_user_duplicate(async_test_client, test_user):
    response = await async_test_client.post(
        "/api/auth/register",
        json={
            "username": test_user.username,
            "display_name": "Duplicate User",
            "email": "duplicate@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 400
    assert "detail" in response.json()

@pytest.mark.asyncio
async def test_login_user_success(async_test_client, test_user):
    response = await async_test_client.post(
        "/api/auth/login",
        json={
            "username": test_user.username,
            "password": "password123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["username"] == test_user.username
    assert data["user_id"] == str(test_user.id)

@pytest.mark.asyncio
async def test_login_user_invalid_credentials(async_test_client, test_user):
    response = await async_test_client.post(
        "/api/auth/login",
        json={
            "username": test_user.username,
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    assert "detail" in response.json()

@pytest.mark.asyncio
async def test_protected_route_success(async_test_client, test_user, test_token):
    response = await async_test_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user.username
    assert data["email"] == test_user.email
    assert data["user_id"] == str(test_user.id)

@pytest.mark.asyncio
async def test_protected_route_invalid_token(async_test_client):
    response = await async_test_client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_protected_route_no_token(async_test_client):
    response = await async_test_client.get("/api/auth/me")
    assert response.status_code in (401, 403)