# Scheduled Equipment Event Monitoring API

A containerized FastAPI service that:

1. accepts event-code watchlist registrations,
2. creates scheduled monitoring tasks for machines,
3. simulates downloadable event CSV files,
4. processes due tasks with Celery,
5. stores only matching events idempotently,
6. exposes those events through a filtered read API.

The project follows a simple **layered architecture**:

```text
routes → services → repositories → SQLAlchemy models
```

No Clean/Hexagonal layering is used; the goal is readable, evaluator-friendly code.

---

## 1. Stack

| Concern | Technology |
|---|---|
| API | FastAPI |
| ORM | SQLAlchemy 2.0 |
| Database | PostgreSQL 16 |
| Migrations | Alembic |
| Cache / broker | Redis 7 |
| Background jobs | Celery Worker + Celery Beat |
| Validation | Pydantic v2 / pydantic-settings |
| Tests | pytest + TestClient (`httpx2`) |
| Containers | Docker + Docker Compose |

---

## 2. Quick start

### 2.1 Copy the environment file

```powershell
copy .env.example .env
```

Then edit `.env`. Only `DB_PASSWORD` needs to be changed for a normal local run.

```dotenv
DB_PASSWORD=change_me
DB_USER=app_user
DB_HOST=db
DB_PORT=5432
DB_NAME=equipment_monitoring
REDIS_URL=redis://redis:6379/0
API_BASE_URL=http://api:8000
DISPATCH_INTERVAL_SECONDS=10
SIMULATOR_MACHINES=ETCH-001,ETCH-002,CNC-001
GENERATED_FILES_DIR=generated_files
GENERATOR_INTERVAL_SECONDS=5
GENERATOR_ROWS_PER_TICK=5
SIMULATOR_LOCK_TTL_SECONDS=10
```

The application builds `DATABASE_URL` from `DB_PASSWORD`, `DB_USER`, `DB_HOST`, `DB_PORT` and `DB_NAME`. There is no second password to keep in sync.

`API_BASE_URL` must be reachable from the Celery worker. Inside Compose, `http://api:8000` is correct.

### 2.2 Start everything

```powershell
docker compose up --build -d
docker compose ps
```

Compose starts:

| Service | Purpose |
|---|---|
| `db` | PostgreSQL |
| `redis` | Celery broker/result backend |
| `migrate` | Runs `alembic upgrade head` once, then exits |
| `api` | FastAPI on port `8000` |
| `worker` | Celery worker that processes tasks |
| `beat` | Celery Beat that enqueues due tasks periodically |
| `generator` | Long-running process that appends events to source CSVs |

Migrations run automatically before the API, worker and generator start.

### 2.3 Verify

```powershell
curl http://localhost:8000/health
```

Expected:

```json
{"status":"healthy"}
```

---

## 3. API endpoints

### Simulator

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/simulator/download` | Returns metadata for a generated CSV file |
| `GET` | `/v1/simulator/files/{file_name}` | Downloads the generated CSV |

Request:

```json
{
  "machine_id": "ETCH-001",
  "last_processed_cursor": 100
}
```

Response:

```json
{
  "file_name": "ETCH-001__101__125.csv",
  "start_cursor": 101,
  "end_cursor": 125,
  "download_url": "http://api:8000/v1/simulator/files/ETCH-001__101__125.csv"
}
```

CSV format:

```csv
cursor,timestamp,event_code
101,2026-01-01T01:41:00Z,TEMP_HIGH
102,2026-01-01T01:42:00Z,DOOR_OPEN
```

Files are generated **deterministically** from the file name. No shared in-memory state is needed between the API and the Celery worker.

### Event codes

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/event-codes` | Registers a code; duplicate active code returns `409` |
| `GET` | `/v1/event-codes` | Lists active registered codes |
| `DELETE` | `/v1/event-codes/{event_code}` | Soft-deletes a code; deleted codes can be registered again |

Request:

```json
{
  "event_code": " temp_high ",
  "event_description": "Temperature above limit",
  "severity": "WARNING"
}
```

