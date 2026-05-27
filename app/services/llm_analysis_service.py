import json
import asyncio
import logging
from pathlib import Path

import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.article import ArticleData
from app.schemas.llm import LLMGraphOutput
from app.utils.exceptions import LLMValidationError

logger = logging.getLogger(__name__)


class LLMAnalysisService:
    def __init__(self):
        prompt_path = (
            Path(__file__).resolve().parents[1]
            / "prompts"
            / "graph_extraction_prompt.txt"
        )
        self.prompt_template = (
            prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
        )
        self.provider = settings.llm_provider.lower().strip()
        self.model = settings.openai_model
        self.max_article_chars = settings.max_llm_article_chars
        self.max_retries = settings.llm_max_retries
        self.retry_base_delay_seconds = settings.llm_retry_base_delay_seconds
        self.fallback_models = self._parse_fallback_models(settings.llm_fallback_models)

    async def analyze(self, article: ArticleData) -> LLMGraphOutput:
        graph, _ = await self.analyze_with_usage(article)
        return graph

    async def analyze_with_usage(
        self, article: ArticleData
    ) -> tuple[LLMGraphOutput, int]:
        payload, total_tokens = await self._analyze_with_provider(article)
        try:
            return LLMGraphOutput.model_validate(payload), total_tokens
        except (json.JSONDecodeError, ValidationError) as exc:
            raise LLMValidationError(f"Invalid LLM output: {exc}") from exc

    async def _analyze_with_provider(self, article: ArticleData) -> tuple[dict, int]:
        if self.provider == "mock":
            return (
                {
                    "people": [
                        {"name": author, "aliases": []} for author in article.authors
                    ],
                    "relationships": [],
                },
                0,
            )
        if self.provider == "gemini":
            return await self._call_gemini_generate_content(article)
        if self.provider in {"ollama", "openai"}:
            return await self._call_chat_completions(article)
        raise LLMValidationError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")

    async def _call_chat_completions(self, article: ArticleData) -> tuple[dict, int]:
        if self.provider == "openai" and not (
            settings.llm_api_key or settings.openai_api_key
        ):
            raise LLMValidationError(
                "OPENAI_API_KEY or LLM_API_KEY is required when LLM_PROVIDER=openai"
            )

        article_text = self._truncate_article_text(article.text)
        user_prompt = (
            f"Article URL: {article.url}\n"
            f"Title: {article.title}\n"
            f"Authors: {', '.join(article.authors) if article.authors else 'unknown'}\n"
            f"Published At: {article.published_at or 'unknown'}\n\n"
            f"Article Text:\n{article_text}"
        )

        headers = {"Content-Type": "application/json"}
        if settings.llm_api_key:
            headers["Authorization"] = f"Bearer {settings.llm_api_key}"
        elif self.provider == "openai":
            headers["Authorization"] = f"Bearer {settings.openai_api_key}"

        endpoint = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
        timeout = settings.request_timeout_seconds
        model_errors: list[str] = []
        async with httpx.AsyncClient(timeout=timeout) as client:
            for model in self._candidate_models():
                body = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": self.prompt_template},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                }
                logger.info(
                    "llm_attempt provider=%s model=%s url=%s",
                    self.provider,
                    model,
                    str(article.url),
                )
                try:
                    data = await self._post_json_with_retries(
                        client, endpoint, headers, body, "Provider API"
                    )
                    logger.info(
                        "llm_success provider=%s model=%s url=%s",
                        self.provider,
                        model,
                        str(article.url),
                    )
                    break
                except LLMValidationError as exc:
                    msg = str(exc)
                    model_errors.append(f"{model}: {msg}")
                    logger.warning(
                        "llm_failed provider=%s model=%s url=%s error=%s",
                        self.provider,
                        model,
                        str(article.url),
                        msg[:400],
                    )
                    if self._is_fallback_error(msg):
                        continue
                    raise
            else:
                raise LLMValidationError(
                    f"All models failed: {' | '.join(model_errors)}"
                )

        try:
            content = data["choices"][0]["message"]["content"]
            total_tokens = self._extract_openai_total_tokens(data)
            if isinstance(content, dict):
                return content, total_tokens
            return json.loads(content), total_tokens
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LLMValidationError(
                f"Provider response is not valid graph JSON: {exc}"
            ) from exc

    async def _call_gemini_generate_content(
        self, article: ArticleData
    ) -> tuple[dict, int]:
        if not settings.llm_api_key:
            raise LLMValidationError(
                "LLM_API_KEY (or GEMINI_API_KEY alias) is required when LLM_PROVIDER=gemini"
            )

        article_text = self._truncate_article_text(article.text)
        prompt = (
            f"{self.prompt_template}\n\n"
            f"Article URL: {article.url}\n"
            f"Title: {article.title}\n"
            f"Authors: {', '.join(article.authors) if article.authors else 'unknown'}\n"
            f"Published At: {article.published_at or 'unknown'}\n\n"
            f"Article Text:\n{article_text}"
        )

        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": settings.llm_api_key,
        }
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
            },
        }
        endpoint = (
            f"{settings.llm_base_url.rstrip('/')}/models/{self.model}:generateContent"
        )
        timeout = settings.request_timeout_seconds

        async with httpx.AsyncClient(timeout=timeout) as client:
            data = await self._post_json_with_retries(
                client, endpoint, headers, body, "Gemini API"
            )

        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMValidationError(
                f"Gemini response is not valid content JSON: {exc}"
            ) from exc

        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()

        try:
            return json.loads(cleaned), self._extract_gemini_total_tokens(data)
        except json.JSONDecodeError as exc:
            raise LLMValidationError(
                f"Gemini output is not valid graph JSON: {exc}"
            ) from exc

    def _extract_openai_total_tokens(self, data: dict) -> int:
        usage = data.get("usage")
        if not isinstance(usage, dict):
            return 0
        total = usage.get("total_tokens")
        if isinstance(total, int):
            return total
        return 0

    def _extract_gemini_total_tokens(self, data: dict) -> int:
        usage = data.get("usageMetadata")
        if not isinstance(usage, dict):
            return 0
        total = usage.get("totalTokenCount")
        if isinstance(total, int):
            return total
        return 0

    def _truncate_article_text(self, text: str) -> str:
        if len(text) <= self.max_article_chars:
            return text
        return text[: self.max_article_chars]

    async def _post_json_with_retries(
        self,
        client: httpx.AsyncClient,
        endpoint: str,
        headers: dict[str, str],
        body: dict,
        label: str,
    ) -> dict:
        attempts = self.max_retries + 1
        for attempt in range(1, attempts + 1):
            try:
                response = await client.post(endpoint, headers=headers, json=body)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code if exc.response is not None else None
                retryable = status == 429 or (
                    status is not None and 500 <= status < 600
                )
                if retryable and attempt < attempts:
                    await asyncio.sleep(self._retry_delay_seconds(attempt))
                    continue
                detail = (
                    exc.response.text[:1000] if exc.response is not None else str(exc)
                )
                raise LLMValidationError(f"{label} error: {detail}") from exc
            except httpx.RequestError as exc:
                if attempt < attempts:
                    await asyncio.sleep(self._retry_delay_seconds(attempt))
                    continue
                raise LLMValidationError(f"{label} request failed: {exc}") from exc
        raise LLMValidationError(f"{label} request failed after retries")

    def _retry_delay_seconds(self, attempt: int) -> float:
        return self.retry_base_delay_seconds * (2 ** (attempt - 1))

    def _candidate_models(self) -> list[str]:
        models = [self.model, *self.fallback_models]
        unique: list[str] = []
        seen: set[str] = set()
        for model in models:
            if model and model not in seen:
                unique.append(model)
                seen.add(model)
        return unique

    def _parse_fallback_models(self, raw: str) -> list[str]:
        return [part.strip() for part in raw.split(",") if part.strip()]

    def _is_fallback_error(self, message: str) -> bool:
        lowered = message.lower()
        return any(
            token in lowered
            for token in [
                "429",
                "rate_limit_exceeded",
                "request too large for model",
                "tokens per minute",
                "context_length_exceeded",
            ]
        )
