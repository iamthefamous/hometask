import asyncio

from app.schemas.article import ArticleProcessResponse
from app.schemas.rescan import RescanError, RescanResponse
from app.services.article_extractor_service import ArticleExtractorService
from app.services.crawler_service import CrawlerService
from app.services.graph_storage_service import GraphStorageService
from app.services.llm_analysis_service import LLMAnalysisService


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
        async with self.semaphore:
            article = await self.extractor.extract(url)
            graph = await self.llm.analyze(article)
            people_count, relationships_count = await self.storage.save_graph(article, graph)

        return ArticleProcessResponse(
            url=url,
            status="processed",
            people_count=people_count,
            relationships_count=relationships_count,
        )

    async def rescan(self, pages: int) -> RescanResponse:
        urls = await self.crawler.get_article_urls(pages)

        tasks = [self.process_article(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed = 0
        errors: list[RescanError] = []

        for url, result in zip(urls, results, strict=False):
            if isinstance(result, Exception):
                errors.append(RescanError(url=url, error=str(result)))
            else:
                processed += 1

        return RescanResponse(
            pages_scanned=pages,
            urls_found=len(urls),
            processed=processed,
            failed=len(errors),
            errors=errors,
        )
