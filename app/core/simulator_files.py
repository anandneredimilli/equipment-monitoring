from pathlib import Path

import redis

from app.core.config import settings


def base_dir() -> Path:
    return Path(settings.generated_files_dir)


def sources_dir() -> Path:
    return base_dir() / "sources"


def snapshots_dir() -> Path:
    return base_dir() / "snapshots"


def ensure_dirs() -> None:
    sources_dir().mkdir(parents=True, exist_ok=True)
    snapshots_dir().mkdir(parents=True, exist_ok=True)


def source_path(machine_id: str) -> Path:
    return sources_dir() / f"{machine_id}.csv"


def snapshot_path(file_name: str) -> Path:
    return snapshots_dir() / file_name


def machine_lock(machine_id: str):
    """Redis-backed lock shared by the generator and the simulator API."""
    client = redis.Redis.from_url(settings.redis_url)
    return client.lock(
        f"simulator:source:{machine_id}",
        timeout=settings.simulator_lock_ttl_seconds,
        blocking_timeout=settings.simulator_lock_ttl_seconds,
    )
