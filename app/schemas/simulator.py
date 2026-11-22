from pydantic import BaseModel, Field, field_validator


class DownloadRequest(BaseModel):
    machine_id: str = Field(..., min_length=1, max_length=100)
    last_processed_cursor: int = Field(..., ge=0)

    @field_validator("machine_id")
    @classmethod
    def normalize_machine_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("machine_id must not be blank")
        return value


class DownloadMetadata(BaseModel):
    file_name: str
    start_cursor: int
    end_cursor: int
    download_url: str
