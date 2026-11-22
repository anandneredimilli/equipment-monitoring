from fastapi import APIRouter
from fastapi.responses import Response

from app.schemas.simulator import DownloadMetadata, DownloadRequest
from app.services.simulator_service import SimulatorService

router = APIRouter(prefix="/v1/simulator", tags=["Simulator"])


@router.post("/download", response_model=DownloadMetadata)
def download_file(payload: DownloadRequest):
    return SimulatorService().download(payload)


@router.get("/files/{file_name}")
def get_file(file_name: str):
    content = SimulatorService.read_snapshot(file_name)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
