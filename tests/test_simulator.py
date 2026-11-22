import csv

from app.core.simulator_files import ensure_dirs, snapshots_dir, source_path


def write_source(machine_id: str, rows: list[tuple[int, str, str]]) -> None:
    ensure_dirs()
    with source_path(machine_id).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["cursor", "timestamp", "event_code"])
        writer.writerows(rows)


def source_rows(count: int) -> list[tuple[int, str, str]]:
    return [
        (cursor, f"2026-11-21T08:00:{cursor:02d}Z", "TEMP_HIGH" if cursor % 2 else "DOOR_OPEN")
        for cursor in range(1, count + 1)
    ]


def test_download_returns_snapshot_metadata_and_rows(client):
    write_source("ETCH-001", source_rows(10))

    response = client.post(
        "/v1/simulator/download",
        json={"machine_id": "ETCH-001", "last_processed_cursor": 5},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["start_cursor"] == 6
    assert data["end_cursor"] == 10
    assert data["file_name"].startswith("ETCH-001_6_10_")
    assert data["download_url"].endswith(data["file_name"])
    assert (snapshots_dir() / data["file_name"]).is_file()

    snapshot = client.get(f"/v1/simulator/files/{data['file_name']}")
    assert snapshot.status_code == 200
    lines = snapshot.text.strip().splitlines()
    assert lines[0] == "cursor,timestamp,event_code"
    assert [line.split(",")[0] for line in lines[1:]] == ["6", "7", "8", "9", "10"]


def test_empty_range_returns_header_only_snapshot(client):
    write_source("CNC-001", source_rows(10))

    data = client.post(
        "/v1/simulator/download",
        json={"machine_id": "CNC-001", "last_processed_cursor": 10},
    ).json()

    assert data["start_cursor"] == 11
    assert data["end_cursor"] == 10

    snapshot = client.get(f"/v1/simulator/files/{data['file_name']}")
    assert snapshot.text.strip() == "cursor,timestamp,event_code"


def test_unknown_machine_rejected(client):
    response = client.post(
        "/v1/simulator/download",
        json={"machine_id": "XYZ-001", "last_processed_cursor": 0},
    )

    assert response.status_code == 422
    assert "Unknown machine_id" in response.json()["detail"]


def test_unknown_file_returns_404(client):
    response = client.get("/v1/simulator/files/not-a-snapshot.csv")

    assert response.status_code == 404
