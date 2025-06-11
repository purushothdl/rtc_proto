from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.dependencies.auth_dependencies import get_auth_service, get_current_user
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Register a new user.
    """
    user, access_token = await auth_service.register_user(request)
    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        username=user.username,
        display_name=user.display_name
    )

@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Authenticate a user and return a JWT.
    """
    user, access_token = await auth_service.login_user(request)
    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        username=user.username,
        display_name=user.display_name
    )

@router.get("/me")
async def protected_route(current_user: User = Depends(get_current_user)):
    """
    Get the current authenticated user's details.
    """
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email
    }