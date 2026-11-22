from datetime import datetime

from sqlalchemy.orm import Session

from app.models import MonitoringTask
from app.schemas.task import TaskCreate


class TaskRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: TaskCreate) -> MonitoringTask:
        task = MonitoringTask(
            machine_id=payload.machine_id,
            status="active",
            start_at=payload.start_at,
            stop_at=payload.stop_at,
            interval_seconds=payload.interval_seconds,
            last_processed_cursor=0,
            next_attempt=payload.start_at,
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_by_id(self, task_id: int) -> MonitoringTask | None:
        return self.db.query(MonitoringTask).filter(MonitoringTask.id == task_id).first()

    def list_all(self, skip: int = 0, limit: int = 100) -> list[MonitoringTask]:
        return (
            self.db.query(MonitoringTask)
            .filter(MonitoringTask.status != 'deleted')
            .order_by(MonitoringTask.id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def list_due(self, now: datetime) -> list[MonitoringTask]:
        return (
            self.db.query(MonitoringTask)
            .filter(
                MonitoringTask.status == "active",
                MonitoringTask.next_attempt.is_not(None),
                MonitoringTask.next_attempt <= now,
                MonitoringTask.stop_at >= now,
            )
            .order_by(MonitoringTask.next_attempt)
            .all()
        )

    def save(self, task: MonitoringTask) -> MonitoringTask:
        self.db.commit()
        self.db.refresh(task)
        return task
