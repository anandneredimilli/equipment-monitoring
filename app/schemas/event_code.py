from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Severity = Literal["INFO", "WARNING", "CRITICAL"]


class EventCodeCreate(BaseModel):
    event_code: str = Field(..., min_length=1, max_length=100)
    event_description: str | None = Field(default=None, max_length=2000)
    severity: Severity = "INFO"

    @field_validator("event_code")
    @classmethod
    def normalize_event_code(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("event_code must not be blank")
        return value.upper()


class EventCodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_code: str
    event_description: str | None = None
    severity: Severity
    created_at: datetime
    updated_at: datetime
