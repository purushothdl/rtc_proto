from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.postgres import get_db_session
from app.services.auth_service import AuthService

async def get_auth_service(db: AsyncSession = Depends(get_db_session)):
    """
    Dependency that provides an instance of AuthService with an active database session.
    """
    async with db as session:
        yield AuthService(session)
