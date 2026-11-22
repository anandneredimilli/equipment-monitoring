TASK_PAYLOAD = {
    "machine_id": "ETCH-001",
    "start_at": "2026-11-23T08:00:00Z",
    "stop_at": "2026-11-24T08:00:00Z",
    "interval_seconds": 300,
}


def create_task(client):
    return client.post("/v1/tasks", json=TASK_PAYLOAD)


def test_create_task(client):
    response = create_task(client)

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["machine_id"] == "ETCH-001"
    assert data["status"] == "active"
    assert data["last_processed_cursor"] == 0
    assert data["next_attempt"].startswith("2026-11-23T08:00:00")


def test_invalid_window_rejected(client):
    payload = dict(TASK_PAYLOAD)
    payload["stop_at"] = payload["start_at"]

    response = client.post("/v1/tasks", json=payload)

    assert response.status_code == 422


def test_pause_resume_delete(client):
    task_id = create_task(client).json()["id"]

    paused = client.patch(f"/v1/tasks/{task_id}/pause")
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"
    assert paused.json()["next_attempt"] is None

    resumed = client.patch(f"/v1/tasks/{task_id}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "active"
    assert resumed.json()["next_attempt"] is not None

    deleted = client.delete(f"/v1/tasks/{task_id}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"
    assert deleted.json()["next_attempt"] is None


def test_get_missing_task_returns_404(client):
    response = client.get("/v1/tasks/999")

    assert response.status_code == 404
