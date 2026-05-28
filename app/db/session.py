from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config.settings import settings

# Create async engine with optimized pool settings for production
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Set to True only for query debugging in development
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,  # Test connection health on checkout to prevent stale connections
)

# Async session maker
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining a request-scoped async database session."""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
