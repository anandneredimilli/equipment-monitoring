from datetime import datetime
from sqlalchemy import create_engine, DateTime, func
from sqlalchemy.orm import DeclarativeBase, sessionmaker,  mapped_column, Mapped

from app.core.config import settings

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

engine = create_engine(
    settings.database_url,
    pool_pre_ping = True
)

SessionLocal = sessionmaker(
    bind = engine,
    autoflush = False,
    autocommit = False,
    expire_on_commit = False
)

def get_db():
    db = SessionLocal()
    try: 
        yield db
    finally:
        db.close()