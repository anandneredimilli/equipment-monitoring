from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models import EventRule
from app.repositories.event_code_repository import EventCodeRepository
from app.schemas.event_code import EventCodeCreate

class EventCodeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = EventCodeRepository(db)

    def create(self, payload: EventCodeCreate) -> EventRule:
        if self.repository.get_by_code(payload.event_code):
            raise AppError(
                status_code=409,
                detail=f"Event code '{payload.event_code}' already exists",
            )
        return self.repository.create(payload)

    def list_all(self) -> list[EventRule]:
        return self.repository.list_all()

    def delete(self, event_code: str) -> dict[str, str]:
        event_rule = self.repository.delete(event_code)
        if not event_rule:
            raise AppError(
                status_code=404,
                detail=f"Event rule with code '{event_code}' not found"
            )

        return {"message": "Event rule deleted successfully"}
        