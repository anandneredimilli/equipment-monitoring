from datetime import datetime, timezone

from app.repositories.event_repository import EventRepository
from tests.conftest import TestingSessionLocal

TASK_PAYLOAD = {
    "machine_id": "ETCH-001",
    "start_at": "2026-11-23T08:00:00Z",
    "stop_at": "2026-11-24T08:00:00Z",
    "interval_seconds": 300,
}


def seed_events(task_id: int) -> int:
    rows = [
        {
            "task_id": task_id,
            "machine_id": "ETCH-001",
            "cursor": 1,
            "event_code": "TEMP_HIGH",
            "severity": "WARNING",
            "event_timestamp": datetime(2026, 11, 19, 10, 0, tzinfo=timezone.utc),
        },
        {
            "task_id": task_id,
            "machine_id": "ETCH-001",
            "cursor": 2,
            "event_code": "PRESSURE_LOW",
            "severity": "CRITICAL",
            "event_timestamp": datetime(2026, 11, 19, 10, 5, tzinfo=timezone.utc),
        },
    ]
    with TestingSessionLocal() as db:
        return EventRepository(db).bulk_create(rows)


def test_list_events(client):
    task_id = client.post("/v1/tasks", json=TASK_PAYLOAD).json()["id"]
    seed_events(task_id)

    response = client.get("/v1/events")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_filter_events(client):
    task_id = client.post("/v1/tasks", json=TASK_PAYLOAD).json()["id"]
    seed_events(task_id)

    by_code = client.get("/v1/events", params={"event_code": "temp_high"})
    by_severity = client.get("/v1/events", params={"severity": "CRITICAL"})

    assert len(by_code.json()) == 1
    assert by_code.json()[0]["event_code"] == "TEMP_HIGH"
    assert len(by_severity.json()) == 1
    assert by_severity.json()[0]["severity"] == "CRITICAL"


def test_duplicate_events_are_ignored(client):
    task_id = client.post("/v1/tasks", json=TASK_PAYLOAD).json()["id"]
    assert seed_events(task_id) == 2
    assert seed_events(task_id) == 0

    response = client.get("/v1/events")

    assert len(response.json()) == 2
