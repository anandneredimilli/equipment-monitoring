from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.workers.tasks as worker_tasks
from app.core.celery import celery_app
from app.core.config import settings
from app.core.database import Base
from app.models import MonitoringTask


def test_beat_schedule_uses_single_dispatcher():
    entry = celery_app.conf.beat_schedule["dispatch-due-tasks"]

    assert entry["task"] == "app.workers.tasks.dispatch_due_tasks"
    assert entry["schedule"] == float(settings.dispatch_interval_seconds)


def test_dispatch_due_tasks_enqueues_only_due_tasks(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    db = Session()

    now = datetime.now(timezone.utc)
    due = MonitoringTask(
        machine_id="ETCH-001",
        status="active",
        start_at=now - timedelta(hours=1),
        stop_at=now + timedelta(hours=1),
        interval_seconds=300,
        next_attempt=now - timedelta(minutes=1),
    )
    future = MonitoringTask(
        machine_id="CNC-001",
        status="active",
        start_at=now + timedelta(hours=1),
        stop_at=now + timedelta(hours=2),
        interval_seconds=300,
        next_attempt=now + timedelta(hours=1),
    )
    db.add_all([due, future])
    db.commit()

    dispatched = []
    monkeypatch.setattr(worker_tasks, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        worker_tasks.process_task,
        "delay",
        lambda task_id: dispatched.append(task_id),
    )

    worker_tasks.dispatch_due_tasks()

    assert dispatched == [due.id]
