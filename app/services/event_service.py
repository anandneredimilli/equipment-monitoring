from datetime import datetime

from sqlalchemy.orm import Session

from app.models import MonitoredEvent
from app.repositories.event_repository import EventRepository
from app.schemas.event_code import Severity


class EventService:
    def __init__(self, db: Session) -> None:
        self.repository = EventRepository(db)

    def list_events(
        self,
        *,
        machine_id: str | None = None,
        event_code: str | None = None,
        severity: Severity | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[MonitoredEvent]:
        return self.repository.list_events(
            machine_id=machine_id,
            event_code=event_code,
            severity=severity,
            from_time=from_time,
            to_time=to_time,
            skip=skip,
            limit=limit,
        )
