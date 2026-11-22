from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.event_code import Severity


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    machine_id: str
    cursor: int
    event_code: str
    severity: Severity
    event_timestamp: datetime
    created_at: datetime
    updated_at: datetime
