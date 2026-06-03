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


async def test_llm_analysis_service_mock_returns_authors(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_analysis_service.settings.llm_provider", "mock"
    )
    service = LLMAnalysisService()

    result = await service.analyze(_article())

    assert len(result.people) == 1
    assert result.people[0].name == "Sam Altman"
    assert result.relationships == []


async def test_llm_analysis_service_rejects_blank_relationship_fields(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_analysis_service.settings.llm_provider", "mock"
    )
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

    monkeypatch.setattr(service, "_analyze_with_provider", _bad_payload)

    try:
        await service.analyze(_article())
        assert False, "Expected LLMValidationError for blank relationship source"
    except LLMValidationError:
        pass


async def test_llm_analysis_service_rejects_blank_person_name(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_analysis_service.settings.llm_provider", "mock"
    )
    service = LLMAnalysisService()

    async def _bad_payload(_article):
        return (
            {
                "people": [{"name": "   ", "aliases": []}],
                "relationships": [],
            },
            0,
        )

    monkeypatch.setattr(service, "_analyze_with_provider", _bad_payload)

    try:
        await service.analyze(_article())
        assert False, "Expected LLMValidationError for blank person name"
    except LLMValidationError:
        pass


async def test_llm_analysis_service_rejects_extra_top_level_fields(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_analysis_service.settings.llm_provider", "mock"
    )
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

    monkeypatch.setattr(service, "_analyze_with_provider", _bad_payload)

    try:
        await service.analyze(_article())
        assert False, "Expected LLMValidationError for extra top-level fields"
    except LLMValidationError:
        pass


async def test_openai_provider_accepts_llm_api_key_without_openai_api_key(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_analysis_service.settings.llm_provider", "openai"
    )
    monkeypatch.setattr("app.services.llm_analysis_service.settings.openai_api_key", "")
    monkeypatch.setattr(
        "app.services.llm_analysis_service.settings.llm_api_key", "test-key"
    )

    service = LLMAnalysisService()

    async def _fake_call(_article):
        return {"people": [], "relationships": []}, 0

    monkeypatch.setattr(service, "_call_chat_completions", _fake_call)

    result = await service.analyze(_article())
    assert result.relationships == []


async def test_gemini_provider_uses_generate_content(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_analysis_service.settings.llm_provider", "gemini"
    )
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
        "app.services.llm_analysis_service.settings.llm_provider", "gemini"
    )
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

    monkeypatch.setattr("app.services.llm_analysis_service.genai.Client", _Client)

    service = LLMAnalysisService()
    graph, tokens = await service._call_gemini_generate_content(_article())

    assert calls["api_key"] == "test-key"
    assert calls["model"] == "gemini-3.1-flash-lite"
    assert "Article Text:" in calls["contents"]
    assert calls["config"]["response_mime_type"] == "application/json"
    assert graph == {"people": [], "relationships": []}
    assert tokens == 7


async def test_openai_fallback_to_second_model_on_rate_limit(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_analysis_service.settings.llm_provider", "openai"
    )
    monkeypatch.setattr(
        "app.services.llm_analysis_service.settings.llm_api_key", "test-key"
    )
    monkeypatch.setattr(
        "app.services.llm_analysis_service.settings.openai_model", "model-a"
    )
    monkeypatch.setattr(
        "app.services.llm_analysis_service.settings.llm_fallback_models",
        "model-b,model-c",
    )

    service = LLMAnalysisService()
    attempted_models: list[str] = []

    async def _fake_post(_client, _endpoint, _headers, body, _label):
        model = body["model"]
        attempted_models.append(model)
        if model == "model-a":
            raise LLMValidationError("Provider API error: rate_limit_exceeded")
        return {
            "choices": [{"message": {"content": '{"people": [], "relationships": []}'}}]
        }

    monkeypatch.setattr(service, "_post_json_with_retries", _fake_post)
    result = await service.analyze(_article())

    assert attempted_models == ["model-a", "model-b"]
    assert result.people == []


async def test_openai_fallback_exhausted_returns_combined_error(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_analysis_service.settings.llm_provider", "openai"
    )
    monkeypatch.setattr(
        "app.services.llm_analysis_service.settings.llm_api_key", "test-key"
    )
    monkeypatch.setattr(
        "app.services.llm_analysis_service.settings.openai_model", "model-a"
    )
    monkeypatch.setattr(
        "app.services.llm_analysis_service.settings.llm_fallback_models", "model-b"
    )

    service = LLMAnalysisService()

    async def _fake_post(_client, _endpoint, _headers, body, _label):
        raise LLMValidationError(
            f"Provider API error: rate_limit_exceeded for {body['model']}"
        )

    monkeypatch.setattr(service, "_post_json_with_retries", _fake_post)

    try:
        await service.analyze(_article())
        assert False, "Expected LLMValidationError"
    except LLMValidationError as exc:
        message = str(exc)
        assert "All models failed" in message
        assert "model-a" in message
        assert "model-b" in message


def test_truncate_article_text(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_analysis_service.settings.llm_provider", "mock"
    )
    monkeypatch.setattr(
        "app.services.llm_analysis_service.settings.max_llm_article_chars", 10
    )
    service = LLMAnalysisService()
    assert service._truncate_article_text("1234567890123") == "1234567890"


def test_retry_delay_seconds(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_analysis_service.settings.llm_provider", "mock"
    )
    monkeypatch.setattr(
        "app.services.llm_analysis_service.settings.llm_retry_base_delay_seconds", 0.5
    )
    service = LLMAnalysisService()
    assert service._retry_delay_seconds(1) == 0.5
    assert service._retry_delay_seconds(2) == 1.0
    assert service._retry_delay_seconds(3) == 2.0


def test_parse_fallback_models(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_analysis_service.settings.llm_provider", "mock"
    )
    monkeypatch.setattr(
        "app.services.llm_analysis_service.settings.llm_fallback_models",
        " a , b ,, c ",
    )
    service = LLMAnalysisService()
    assert service.fallback_models == ["a", "b", "c"]
