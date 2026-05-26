import asyncio
import logging

from app.schemas.article import ArticleProcessResponse
from app.schemas.rescan import RescanError, RescanResponse
from app.services.article_extractor_service import ArticleExtractorService
from app.services.crawler_service import CrawlerService
from app.services.graph_storage_service import GraphStorageService
from app.services.llm_analysis_service import LLMAnalysisService

logger = logging.getLogger(__name__)


class PipelineService:
    def __init__(
        self,
        crawler: CrawlerService,
        extractor: ArticleExtractorService,
        llm: LLMAnalysisService,
        storage: GraphStorageService,
        max_concurrent_articles: int,
    ):
        self.crawler = crawler
        self.extractor = extractor
        self.llm = llm
        self.storage = storage
        self.semaphore = asyncio.Semaphore(max_concurrent_articles)

    async def process_article(self, url: str) -> ArticleProcessResponse:
        response, _ = await self._process_article_with_metrics(url)
        return response

    async def _process_article_with_metrics(
        self, url: str
    ) -> tuple[ArticleProcessResponse, int]:
        logger.info("article_process_start url=%s", url)
        async with self.semaphore:
            article = await self.extractor.extract(url)
            logger.info(
                "article_extract_success url=%s title=%s", url, article.title[:120]
            )
            if hasattr(self.llm, "analyze_with_usage"):
                graph, total_tokens = await self.llm.analyze_with_usage(article)
            else:
                graph = await self.llm.analyze(article)
                total_tokens = 0
            logger.info(
                "article_llm_success url=%s people=%d relationships=%d total_tokens=%d",
                url,
                len(graph.people),
                len(graph.relationships),
                total_tokens,
            )
            people_count, relationships_count = await self.storage.save_graph(
                article, graph
            )
            logger.info(
                "article_store_success url=%s people_count=%d relationships_count=%d",
                url,
                people_count,
                relationships_count,
            )

        return (
            ArticleProcessResponse(
                url=url,
                status="processed",
                people_count=people_count,
                relationships_count=relationships_count,
            ),
            total_tokens,
        )

    async def rescan(self, pages: int) -> RescanResponse:
        urls = await self.crawler.get_article_urls(pages)
        logger.info("rescan_start pages=%d urls_found=%d", pages, len(urls))

        tasks = [self._process_article_with_metrics(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed = 0
        total_tokens = 0
        errors: list[RescanError] = []

        for url, result in zip(urls, results, strict=False):
            if isinstance(result, Exception):
                logger.error("article_process_failed url=%s error=%s", url, str(result))
                errors.append(RescanError(url=url, error=str(result)))
            else:
                _, article_tokens = result
                processed += 1
                total_tokens += article_tokens
        logger.info(
            "rescan_done pages=%d processed=%d failed=%d total_tokens=%d",
            pages,
            processed,
            len(errors),
            total_tokens,
        )

        return RescanResponse(
            pages_scanned=pages,
            urls_found=len(urls),
            processed=processed,
            failed=len(errors),
            errors=errors,
        )
