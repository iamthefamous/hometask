from fastapi import APIRouter, Depends

from app.api.deps import get_pipeline_service
from app.schemas.article import ArticleProcessRequest, ArticleProcessResponse
from app.services.pipeline_service import PipelineService

router = APIRouter(prefix="/articles", tags=["articles"])


@router.post("", response_model=ArticleProcessResponse)
async def process_article(
    payload: ArticleProcessRequest,
    pipeline: PipelineService = Depends(get_pipeline_service),
):
    return await pipeline.process_article(str(payload.url))
