import csv
import random
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.machines import allowed_machines
from app.core.simulator_files import ensure_dirs, machine_lock, source_path
from app.repositories.event_code_repository import EventCodeRepository

_DEFAULT_CODES = ["TEMP_HIGH", "PRESSURE_LOW", "VIBRATION_HIGH"]
_NOISE_CODES = ["DOOR_OPEN", "HUMIDITY_HIGH", "BATTERY_LOW", "UNKNOWN"]


def _last_cursor(path) -> int:
    if not path.exists():
        return 0

    last = 0
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            try:
                last = max(last, int(row["cursor"]))
            except (KeyError, TypeError, ValueError):
                continue
    return last


def _ensure_header(path) -> None:
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(["cursor", "timestamp", "event_code"])


def append_events(machine_id: str, db: Session) -> int:
    """Append one tick of events to a machine's source CSV."""
    ensure_dirs()
    path = source_path(machine_id)

    with machine_lock(machine_id):
        _ensure_header(path)
        last_cursor = _last_cursor(path)

        registered = [rule.event_code for rule in EventCodeRepository(db).list_all()]
        pool = registered + _NOISE_CODES if registered else _DEFAULT_CODES + _NOISE_CODES

        now = datetime.now(timezone.utc)
        with path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            for offset in range(1, settings.generator_rows_per_tick + 1):
                timestamp = (now + timedelta(seconds=offset)).isoformat()
                timestamp = timestamp.replace("+00:00", "Z")
                writer.writerow([last_cursor + offset, timestamp, random.choice(pool)])

        return settings.generator_rows_per_tick


def run() -> None:
    ensure_dirs()
    print(
        f"Generator started: {', '.join(allowed_machines())} "
        f"| {settings.generator_rows_per_tick} rows every "
        f"{settings.generator_interval_seconds}s",
        flush=True,
    )

    while True:
        db = SessionLocal()
        try:
            for machine_id in allowed_machines():
                try:
                    append_events(machine_id, db)
                except Exception as exc:
                    print(f"Generator error for {machine_id}: {exc}", flush=True)
        finally:
            db.close()

        time.sleep(settings.generator_interval_seconds)


if __name__ == "__main__":
    run()
