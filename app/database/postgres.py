# app/database/postgres.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.base import Base

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

async_session = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

async def get_db_session():
    """
    Provide a database session for dependency injection.
    
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def initialize_db():
    """
    Initialize the database by creating all tables defined in SQLAlchemy models.
    This method is idempotent and safe to run at startup.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
