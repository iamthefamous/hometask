import json
import asyncio
import logging
from pathlib import Path

from google import genai
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
        self.model = settings.gemini_model
        self.max_article_chars = settings.max_llm_article_chars

    async def analyze(self, article: ArticleData) -> LLMGraphOutput:
        graph, _ = await self.analyze_with_usage(article)
        return graph

    async def analyze_with_usage(
        self, article: ArticleData
    ) -> tuple[LLMGraphOutput, int]:
        payload, total_tokens = await self._call_gemini_generate_content(article)
        try:
            return LLMGraphOutput.model_validate(payload), total_tokens
        except (json.JSONDecodeError, ValidationError) as exc:
            raise LLMValidationError(f"Invalid LLM output: {exc}") from exc

    async def _call_gemini_generate_content(
        self, article: ArticleData
    ) -> tuple[dict, int]:
        if not settings.gemini_api_key:
            raise LLMValidationError("GEMINI_API_KEY is required for LLM analysis")

        article_text = self._truncate_article_text(article.text)
        prompt = (
            f"{self.prompt_template}\n\n"
            f"Article URL: {article.url}\n"
            f"Title: {article.title}\n"
            f"Authors: {', '.join(article.authors) if article.authors else 'unknown'}\n"
            f"Published At: {article.published_at or 'unknown'}\n\n"
            f"Article Text:\n{article_text}"
        )

        client = genai.Client(api_key=settings.gemini_api_key)
        logger.info(
            "llm_attempt provider=gemini model=%s url=%s",
            self.model,
            str(article.url),
        )
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=prompt,
                config={
                    "temperature": 0,
                    "response_mime_type": "application/json",
                },
            )
        except Exception as exc:
            raise LLMValidationError(f"Gemini API request failed: {exc}") from exc

        logger.info(
            "llm_success provider=gemini model=%s url=%s",
            self.model,
            str(article.url),
        )

        text = getattr(response, "text", None)
        if not isinstance(text, str) or not text.strip():
            raise LLMValidationError(
                "Gemini response is not valid content JSON: missing text"
            )

        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()

        try:
            return json.loads(cleaned), self._extract_gemini_total_tokens(response)
        except json.JSONDecodeError as exc:
            raise LLMValidationError(
                f"Gemini output is not valid graph JSON: {exc}"
            ) from exc

    def _extract_gemini_total_tokens(self, response: object) -> int:
        usage = getattr(response, "usage_metadata", None)
        if usage is None:
            return 0
        total = getattr(usage, "total_token_count", None)
        if isinstance(total, int):
            return total
        return 0

    def _truncate_article_text(self, text: str) -> str:
        if len(text) <= self.max_article_chars:
            return text
        return text[: self.max_article_chars]
