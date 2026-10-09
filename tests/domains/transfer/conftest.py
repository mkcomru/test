from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config.settings import get_settings
from src.common.database import BaseModel
from src.transfer.repository import TransferRepository
from src.transfer.service import TransferService


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with maker() as db_session:
        yield db_session
    await engine.dispose()


@pytest.fixture
def service(session: AsyncSession) -> TransferService:
    return TransferService(TransferRepository(session), get_settings())


class FakeResponse:
    def __init__(self, status_code: int = 200):
        self._response = httpx.Response(
            status_code, request=httpx.Request("POST", "http://webhook.test/hook")
        )

    def raise_for_status(self) -> None:
        self._response.raise_for_status()


@pytest.fixture
def webhook_capture(monkeypatch: pytest.MonkeyPatch) -> dict:
    calls: list[dict] = []
    script: list = []

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, *exc_info) -> bool:
            return False

        async def post(self, url, content=None, headers=None) -> FakeResponse:
            calls.append({"url": url, "content": content, "headers": headers})
            if script:
                behavior = script.pop(0)
                if isinstance(behavior, Exception):
                    raise behavior
                return FakeResponse(behavior)
            return FakeResponse(200)

    monkeypatch.setattr("src.transfer.service.httpx.AsyncClient", FakeAsyncClient)
    return {"calls": calls, "script": script}


@pytest.fixture
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _no_sleep(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr("src.transfer.service.asyncio.sleep", _no_sleep)