`severity` is optional and defaults to `INFO`. Allowed values: `INFO`, `WARNING`, `CRITICAL`.

Codes are stripped and uppercased, so `" temp_high "` becomes `"TEMP_HIGH"`.

### Tasks

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/tasks` | Creates an active monitoring task |
| `GET` | `/v1/tasks` | Lists tasks (`skip`, `limit`) |
| `GET` | `/v1/tasks/{id}` | Gets one task |
| `PATCH` | `/v1/tasks/{id}/pause` | Pauses a task |
| `PATCH` | `/v1/tasks/{id}/resume` | Resumes a task |
| `DELETE` | `/v1/tasks/{id}` | Soft-deletes a task (`status="deleted"`) |

Create request:

```json
{
  "machine_id": "ETCH-001",
  "start_at": "2026-11-23T08:00:00Z",
  "stop_at": "2026-11-24T08:00:00Z",
  "interval_seconds": 300
}
```

`stop_at` must be after `start_at`; `interval_seconds` must be positive.

### Events

| Method | Path | Description |
|---|---|---|
| `GET` | `/v1/events` | Lists stored matching events |

Supported query parameters:

```text
machine_id
event_code
severity
from_time
to_time
skip
limit
```

Example:

```powershell
curl "http://localhost:8000/v1/events?machine_id=ETCH-001&severity=CRITICAL"
```

---

## 4. How processing works

1. `POST /v1/tasks` creates a task with `next_attempt = start_at`.
2. Celery Beat runs `dispatch_due_tasks` every `DISPATCH_INTERVAL_SECONDS`.
3. The dispatcher finds tasks where:
   - `status = active`,
   - `next_attempt <= now`,
   - `stop_at >= now`.
4. Each due task is enqueued as `process_task(task_id)`.
5. The worker:
   - creates a `task_executions` row with status `RUNNING`,
   - calls the simulator download endpoint,
   - fetches the CSV,
   - keeps rows whose `event_code` is registered in `event_rules`,
   - copies the rule’s severity into each event,
   - inserts events idempotently,
   - advances `last_processed_cursor`,
   - sets the next attempt,
   - marks the execution `SUCCESS` or `FAILED`.

### Idempotency

`monitored_events` has:

```sql
UNIQUE (machine_id, cursor)
```

If a task is retried, duplicate rows are ignored using PostgreSQL `INSERT ... ON CONFLICT DO NOTHING`. This makes retries and out-of-order completion safe.

---

## 5. Database schema

| Table | Purpose |
|---|---|
| `event_rules` | Registered event codes, description, severity |
| `monitoring_tasks` | Schedules and cursor progress |
| `monitored_events` | Stored matching events |
| `task_executions` | Per-run audit history |

Alembic revision:

1. `133ef16cfedc_initial_migration.py` — creates the final schema directly, including nullable `event_description`, `severity`, and a partial unique index for active `event_code` values.


---

## 6. Tests

```powershell
docker compose exec api pytest -q
```

Tests use an in-memory SQLite database injected via `get_db` dependency override. No external services are needed.

Coverage:

| File | Covers |
|---|---|
| `tests/test_event_codes.py` | create, optional description, severity, duplicate, validation, list, soft delete, recreate |
| `tests/test_simulator.py` | snapshot metadata, empty range, unknown machine/file |
| `tests/test_tasks.py` | create, validation, unknown machine, pause/resume/delete, 404 |
| `tests/test_events.py` | list, filters, idempotency |
| `tests/test_generator.py` | source CSV append and cursor continuity |
| `tests/test_scheduler.py` | Beat schedule and due-task dispatch |
| `tests/test_worker.py` | CSV parsing helper |

`pytest.ini` sets `pythonpath = .` so `import app` works, and pins the asyncio fixture loop scope to remove warnings.

---

## 7. Project structure

```text
app/
├── api/v1/
│   ├── event_codes.py
│   ├── events.py
│   ├── simulator.py
│   └── tasks.py
├── core/
│   ├── celery.py
│   ├── config.py
│   ├── database.py
│   ├── exceptions.py
│   ├── machines.py
│   └── simulator_files.py
├── models/
│   ├── event_rule.py
│   ├── monitored_event.py
│   ├── monitoring_task.py
│   └── task_execution.py
├── repositories/
│   ├── event_code_repository.py
│   ├── event_repository.py
│   └── task_repository.py
├── schemas/
│   ├── event.py
│   ├── event_code.py
│   ├── simulator.py
│   └── task.py
├── services/
│   ├── event_code_service.py
│   ├── event_service.py
│   ├── simulator_service.py
│   └── task_service.py
├── workers/
│   ├── generator.py
│   └── tasks.py
└── main.py

