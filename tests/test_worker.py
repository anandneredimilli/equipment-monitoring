from app.workers.tasks import _parse_csv


def test_parse_simulator_csv():
    content = (
        "cursor,timestamp,event_code\n"
        "1,2026-11-19T10:00:00Z,TEMP_HIGH\n"
        "2,2026-11-19T10:01:00Z,DOOR_OPEN\n"
    )

    rows = _parse_csv(content)

    assert len(rows) == 2
    assert rows[0]["cursor"] == 1
    assert rows[0]["event_code"] == "TEMP_HIGH"
    assert rows[0]["event_timestamp"].tzinfo is not None
