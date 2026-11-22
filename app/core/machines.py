from app.core.config import settings
from app.core.exceptions import AppError


def allowed_machines() -> list[str]:
    return [item.strip() for item in settings.simulator_machines.split(",") if item.strip()]


def validate_machine_id(machine_id: str) -> str:
    value = machine_id.strip()
    machines = allowed_machines()
    if value not in machines:
        raise AppError(
            status_code=422,
            detail=f"Unknown machine_id '{value}'. Allowed machines: {', '.join(machines)}",
        )
    return value
