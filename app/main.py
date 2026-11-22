from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1.event_codes import router as event_codes_router
from app.api.v1.events import router as events_router
from app.api.v1.simulator import router as simulator_router
from app.api.v1.tasks import router as tasks_router
from app.core.exceptions import AppError

app = FastAPI(
    title="Scheduled Equipment Event Monitoring API",
    description="Backend service for monitoring machine events.",
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(simulator_router)
app.include_router(event_codes_router)
app.include_router(tasks_router)
app.include_router(events_router)


@app.get("/health")
def health_check():
    return {"status": "healthy"}
