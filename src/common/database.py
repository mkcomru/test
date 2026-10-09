from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config.settings import get_settings

settings = get_settings()

class BaseModel(DeclarativeBase):
    pass


engine = create_async_engine(settings.database.url, echo=settings.debug, pool_size=10, max_overflow=20)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session