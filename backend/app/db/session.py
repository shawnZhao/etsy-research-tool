import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

_engine = None
_engine_loop = None
_async_session = None


def _get_async_session():
    global _engine, _engine_loop, _async_session

    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _engine is not None and _engine_loop is not current_loop:
        _engine = None
        _async_session = None

    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False)
        _engine_loop = current_loop
        _async_session = async_sessionmaker(_engine, expire_on_commit=False)

    return _async_session


async def get_db() -> AsyncSession:
    sessionmaker = _get_async_session()
    async with sessionmaker() as session:
        yield session


def get_engine():
    """Return the current async engine, creating it if needed."""
    _get_async_session()
    return _engine
