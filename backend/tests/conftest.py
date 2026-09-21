"""Общие фикстуры.

Приложение создаёт движок БД на уровне импорта модуля ``app.core.db``,
поэтому переменные окружения выставляются здесь до любых импортов ``app.*``.
Тесты идут на файловой SQLite: in-memory не подходит, потому что
``create_async_engine`` отдаёт каждому соединению свою пустую базу.
"""

import os
import tempfile
from pathlib import Path

import pytest

_DB_FILE = Path(tempfile.gettempdir()) / "calendar52_test.db"

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB_FILE.as_posix()}"
os.environ["DATABASE_URL_SYNC"] = f"sqlite:///{_DB_FILE.as_posix()}"
os.environ["SECRET_KEY"] = "test-secret-key-not-used-anywhere-else"
os.environ["APP_ENV"] = "test"
os.environ["ANTHROPIC_API_KEY"] = ""

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.db import Base, async_session_maker, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Year  # noqa: E402


@pytest.fixture(autouse=True)
async def _database() -> None:
    """Чистая схема на каждый тест — изоляция важнее скорости на таком объёме."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def session() -> AsyncSession:
    async with async_session_maker() as s:
        yield s


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def register_and_login(client: AsyncClient, email: str, password: str = "Passw0rd!123") -> None:
    """Зарегистрировать пользователя и залогинить его в переданный клиент.

    Куку ставит сам fastapi-users, httpx сохраняет её в клиенте,
    поэтому дальше запросы этого клиента идут от имени пользователя.
    """
    r = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": password}
    )
    assert r.status_code == 201, r.text

    r = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert r.status_code in (200, 204), r.text


@pytest.fixture
async def alice(client: AsyncClient) -> AsyncClient:
    """Основной пользователь, уже залогиненный."""
    await register_and_login(client, "alice@example.com")
    return client


@pytest.fixture
async def bob() -> AsyncClient:
    """Второй пользователь на отдельном клиенте — для проверок доступа к чужим данным."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        await register_and_login(c, "bob@example.com")
        yield c


async def first_week_id(authed: AsyncClient, session: AsyncSession) -> str:
    """ID первой недели текущего года у пользователя этого клиента.

    Год и 52 недели создаются сидом при регистрации.
    """
    from sqlalchemy import select

    me = await authed.get("/api/v1/users/me")
    assert me.status_code == 200, me.text
    user_id = me.json()["id"]

    year = (
        await session.execute(select(Year).where(Year.user_id == user_id))
    ).scalars().first()
    assert year is not None, "сид не создал год при регистрации"

    detail = await authed.get(f"/api/v1/years/{year.year_number}")
    assert detail.status_code == 200, detail.text
    return detail.json()["quarters"][0]["weeks"][0]["id"]
