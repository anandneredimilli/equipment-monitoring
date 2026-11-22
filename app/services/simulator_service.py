import csv
import os
import re
from datetime import datetime, timezone

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.machines import validate_machine_id
from app.core.simulator_files import (
    ensure_dirs,
    machine_lock,
    snapshot_path,
    snapshots_dir,
    source_path,
)
from app.schemas.simulator import DownloadMetadata, DownloadRequest

_SNAPSHOT_PATTERN = re.compile(
    r"^(?P<machine>.+)_(?P<start>\d+)_(?P<end>\d+)_"
    r"\d{8}_\d{6}(?:_\d+)?\.csv$"
)


class SimulatorService:
    """Reads generator source files and publishes immutable snapshots."""

    def download(self, payload: DownloadRequest) -> DownloadMetadata:
        machine_id = validate_machine_id(payload.machine_id)
        last_cursor = payload.last_processed_cursor
        start_cursor = last_cursor + 1

        ensure_dirs()
        with machine_lock(machine_id):
            rows = self._read_rows(source_path(machine_id))
            selected = [row for row in rows if row[0] > last_cursor]
            end_cursor = selected[-1][0] if selected else last_cursor
            file_name = self._write_snapshot(machine_id, start_cursor, end_cursor, selected)

        return DownloadMetadata(
            file_name=file_name,
            start_cursor=start_cursor,
            end_cursor=end_cursor,
            download_url=(
                f"{settings.api_base_url.rstrip('/')}/v1/simulator/files/{file_name}"
            ),
        )

    @staticmethod
    def _read_rows(path) -> list[tuple[int, str, str]]:
        if not path.exists():
            return []

        rows: list[tuple[int, str, str]] = []
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                try:
                    cursor = int(row["cursor"])
                except (KeyError, TypeError, ValueError):
                    continue
                rows.append(
                    (
                        cursor,
                        row.get("timestamp") or "",
                        row.get("event_code") or "",
                    )
                )

        return sorted(rows, key=lambda item: item[0])

    @staticmethod
    def _write_snapshot(
        machine_id: str,
        start_cursor: int,
        end_cursor: int,
        rows: list[tuple[int, str, str]],
    ) -> str:
        ensure_dirs()
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        base = f"{machine_id}_{start_cursor}_{end_cursor}_{stamp}"
        candidate = snapshots_dir() / f"{base}.csv"
        suffix = 1
        while candidate.exists():
            candidate = snapshots_dir() / f"{base}_{suffix}.csv"
            suffix += 1

        temp_path = candidate.with_name(candidate.name + ".tmp")
        with temp_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["cursor", "timestamp", "event_code"])
            writer.writerows(rows)

        os.replace(temp_path, candidate)
        return candidate.name

    @staticmethod
    def read_snapshot(file_name: str) -> str:
        if "\\" in file_name or "/" in file_name or not _SNAPSHOT_PATTERN.match(file_name):
            raise AppError(status_code=404, detail=f"Snapshot {file_name} not found")

        path = snapshot_path(file_name)
        if not path.is_file():
            raise AppError(status_code=404, detail=f"Snapshot {file_name} not found")

        if not path.resolve().is_relative_to(snapshots_dir().resolve()):
            raise AppError(status_code=404, detail=f"Snapshot {file_name} not found")

        return path.read_text(encoding="utf-8")
