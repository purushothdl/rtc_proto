from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.postgres import get_db_session
from app.services.auth_service import AuthService


