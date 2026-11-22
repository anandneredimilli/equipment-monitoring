from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models import EventRule
from app.schemas.event_code import EventCodeCreate


class EventCodeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_code(self, code: str) -> EventRule | None:
        return (
            self.db.query(EventRule)
            .filter(
                EventRule.event_code == code,
                EventRule.is_deleted.is_(False),
            )
            .first()
        )

    def create(self, payload: EventCodeCreate) -> EventRule:
        rule = EventRule(
            event_code=payload.event_code,
            event_description=payload.event_description,
            severity=payload.severity,
        )
        self.db.add(rule)
        try:
            self.db.commit()
            self.db.refresh(rule)
        except IntegrityError as exc:
            self.db.rollback()
            raise AppError(
                status_code=409,
                detail=f"Event code '{payload.event_code}' already exists",
            ) from exc
        return rule

    def list_all(self) -> list[EventRule]:
        return self.db.query(EventRule).filter(EventRule.is_deleted.is_(False)).order_by(EventRule.id).all()

    def delete(self, event_code: str) -> EventRule | None:
        event_rule = (
            self.db.query(EventRule)
            .filter(
                EventRule.event_code == event_code,
                EventRule.is_deleted.is_(False),
            )
            .first()
        )

        if not event_rule:
            return None

        event_rule.is_deleted = True
        self.db.commit()
        return event_rule
