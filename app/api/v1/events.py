from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.event import EventRead
from app.schemas.event_code import Severity
from app.services.event_service import EventService

router = APIRouter(prefix="/v1/events", tags=["Events"])


@router.get("", response_model=list[EventRead])
def list_events(
    machine_id: str | None = None,
    event_code: str | None = None,
    severity: Severity | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return EventService(db).list_events(
        machine_id=machine_id,
        event_code=event_code,
        severity=severity,
        from_time=from_time,
        to_time=to_time,
        skip=skip,
        limit=limit,
    )
