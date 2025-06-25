from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.dependencies.auth_dependencies import get_current_user
from app.database.postgres import get_db_session
from app.models.user import User
from app.schemas.user import FCMTokenCreate
from app.services.notification_service import NotificationService 
from app.dependencies.service_dependencies import get_notification_service 

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@router.post("/register-fcm-token", status_code=status.HTTP_204_NO_CONTENT)
async def register_fcm_token(
    request: FCMTokenCreate,
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    Registers or updates an FCM token for the authenticated user.
    """
    await notification_service.register_fcm_token(
        user_id=current_user.id, 
        token=request.token, 
        device_type=request.device_type
    )