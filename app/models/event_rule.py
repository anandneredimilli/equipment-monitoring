from sqlalchemy import Boolean, Index, String, Text, false, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class EventRule(Base, TimestampMixin):
    __tablename__ = "event_rules"

    __table_args__ = (
        Index(
            "uq_event_rules_event_code_active",
            "event_code",
            unique=True,
            postgresql_where=text("is_deleted = false"),
            sqlite_where=text("is_deleted = 0"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_code: Mapped[str] = mapped_column(String(100), nullable=False)
    event_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default="INFO", nullable=False)
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
        nullable=False,
    )
