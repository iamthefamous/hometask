from functools import lru_cache

from app.core.config import settings
from app.db.mongo import get_database
from app.repositories.article_repository import ArticleRepository
from app.repositories.person_repository import PersonRepository
from app.repositories.relationship_repository import RelationshipRepository
from app.services.article_extractor_service import ArticleExtractorService
from app.services.crawler_service import CrawlerService
from app.services.graph_storage_service import GraphStorageService
from app.services.llm_analysis_service import LLMAnalysisService
from app.services.pipeline_service import PipelineService


@lru_cache
def get_pipeline_service() -> PipelineService:
    db = get_database()
    storage = GraphStorageService(
        article_repo=ArticleRepository(db),
        person_repo=PersonRepository(db),
        relationship_repo=RelationshipRepository(db),
    )
    return PipelineService(
        crawler=CrawlerService(timeout_seconds=settings.request_timeout_seconds),
        extractor=ArticleExtractorService(
            timeout_seconds=settings.request_timeout_seconds
        ),
        llm=LLMAnalysisService(),
        storage=storage,
        max_concurrent_articles=settings.max_concurrent_articles,
        llm_article_batch_size=settings.llm_article_batch_size,
    )


@lru_cache
def get_person_repository() -> PersonRepository:
    return PersonRepository(get_database())


@lru_cache
def get_relationship_repository() -> RelationshipRepository:
    return RelationshipRepository(get_database())
