from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TaskCreate(BaseModel):
    machine_id: str = Field(..., min_length=1, max_length=100)
    start_at: datetime
    stop_at: datetime
    interval_seconds: int = Field(..., gt=0)

    @model_validator(mode="after")
    def validate_window(self) -> "TaskCreate":
        if self.stop_at <= self.start_at:
            raise ValueError("stop_at must be after start_at")
        return self


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    machine_id: str
    status: str
    start_at: datetime
    stop_at: datetime
    interval_seconds: int
    last_processed_cursor: int
    last_attempt: datetime | None
    next_attempt: datetime | None
    created_at: datetime
    updated_at: datetime
