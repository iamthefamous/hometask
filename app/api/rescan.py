from fastapi import APIRouter, Depends

from app.api.deps import get_pipeline_service
from app.schemas.rescan import RescanRequest, RescanResponse
from app.services.pipeline_service import PipelineService

router = APIRouter(prefix="/rescan", tags=["rescan"])


@router.post("", response_model=RescanResponse)
async def rescan(
    payload: RescanRequest,
    pipeline: PipelineService = Depends(get_pipeline_service),
):
    return await pipeline.rescan(payload.pages)
