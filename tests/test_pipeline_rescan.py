import asyncio

import pytest

from app.services.pipeline_service import PipelineService


class _Crawler:
    async def get_article_urls(self, pages: int):
        return ["https://a", "https://b"]


class _Extractor:
    async def extract(self, url: str):
        if url.endswith("b"):
            raise ValueError("bad article")
        return type(
            "A",
            (),
            {
                "url": url,
                "title": "Example",
                "authors": [],
                "model_dump": lambda self: {"url": url, "text": "t"},
            },
        )()


class _LLM:
    async def analyze(self, article):
        return type("G", (), {"people": [], "relationships": []})()


class _Storage:
    async def save_graph(self, article, graph):
        return 0, 0


@pytest.mark.asyncio
async def test_rescan_continues_if_one_article_fails():
    svc = PipelineService(_Crawler(), _Extractor(), _LLM(), _Storage(), 5)
    result = await svc.rescan(1)

    assert result.urls_found == 2
    assert result.processed == 1
    assert result.failed == 1
    assert result.errors[0].url == "https://b"


class _LLMWithUsage:
    async def analyze_with_usage(self, article):
        return type("G", (), {"people": [], "relationships": []})(), 42


@pytest.mark.asyncio
async def test_rescan_logs_total_tokens(caplog):
    svc = PipelineService(_Crawler(), _Extractor(), _LLMWithUsage(), _Storage(), 5)
    with caplog.at_level("INFO"):
        result = await svc.rescan(1)

    assert result.processed == 1
    assert any(
        "rescan_done" in rec.message and "total_tokens=42" in rec.message
        for rec in caplog.records
    )


class _CrawlerWithUrls:
    def __init__(self, urls):
        self.urls = urls

    async def get_article_urls(self, pages: int):
        return self.urls


class _TrackingExtractor:
    def __init__(self):
        self.active = 0
        self.max_active = 0

    async def extract(self, url: str):
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0.01)
        self.active -= 1
        return type(
            "A",
            (),
            {
                "url": url,
                "title": "Example",
                "authors": [],
                "model_dump": lambda self: {"url": url, "text": "t"},
            },
        )()


@pytest.mark.asyncio
async def test_rescan_processes_urls_in_configured_llm_batches():
    urls = [f"https://example.com/{index}" for index in range(6)]
    extractor = _TrackingExtractor()
    svc = PipelineService(
        _CrawlerWithUrls(urls),
        extractor,
        _LLM(),
        _Storage(),
        max_concurrent_articles=6,
        llm_article_batch_size=2,
    )

    result = await svc.rescan(1)

    assert result.processed == 6
    assert extractor.max_active == 2
