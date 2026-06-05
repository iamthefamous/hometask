from app.core.config import Settings
from app.schemas.article import ArticleData
from app.services.llm_analysis_service import LLMAnalysisService
from app.utils.exceptions import LLMValidationError


def _article() -> ArticleData:
    return ArticleData(
        url="https://techcrunch.com/example",
        title="Example",
        authors=["Sam Altman"],
        text="Sam Altman discussed model safety with Elon Musk.",
    )


def test_gemini_model_defaults_to_flash_lite(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    config = Settings(_env_file=None)

    assert config.gemini_model == "gemini-3.1-flash-lite"


def test_max_concurrent_agents_alias(monkeypatch):
    monkeypatch.setenv("MAX_CONCURRENT_AGENTS", "9")
    monkeypatch.delenv("MAX_CONCURRENT_ARTICLES", raising=False)
    config = Settings(_env_file=None)

    assert config.max_concurrent_articles == 9


def test_llm_article_batch_size_comes_from_env(monkeypatch):
    monkeypatch.setenv("LLM_ARTICLE_BATCH_SIZE", "3")
    config = Settings(_env_file=None)

    assert config.llm_article_batch_size == 3


async def test_llm_analysis_service_rejects_blank_relationship_fields(monkeypatch):
    service = LLMAnalysisService()

    async def _bad_payload(_article):
        return (
            {
                "people": [{"name": "Sam Altman", "aliases": []}],
                "relationships": [
                    {
                        "source": "   ",
                        "target": "Elon Musk",
                        "type": "criticizes",
                        "explanation": "x",
                        "evidence": "y",
                    }
                ],
            },
            0,
        )

    monkeypatch.setattr(service, "_call_gemini_generate_content", _bad_payload)

    try:
        await service.analyze(_article())
        assert False, "Expected LLMValidationError for blank relationship source"
    except LLMValidationError:
        pass


async def test_llm_analysis_service_rejects_blank_person_name(monkeypatch):
    service = LLMAnalysisService()

    async def _bad_payload(_article):
        return (
            {
                "people": [{"name": "   ", "aliases": []}],
                "relationships": [],
            },
            0,
        )

    monkeypatch.setattr(service, "_call_gemini_generate_content", _bad_payload)

    try:
        await service.analyze(_article())
        assert False, "Expected LLMValidationError for blank person name"
    except LLMValidationError:
        pass


async def test_llm_analysis_service_rejects_extra_top_level_fields(monkeypatch):
    service = LLMAnalysisService()

    async def _bad_payload(_article):
        return (
            {
                "people": [{"name": "Sam Altman", "aliases": []}],
                "relationships": [],
                "meta": {"confidence": 0.8},
            },
            0,
        )

    monkeypatch.setattr(service, "_call_gemini_generate_content", _bad_payload)

    try:
        await service.analyze(_article())
        assert False, "Expected LLMValidationError for extra top-level fields"
    except LLMValidationError:
        pass


async def test_gemini_provider_uses_generate_content(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_analysis_service.settings.gemini_api_key", "test-key"
    )

    service = LLMAnalysisService()

    async def _fake_gemini_call(_article):
        return (
            {
                "people": [
                    {"name": "Sam Altman", "aliases": ["Altman"]},
                    {"name": "Elon Musk", "aliases": ["Musk"]},
                ],
                "relationships": [
                    {
                        "source": "Elon Musk",
                        "target": "Sam Altman",
                        "type": "criticizes",
                        "explanation": "Musk criticized Altman.",
                        "evidence": "Musk criticized OpenAI CEO Sam Altman.",
                    }
                ],
            },
            0,
        )

    monkeypatch.setattr(service, "_call_gemini_generate_content", _fake_gemini_call)
    result = await service.analyze(_article())

    assert len(result.people) == 2
    assert len(result.relationships) == 1


async def test_gemini_provider_calls_google_genai_with_configured_model(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_analysis_service.settings.gemini_api_key", "test-key"
    )
    monkeypatch.setattr(
        "app.services.llm_analysis_service.settings.gemini_model",
        "gemini-3.1-flash-lite",
    )

    calls = {}

    class _Usage:
        total_token_count = 7

    class _Response:
        text = '{"people": [], "relationships": []}'
        usage_metadata = _Usage()

    class _Models:
        def generate_content(self, *, model, contents, config):
            calls["model"] = model
            calls["contents"] = contents
            calls["config"] = config
            return _Response()

    class _Client:
        def __init__(self, *, api_key):
            calls["api_key"] = api_key
            self.models = _Models()

    async def _to_thread(func, /, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr("app.services.llm_analysis_service.genai.Client", _Client)
    monkeypatch.setattr(
        "app.services.llm_analysis_service.asyncio.to_thread", _to_thread
    )

    service = LLMAnalysisService()
    graph, tokens = await service._call_gemini_generate_content(_article())

    assert calls["api_key"] == "test-key"
    assert calls["model"] == "gemini-3.1-flash-lite"
    assert "Article Text:" in calls["contents"]
    assert calls["config"]["response_mime_type"] == "application/json"
    assert graph == {"people": [], "relationships": []}
    assert tokens == 7


def test_truncate_article_text(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_analysis_service.settings.max_llm_article_chars", 10
    )
    service = LLMAnalysisService()
    assert service._truncate_article_text("1234567890123") == "1234567890"
