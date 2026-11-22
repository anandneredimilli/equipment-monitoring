from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.task import TaskCreate, TaskRead
from app.services.task_service import TaskService

router = APIRouter(prefix="/v1/tasks", tags=["Tasks"])


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    return TaskService(db).create(payload)


@router.get("", response_model=list[TaskRead])
def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return TaskService(db).list_all(skip=skip, limit=limit)


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: int, db: Session = Depends(get_db)):
    return TaskService(db).get(task_id)


@router.patch("/{task_id}/pause", response_model=TaskRead)
def pause_task(task_id: int, db: Session = Depends(get_db)):
    return TaskService(db).pause(task_id)


@router.patch("/{task_id}/resume", response_model=TaskRead)
def resume_task(task_id: int, db: Session = Depends(get_db)):
    return TaskService(db).resume(task_id)


@router.delete("/{task_id}", response_model=TaskRead)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    return TaskService(db).delete(task_id)
