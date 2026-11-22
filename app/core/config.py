from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    db_password: str
    db_user: str = "app_user"
    db_host: str = "db"
    db_port: int = 5432
    db_name: str = "equipment_monitoring"

    redis_url: str
    api_base_url: str = "http://api:8000"
    dispatch_interval_seconds: int = 10

    simulator_machines: str = "ETCH-001,ETCH-002,CNC-001"
    generated_files_dir: str = "generated_files"
    generator_interval_seconds: int = 5
    generator_rows_per_tick: int = 5
    simulator_lock_ttl_seconds: int = 10

    @property
    def database_url(self) -> str:
        password = quote_plus(self.db_password)
        return (
            f"postgresql+psycopg://{self.db_user}:{password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
