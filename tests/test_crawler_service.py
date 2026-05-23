import pytest

from app.services.crawler_service import CrawlerService


class _Resp:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        return None


class _Client:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, _url: str):
        return _Resp(
            '<a href="https://techcrunch.com/2026/01/01/a">a</a>'
            '<a href="https://techcrunch.com/2026/01/01/b/">b</a>'
            '<a href="https://example.com/ignore">x</a>'
        )


@pytest.mark.asyncio
async def test_crawler_extracts_article_urls(monkeypatch):
    monkeypatch.setattr("app.services.crawler_service.httpx.AsyncClient", lambda **_: _Client())
    service = CrawlerService()
    urls = await service.get_article_urls(1)
    assert urls == [
        "https://techcrunch.com/2026/01/01/a",
        "https://techcrunch.com/2026/01/01/b/",
    ]
