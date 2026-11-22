from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.machines import validate_machine_id
from app.models import MonitoringTask
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class TaskService:
    def __init__(self, db: Session) -> None:
        self.repository = TaskRepository(db)

    def create(self, payload: TaskCreate) -> MonitoringTask:
        validate_machine_id(payload.machine_id)
        return self.repository.create(payload)

    def list_all(self, skip: int = 0, limit: int = 100) -> list[MonitoringTask]:
        return self.repository.list_all(skip=skip, limit=limit)

    def get(self, task_id: int) -> MonitoringTask:
        task = self.repository.get_by_id(task_id)
        if task is None:
            raise AppError(status_code=404, detail=f"Task {task_id} not found")
        return task

    def pause(self, task_id: int) -> MonitoringTask:
        task = self.get(task_id)
        task.status = "paused"
        task.next_attempt = None
        return self.repository.save(task)

    def resume(self, task_id: int) -> MonitoringTask:
        task = self.get(task_id)
        now = datetime.now(timezone.utc)
        start_at = _as_utc(task.start_at)
        stop_at = _as_utc(task.stop_at)

        next_attempt = max(now, start_at)
        if next_attempt > stop_at:
            next_attempt = None

        task.status = "active"
        task.next_attempt = next_attempt
        return self.repository.save(task)

    def delete(self, task_id: int) -> MonitoringTask:
        task = self.get(task_id)
        task.status = "deleted"
        task.next_attempt = None
        return self.repository.save(task)