migrations/versions/
tests/
docker-compose.yml
Dockerfile
requirements.txt
pytest.ini
.env.example
README.md
```

---

## 8. Assumptions and decisions

### 8.1 Assumptions

- The assignment defines the public contract, not the internal table names; the internal table remains `event_rules` with column `event_code`, while the API remains `/v1/event-codes`.
- Event codes are global. The specification does not define per-machine event codes.
- `machine_id` is an external simulator identifier. There is no `machines` table because the machines are predefined in configuration.
- Event codes can be soft-deleted. Deleted rules are hidden from list/create checks and from worker/generator selection.
- Severity is stored on the rule and copied onto each stored event at ingestion time.
- `/v1/events` returns stored matching events only, not raw simulator downloads.
- The generator continuously appends rows to per-machine source CSV files. `/v1/simulator/download` creates an immutable snapshot for safe worker reads.
- Authentication, multi-tenancy, operator UI and numeric severity levels are outside the assignment scope.

### 8.2 Design decisions

| Area | Decision | Why / rejected alternative |
|---|---|---|
| Architecture | Simple layered architecture: routes → services → repositories → SQLAlchemy models. | Easy to read and evaluate. Clean/Hexagonal architecture was rejected because it would add ports, adapters and extra folders without improving this small API. |
| Dependency management | Use `requirements.txt`. | Simple and expected for a small FastAPI project. `pyproject.toml` and `uv.lock` were rejected because they add tooling overhead without a requirement. |
| Migration execution | A one-shot `migrate` Compose service runs `alembic upgrade head` before API/worker/beat/generator start. | Migrations happen automatically on `docker compose up --build -d`. API, worker, beat and generator wait for `migrate` to complete successfully. |
| Event-code deletion | Use soft delete with `is_deleted=True`. | Preserves audit history and hides deleted codes from active reads. Hard delete was rejected because it removes history. |
| Event-code uniqueness | Use a partial unique index on active rows only: `UNIQUE(event_code) WHERE is_deleted = false`. | Prevents duplicate active codes while allowing a deleted code to be registered again. A full unique index was rejected because deleted rows would reserve codes forever. |
| Idempotent event storage | Use `UNIQUE(machine_id, cursor)` and PostgreSQL `ON CONFLICT DO NOTHING ... RETURNING id`. | Prevents duplicate event rows even if a task is retried. Check-then-insert was rejected because it has a race condition. |
| Scheduler design | Use one Celery Beat job, `dispatch_due_tasks`, that scans due tasks and enqueues `process_task`. | Easier to manage than per-task Beat entries. Pause/resume/delete only change DB state; no dynamic Beat schedule updates are needed. |
| Task timing | Store `next_attempt` on each task. After successful processing, the worker derives the next due time from `interval_seconds`. | Keeps scheduling state in the DB and separates each task’s cadence from Beat’s polling frequency. |
| Pause/resume/delete | Change task `status` and `next_attempt` instead of deleting rows. | Preserves execution history and keeps `/v1/events` traceable. Physical deletion was rejected because it would break audit history. |
| Celery worker retries | `process_task` retries failed jobs up to 3 times with a 60-second delay. | Handles transient API/download failures without manual intervention. Infinite retries were rejected because they can hide permanent bugs. |
| Simulator generator | Generator is a plain Python long-running service, not a Celery task. | It is a continuous loop, not a queued/retried job. Celery was rejected because its retry model does not fit continuous generation. |
| Simulator file safety | Generator writes per-machine source CSVs under a Redis lock; downloads create immutable snapshots. | Prevents concurrent read/write corruption. Serving source files directly was rejected because the generator keeps appending to them. |
| Redis usage | Redis is the Celery broker/backend and the simulator lock provider. | One shared Redis service covers queuing and file-access coordination. Added infrastructure was unnecessary. |
| Machine validation | Only `ETCH-001`, `ETCH-002` and `CNC-001` are accepted. | Keeps the simulator deterministic and evaluator-friendly. Dynamic machine registration was rejected because the assignment does not require it. |
| DB URL construction | Build `DATABASE_URL` from `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` and `DB_NAME`. | One password source of truth. A separate full `DATABASE_URL` was rejected because it risks mismatched credentials. |
| Worker API access | Worker uses `API_BASE_URL=http://api:8000` inside Compose. Host-side checks use `http://localhost:8000`. | Compose DNS resolves `api` inside the network, while the host publishes the API on `localhost:8000`. |
| Error handling | Central `AppError` class with one global FastAPI handler. | Keeps services free from FastAPI-specific `HTTPException`s and gives every business error a consistent `{"detail": ...}` response. |
| Tests | Use pytest with an in-memory SQLite DB and FastAPI `TestClient`. | Tests are fast and need no external PostgreSQL/Redis. Integration with real services is covered by Docker Compose startup. |


