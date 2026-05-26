import pytest

from app.api.articles import process_article
from app.schemas.article import ArticleProcessRequest, ArticleProcessResponse


class _Pipeline:
    async def process_article(self, url: str) -> ArticleProcessResponse:
        return ArticleProcessResponse(
            url=url,
            status="processed",
            people_count=3,
            relationships_count=2,
        )


@pytest.mark.asyncio
async def test_process_article_endpoint_function():
    payload = ArticleProcessRequest(url="https://techcrunch.com/2026/01/01/example")
    response = await process_article(payload=payload, pipeline=_Pipeline())
    assert response.status == "processed"
    assert response.people_count == 3
    assert response.relationships_count == 2
