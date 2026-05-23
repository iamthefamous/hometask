from app.schemas.article import ArticleData
from app.services.llm_analysis_service import LLMAnalysisService


def _article() -> ArticleData:
    return ArticleData(
        url="https://techcrunch.com/example",
        title="Example",
        authors=["Sam Altman"],
        text="Sam Altman discussed model safety with Elon Musk.",
    )


async def test_llm_analysis_service_mock_returns_authors(monkeypatch):
    monkeypatch.setattr("app.services.llm_analysis_service.settings.llm_provider", "mock")
    service = LLMAnalysisService()

    result = await service.analyze(_article())

    assert len(result.people) == 1
    assert result.people[0].name == "Sam Altman"
    assert result.relationships == []