---

## 9. AI usage disclosure

An AI assistant (OpenCode) was used as a development aid for:

- documenting the layered structure,
- generating SQLAlchemy models, Alembic revisions,
- generating docker files,
- generating test cases,
- diagnosing Docker, pytest import and deprecation issues,
- reviewing the code
- writing this README.

All generated code was reviewed, adapted and validated against the assignment requirements before being included.

---

## 10. Future improvements

The current implementation is intentionally simple and focused on the assignment requirements. The following improvements would make it more production-ready:

| Area | Improvement | Benefit |
|---|---|---|
| Scheduling precision | Add fixed-rate scheduling anchored to `start_at`, or use Celery ETA/countdown instead of relying only on Beat polling. | Tasks would run closer to exact times such as `10:00:00`, `10:00:10`, and `10:00:20`, instead of waiting for the next Beat poll. |
| Authentication and authorization | Add API keys or JWT-based authentication for write endpoints. | Would protect event-code registration, task creation, pause/resume/delete and simulator downloads in a real deployment. |
| Pagination | Add `skip` and `limit` to `/v1/event-codes` and `/v1/events`. | Prevents large responses when many event codes or monitored events accumulate. |
| Restore endpoint | Add `POST /v1/event-codes/{event_code}/restore`. | Would allow an accidentally soft-deleted rule to be reactivated without creating a duplicate row. |
| Retention policy | Archive or delete old snapshots, source CSV rows and `task_executions` after a configurable period. | Prevents unbounded disk and database growth in a long-running deployment. |
| Observability | Add structured JSON logs, request IDs, metrics and Celery Flower. | Easier debugging of request flows, task retries, queue depth and worker performance. |
| CI pipeline | Add GitHub Actions to run `pytest`, `docker compose config`, `docker build`, and Alembic checks on every push. | Prevents broken commits and confirms the evaluator can build and test the project cleanly. |
| Concurrency hardening | Replace Redis-only file locking with stronger coordination, such as DB advisory locks or an append-only event store. | Improves correctness under higher concurrency and multiple generator instances. |
| Secrets management | Use Docker secrets or an external secret manager instead of `.env` for production. | Reduces the risk of accidental credential leaks. |
| Performance tuning | Add query plans, bulk operation tuning and targeted indexes after load testing. | Ensures the API remains responsive as event volume grows. |