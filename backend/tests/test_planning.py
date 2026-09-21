"""Основной сценарий планирования: пометки, задачи недели и дня, счётчик загрузки."""

from datetime import datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import first_week_id

# Сид создаёт год по системной дате, поэтому год в путях берём оттуда же.
CURRENT_YEAR = datetime.now().year


async def test_create_mark_and_read_it_back(alice: AsyncClient, session: AsyncSession):
    week_id = await first_week_id(alice, session)

    r = await alice.post(f"/api/v1/weeks/{week_id}/marks", json={"title": "Запустить сайт"})
    assert r.status_code == 200, r.text
    mark = r.json()
    assert mark["title"] == "Запустить сайт"
    assert mark["position"] == 0

    week = (await alice.get(f"/api/v1/weeks/{week_id}")).json()
    assert [m["id"] for m in week["marks"]] == [mark["id"]]


async def test_marks_get_sequential_positions(alice: AsyncClient, session: AsyncSession):
    week_id = await first_week_id(alice, session)

    positions = []
    for title in ("Первая", "Вторая", "Третья"):
        r = await alice.post(f"/api/v1/weeks/{week_id}/marks", json={"title": title})
        positions.append(r.json()["position"])

    assert positions == [0, 1, 2]


async def test_cached_load_counts_only_open_tasks(alice: AsyncClient, session: AsyncSession):
    """cached_load — это число задач в статусе todo; done и cancelled не считаются."""
    week_id = await first_week_id(alice, session)

    task_ids = []
    for title in ("A", "B", "C"):
        r = await alice.post(f"/api/v1/weeks/{week_id}/tasks", json={"title": title})
        assert r.status_code == 200, r.text
        task_ids.append(r.json()["id"])

    assert (await alice.get(f"/api/v1/weeks/{week_id}")).json()["cached_load"] == 3

    r = await alice.patch(f"/api/v1/week-tasks/{task_ids[0]}", json={"status": "done"})
    assert r.status_code == 200, r.text
    assert (await alice.get(f"/api/v1/weeks/{week_id}")).json()["cached_load"] == 2

    r = await alice.delete(f"/api/v1/week-tasks/{task_ids[1]}")
    assert r.status_code == 200, r.text
    assert (await alice.get(f"/api/v1/weeks/{week_id}")).json()["cached_load"] == 1


async def test_delete_is_soft_and_hides_task(alice: AsyncClient, session: AsyncSession):
    week_id = await first_week_id(alice, session)
    task_id = (
        await alice.post(f"/api/v1/weeks/{week_id}/tasks", json={"title": "Удалить меня"})
    ).json()["id"]

    await alice.delete(f"/api/v1/week-tasks/{task_id}")

    week = (await alice.get(f"/api/v1/weeks/{week_id}")).json()
    assert week["week_tasks"] == []

    # Задача помечена удалённой, поэтому повторное обращение к ней даёт 404.
    r = await alice.patch(f"/api/v1/week-tasks/{task_id}", json={"title": "Воскресить"})
    assert r.status_code == 404


async def test_move_week_task_updates_load_on_both_weeks(alice: AsyncClient, session: AsyncSession):
    year = (await alice.get(f"/api/v1/years/{CURRENT_YEAR}")).json()
    weeks = year["quarters"][0]["weeks"]
    source, target = weeks[0]["id"], weeks[1]["id"]

    task_id = (
        await alice.post(f"/api/v1/weeks/{source}/tasks", json={"title": "Переезжает"})
    ).json()["id"]
    assert (await alice.get(f"/api/v1/weeks/{source}")).json()["cached_load"] == 1

    r = await alice.patch(
        f"/api/v1/week-tasks/{task_id}/move", json={"target_week_id": target}
    )
    assert r.status_code == 200, r.text

    assert (await alice.get(f"/api/v1/weeks/{source}")).json()["cached_load"] == 0
    assert (await alice.get(f"/api/v1/weeks/{target}")).json()["cached_load"] == 1


async def test_day_task_rejects_day_out_of_range(alice: AsyncClient, session: AsyncSession):
    week_id = await first_week_id(alice, session)
    r = await alice.post(f"/api/v1/weeks/{week_id}/days/9/tasks", json={"title": "Восьмой день"})
    assert r.status_code == 422


async def test_deleting_mark_with_detach_keeps_tasks(alice: AsyncClient, session: AsyncSession):
    week_id = await first_week_id(alice, session)
    mark_id = (
        await alice.post(f"/api/v1/weeks/{week_id}/marks", json={"title": "Пометка"})
    ).json()["id"]
    await alice.post(
        f"/api/v1/weeks/{week_id}/tasks", json={"title": "Задача", "mark_id": mark_id}
    )

    r = await alice.delete(f"/api/v1/marks/{mark_id}?cascade=detach")
    assert r.status_code == 200, r.text

    week = (await alice.get(f"/api/v1/weeks/{week_id}")).json()
    assert week["marks"] == []
    assert len(week["week_tasks"]) == 1
    assert week["week_tasks"][0]["mark_id"] is None


async def test_deleting_mark_with_cascade_removes_tasks(alice: AsyncClient, session: AsyncSession):
    week_id = await first_week_id(alice, session)
    mark_id = (
        await alice.post(f"/api/v1/weeks/{week_id}/marks", json={"title": "Пометка"})
    ).json()["id"]
    await alice.post(
        f"/api/v1/weeks/{week_id}/tasks", json={"title": "Задача", "mark_id": mark_id}
    )

    r = await alice.delete(f"/api/v1/marks/{mark_id}?cascade=delete")
    assert r.status_code == 200, r.text

    week = (await alice.get(f"/api/v1/weeks/{week_id}")).json()
    assert week["marks"] == []
    assert week["week_tasks"] == []


async def test_quarter_note_roundtrip(alice: AsyncClient):
    r = await alice.put(
        f"/api/v1/years/{CURRENT_YEAR}/quarters/1/note", json={"content": "Цель квартала"}
    )
    assert r.status_code == 200, r.text

    r = await alice.get(f"/api/v1/years/{CURRENT_YEAR}/quarters/1/note")
    assert r.json()["content"] == "Цель квартала"


async def test_unknown_id_returns_404_not_500(alice: AsyncClient):
    """Раньше несуществующий ID падал в 500 на обращении к None."""
    r = await alice.patch(
        "/api/v1/week-tasks/00000000-0000-0000-0000-000000000000", json={"title": "x"}
    )
    assert r.status_code == 404


async def test_malformed_uuid_returns_404_not_500(alice: AsyncClient):
    r = await alice.get("/api/v1/weeks/not-a-uuid")
    assert r.status_code == 404
