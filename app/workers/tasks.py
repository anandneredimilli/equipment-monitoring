import csv
import io
from datetime import datetime, timedelta, timezone

import httpx2 as httpx

from app.core.celery import celery_app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models import TaskExecution
from app.repositories.event_code_repository import EventCodeRepository
from app.repositories.event_repository import EventRepository
from app.repositories.task_repository import TaskRepository


def _parse_csv(content: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(content))
    rows: list[dict] = []
    for row in reader:
        rows.append(
            {
                "cursor": int(row["cursor"]),
                "event_timestamp": datetime.fromisoformat(
                    row["timestamp"].replace("Z", "+00:00")
                ),
                "event_code": row["event_code"],
            }
        )
    return rows


@celery_app.task(name="app.workers.tasks.dispatch_due_tasks")
def dispatch_due_tasks():
    """Enqueue every active task whose next_attempt is due."""
    db = SessionLocal()
    try:
        due = TaskRepository(db).list_due(datetime.now(timezone.utc))
        task_ids = [task.id for task in due]
    finally:
        db.close()

    for task_id in task_ids:
        process_task.delay(task_id)

    return {"dispatched": task_ids}


@celery_app.task(
    name="app.workers.tasks.process_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def process_task(self, task_id: int):
    """Download one simulated file, filter it, and store matching events."""
    db = SessionLocal()
    execution: TaskExecution | None = None

    try:
        task = TaskRepository(db).get_by_id(task_id)
        if task is None or task.status != "active":
            return {"skipped": True, "task_id": task_id}

        execution = TaskExecution(task_id=task_id, status="RUNNING")
        db.add(execution)
        db.commit()
        db.refresh(execution)

        base_url = settings.api_base_url.rstrip("/")
        with httpx.Client(timeout=30.0) as client:
            download_response = client.post(
                f"{base_url}/v1/simulator/download",
                json={
                    "machine_id": task.machine_id,
                    "last_processed_cursor": task.last_processed_cursor,
                },
            )
            download_response.raise_for_status()
            metadata = download_response.json()

            file_response = client.get(metadata["download_url"])
            file_response.raise_for_status()
            csv_text = file_response.text

        csv_rows = _parse_csv(csv_text)
        severity_by_code = {
            rule.event_code: rule.severity
            for rule in EventCodeRepository(db).list_all()
        }

        event_rows = []
        for row in csv_rows:
            severity = severity_by_code.get(row["event_code"])
            if severity is None:
                continue
            event_rows.append(
                {
                    "task_id": task.id,
                    "machine_id": task.machine_id,
                    "cursor": row["cursor"],
                    "event_code": row["event_code"],
                    "severity": severity,
                    "event_timestamp": row["event_timestamp"],
                }
            )

        inserted = EventRepository(db).bulk_create(event_rows)

        now = datetime.now(timezone.utc)
        next_attempt = now + timedelta(seconds=task.interval_seconds)
        stop_at = (
            task.stop_at
            if task.stop_at.tzinfo
            else task.stop_at.replace(tzinfo=timezone.utc)
        )
        if next_attempt > stop_at:
            next_attempt = None

        task.last_processed_cursor = metadata["end_cursor"]
        task.last_attempt = now
        task.next_attempt = next_attempt

        execution.status = "SUCCESS"
        execution.finished_at = now
        execution.file_name = metadata["file_name"]
        execution.start_cursor = metadata["start_cursor"]
        execution.end_cursor = metadata["end_cursor"]
        execution.records_downloaded = len(csv_rows)
        execution.matched_events = inserted
        db.commit()

        return {
            "task_id": task_id,
            "file_name": metadata["file_name"],
            "records_downloaded": len(csv_rows),
            "matched_events": inserted,
        }

    except Exception as exc:
        db.rollback()
        if execution is not None:
            try:
                db.refresh(execution)
                execution.status = "FAILED"
                execution.finished_at = datetime.now(timezone.utc)
                execution.error_message = str(exc)
                db.commit()
            except Exception:
                db.rollback()
        raise self.retry(exc=exc)
    finally:
        db.close()
