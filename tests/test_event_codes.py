from app.repositories.event_code_repository import EventCodeRepository
from tests.conftest import TestingSessionLocal


def test_create_event_code(client):
    response = client.post(
        "/v1/event-codes",
        json={"event_code": " temp_high ", "event_description": "Temperature high"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["event_code"] == "TEMP_HIGH"
    assert data["event_description"] == "Temperature high"
    assert data["severity"] == "INFO"


def test_create_event_code_with_severity(client):
    response = client.post(
        "/v1/event-codes",
        json={"event_code": "PRESSURE_HIGH", "severity": "CRITICAL"},
    )

    assert response.status_code == 201
    assert response.json()["severity"] == "CRITICAL"


def test_create_event_code_without_description(client):
    response = client.post(
        "/v1/event-codes",
        json={"event_code": "PRESSURE_LOW"},
    )

    assert response.status_code == 201
    assert response.json()["event_description"] is None


def test_duplicate_event_code_returns_409(client):
    client.post("/v1/event-codes", json={"event_code": "TEMP_HIGH"})

    response = client.post("/v1/event-codes", json={"event_code": "TEMP_HIGH"})

    assert response.status_code == 409
    assert response.json()["detail"] == "Event code 'TEMP_HIGH' already exists"


def test_blank_event_code_rejected(client):
    response = client.post("/v1/event-codes", json={"event_code": "   "})

    assert response.status_code == 422


def test_list_event_codes(client):
    client.post("/v1/event-codes", json={"event_code": "TEMP_HIGH"})
    client.post("/v1/event-codes", json={"event_code": "VIBRATION_HIGH"})

    response = client.get("/v1/event-codes")

    assert response.status_code == 200
    assert [item["event_code"] for item in response.json()] == [
        "TEMP_HIGH",
        "VIBRATION_HIGH",
    ]


def test_delete_event_code(client):
    client.post("/v1/event-codes", json={"event_code": "TEMP_HIGH"})

    response = client.delete("/v1/event-codes/TEMP_HIGH")

    assert response.status_code == 200
    assert response.json() == {"message": "Event rule deleted successfully"}


def test_deleted_event_code_is_not_listed(client):
    client.post("/v1/event-codes", json={"event_code": "TEMP_HIGH"})
    client.post("/v1/event-codes", json={"event_code": "VIBRATION_HIGH"})

    delete_response = client.delete("/v1/event-codes/TEMP_HIGH")
    list_response = client.get("/v1/event-codes")

    assert delete_response.status_code == 200
    assert [item["event_code"] for item in list_response.json()] == [
        "VIBRATION_HIGH"
    ]


def test_delete_unknown_event_code_returns_404(client):
    response = client.delete("/v1/event-codes/UNKNOWN")

    assert response.status_code == 404
    assert response.json()["detail"] == "Event rule with code 'UNKNOWN' not found"


def test_delete_already_deleted_event_code_returns_404(client):
    client.post("/v1/event-codes", json={"event_code": "TEMP_HIGH"})
    client.delete("/v1/event-codes/TEMP_HIGH")

    response = client.delete("/v1/event-codes/TEMP_HIGH")

    assert response.status_code == 404
    assert response.json()["detail"] == "Event rule with code 'TEMP_HIGH' not found"


def test_deleted_rule_is_not_returned_by_repository(client):
    client.post("/v1/event-codes", json={"event_code": "TEMP_HIGH"})
    client.delete("/v1/event-codes/TEMP_HIGH")

    db = TestingSessionLocal()
    try:
        repository = EventCodeRepository(db)

        assert repository.get_by_code("TEMP_HIGH") is None
        assert repository.list_all() == []
    finally:
        db.close()


def test_recreate_deleted_event_code_returns_201(client):
    client.post("/v1/event-codes", json={"event_code": "TEMP_HIGH"})
    client.delete("/v1/event-codes/TEMP_HIGH")

    response = client.post("/v1/event-codes", json={"event_code": "TEMP_HIGH"})

    assert response.status_code == 201
    assert response.json()["event_code"] == "TEMP_HIGH"

    list_response = client.get("/v1/event-codes")
    assert [item["event_code"] for item in list_response.json()] == ["TEMP_HIGH"]


def test_duplicate_active_event_code_still_returns_409(client):
    client.post("/v1/event-codes", json={"event_code": "TEMP_HIGH"})

    response = client.post("/v1/event-codes", json={"event_code": "TEMP_HIGH"})

    assert response.status_code == 409
    assert response.json()["detail"] == "Event code 'TEMP_HIGH' already exists"
