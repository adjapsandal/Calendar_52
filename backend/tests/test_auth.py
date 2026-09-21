"""Регистрация, вход и разграничение доступа к защищённым эндпоинтам."""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seed import DEFAULT_THEMES
from app.models import Settings, Week, Year


async def test_health_is_public(client: AsyncClient):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_protected_endpoint_rejects_anonymous(client: AsyncClient):
    r = await client.get("/api/v1/themes")
    assert r.status_code == 401


async def test_register_then_login_sets_cookie(client: AsyncClient):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "Passw0rd!123"},
    )
    assert r.status_code == 201

    r = await client.post(
        "/api/v1/auth/login",
        data={"username": "new@example.com", "password": "Passw0rd!123"},
    )
    assert r.status_code in (200, 204)
    assert "calendar52_auth" in client.cookies


async def test_login_with_wrong_password_fails(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "wrong@example.com", "password": "Passw0rd!123"},
    )
    r = await client.post(
        "/api/v1/auth/login",
        data={"username": "wrong@example.com", "password": "not-the-password"},
    )
    assert r.status_code == 400


async def test_registration_seeds_year_with_52_weeks(alice: AsyncClient, session: AsyncSession):
    """Сид должен создать год, 52 недели, настройки и темы по умолчанию."""
    me = (await alice.get("/api/v1/users/me")).json()

    year = (
        await session.execute(select(Year).where(Year.user_id == me["id"]))
    ).scalars().one()

    weeks = (
        await session.execute(select(Week).where(Week.year_id == year.id))
    ).scalars().all()
    assert len(weeks) == 52

    # 4 квартала по 13 недель, последняя неделя каждого квартала — на отдых.
    assert sorted(w.display_position for w in weeks) == list(range(1, 53))
    assert sum(w.is_rest_week for w in weeks) == 4

    settings = (
        await session.execute(select(Settings).where(Settings.user_id == me["id"]))
    ).scalars().one()
    assert settings.week_budget == 10

    themes = (await alice.get("/api/v1/themes")).json()
    assert {t["name"] for t in themes} == {name for name, _ in DEFAULT_THEMES}
