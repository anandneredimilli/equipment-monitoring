from datetime import datetime
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import DateTime, String, ForeignKey, Integer, Text, func

from app.core.database import Base, TimestampMixin

class TaskExecution(Base, TimestampMixin):
    __tablename__ = "task_executions"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("monitoring_tasks.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_cursor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_cursor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    records_downloaded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matched_events: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    task: Mapped["MonitoringTask"] = relationship(back_populates="executions")