from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import MonitoredEvent
from app.schemas.event_code import Severity


class EventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def bulk_create(self, rows: list[dict]) -> int:
        """Insert events. Existing (machine_id, cursor) pairs are ignored."""
        if not rows:
            return 0

        if self.db.bind.dialect.name == "postgresql":
            statement = (
                pg_insert(MonitoredEvent)
                .values(rows)
                .on_conflict_do_nothing(index_elements=["machine_id", "cursor"])
                .returning(MonitoredEvent.id)
            )
            inserted_ids = self.db.execute(statement).scalars().all()
            self.db.commit()
            return len(inserted_ids)

        inserted = 0
        for row in rows:
            exists = (
                self.db.query(MonitoredEvent)
                .filter(
                    MonitoredEvent.machine_id == row["machine_id"],
                    MonitoredEvent.cursor == row["cursor"],
                )
                .first()
            )
            if exists is None:
                self.db.add(MonitoredEvent(**row))
                inserted += 1
        self.db.commit()
        return inserted

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
        statement = select(MonitoredEvent)

        if machine_id:
            statement = statement.where(MonitoredEvent.machine_id == machine_id)
        if event_code:
            statement = statement.where(MonitoredEvent.event_code == event_code.upper())
        if severity:
            statement = statement.where(MonitoredEvent.severity == severity)
        if from_time:
            statement = statement.where(MonitoredEvent.event_timestamp >= from_time)
        if to_time:
            statement = statement.where(MonitoredEvent.event_timestamp <= to_time)

        statement = (
            statement.order_by(MonitoredEvent.event_timestamp.desc(), MonitoredEvent.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(statement).scalars().all())
