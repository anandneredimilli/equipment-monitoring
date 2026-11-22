from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import DateTime, String, Integer
from datetime import datetime
from app.core.database import Base, TimestampMixin

class MonitoringTask(Base, TimestampMixin):
    __tablename__ = "monitoring_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    machine_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default='active', nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stop_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    last_processed_cursor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_attempt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_attempt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executions: Mapped[list["TaskExecution"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
