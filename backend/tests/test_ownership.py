"""Регрессии на разграничение доступа между пользователями.

До появления ``app.core.ownership`` роутеры доставали объекты через
``session.get(Model, id)`` без фильтра по владельцу: любой авторизованный
пользователь мог прочитать и изменить чужие данные, зная UUID.
Каждый тест ниже проверяет один такой путь.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import first_week_id


async def test_cannot_read_another_users_week(
    alice: AsyncClient, bob: AsyncClient, session: AsyncSession
):
    week_id = await first_week_id(alice, session)

    assert (await alice.get(f"/api/v1/weeks/{week_id}")).status_code == 200
    assert (await bob.get(f"/api/v1/weeks/{week_id}")).status_code == 404


async def test_cannot_create_mark_in_another_users_week(
    alice: AsyncClient, bob: AsyncClient, session: AsyncSession
):
    week_id = await first_week_id(alice, session)

    r = await bob.post(f"/api/v1/weeks/{week_id}/marks", json={"title": "Чужая пометка"})
    assert r.status_code == 404

    week = (await alice.get(f"/api/v1/weeks/{week_id}")).json()
    assert week["marks"] == []


async def test_cannot_update_another_users_mark(
    alice: AsyncClient, bob: AsyncClient, session: AsyncSession
):
    week_id = await first_week_id(alice, session)
    mark_id = (
        await alice.post(f"/api/v1/weeks/{week_id}/marks", json={"title": "Моя пометка"})
    ).json()["id"]

    r = await bob.patch(f"/api/v1/marks/{mark_id}", json={"title": "Захвачено"})
    assert r.status_code == 404

    week = (await alice.get(f"/api/v1/weeks/{week_id}")).json()
    assert week["marks"][0]["title"] == "Моя пометка"


async def test_cannot_delete_another_users_mark(
    alice: AsyncClient, bob: AsyncClient, session: AsyncSession
):
    week_id = await first_week_id(alice, session)
    mark_id = (
        await alice.post(f"/api/v1/weeks/{week_id}/marks", json={"title": "Моя пометка"})
    ).json()["id"]

    assert (await bob.delete(f"/api/v1/marks/{mark_id}")).status_code == 404
    assert len((await alice.get(f"/api/v1/weeks/{week_id}")).json()["marks"]) == 1


async def test_cannot_touch_another_users_week_task(
    alice: AsyncClient, bob: AsyncClient, session: AsyncSession
):
    week_id = await first_week_id(alice, session)
    task_id = (
        await alice.post(f"/api/v1/weeks/{week_id}/tasks", json={"title": "Моя задача"})
    ).json()["id"]

    assert (
        await bob.patch(f"/api/v1/week-tasks/{task_id}", json={"status": "done"})
    ).status_code == 404
    assert (await bob.delete(f"/api/v1/week-tasks/{task_id}")).status_code == 404

    week = (await alice.get(f"/api/v1/weeks/{week_id}")).json()
    assert week["week_tasks"][0]["status"] == "todo"


async def test_cannot_touch_another_users_day_task(
    alice: AsyncClient, bob: AsyncClient, session: AsyncSession
):
    week_id = await first_week_id(alice, session)
    task_id = (
        await alice.post(f"/api/v1/weeks/{week_id}/days/0/tasks", json={"title": "Понедельник"})
    ).json()["id"]

    assert (
        await bob.patch(f"/api/v1/day-tasks/{task_id}", json={"title": "Захвачено"})
    ).status_code == 404
    assert (await bob.delete(f"/api/v1/day-tasks/{task_id}")).status_code == 404


async def test_cannot_move_own_task_into_another_users_week(
    alice: AsyncClient, bob: AsyncClient, session: AsyncSession
):
    """Проверяется целевая неделя, а не только сама задача."""
    alice_week = await first_week_id(alice, session)
    bob_week = await first_week_id(bob, session)

    task_id = (
        await bob.post(f"/api/v1/weeks/{bob_week}/tasks", json={"title": "Задача Боба"})
    ).json()["id"]

    r = await bob.patch(
        f"/api/v1/week-tasks/{task_id}/move", json={"target_week_id": alice_week}
    )
    assert r.status_code == 404

    assert (await alice.get(f"/api/v1/weeks/{alice_week}")).json()["week_tasks"] == []


async def test_cannot_update_another_users_theme(alice: AsyncClient, bob: AsyncClient):
    theme_id = (await alice.get("/api/v1/themes")).json()[0]["id"]

    assert (
        await bob.patch(f"/api/v1/themes/{theme_id}", json={"name": "Захвачено"})
    ).status_code == 404
    assert (await bob.delete(f"/api/v1/themes/{theme_id}")).status_code == 404

    assert theme_id in {t["id"] for t in (await alice.get("/api/v1/themes")).json()}


async def test_cannot_start_review_on_another_users_week(
    alice: AsyncClient, bob: AsyncClient, session: AsyncSession
):
    week_id = await first_week_id(alice, session)
    r = await bob.post(f"/api/v1/weeks/{week_id}/review/start")
    assert r.status_code == 404


async def test_cannot_complete_review_on_another_users_week(
    alice: AsyncClient, bob: AsyncClient, session: AsyncSession
):
    week_id = await first_week_id(alice, session)
    await alice.post(f"/api/v1/weeks/{week_id}/tasks", json={"title": "Не закрыта"})

    r = await bob.post(f"/api/v1/weeks/{week_id}/review/complete")
    assert r.status_code == 404

    # Задача Алисы осталась открытой.
    week = (await alice.get(f"/api/v1/weeks/{week_id}")).json()
    assert week["week_tasks"][0]["status"] == "todo"


async def test_users_see_only_their_own_themes(alice: AsyncClient, bob: AsyncClient):
    await alice.post("/api/v1/themes", json={"name": "Только Алисы", "color": "#111111"})

    bob_themes = {t["name"] for t in (await bob.get("/api/v1/themes")).json()}
    assert "Только Алисы" not in bob_themes
