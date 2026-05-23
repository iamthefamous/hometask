import json
from pathlib import Path

import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.article import ArticleData
from app.schemas.llm import LLMGraphOutput
from app.utils.exceptions import LLMValidationError


class LLMAnalysisService:
    def __init__(self):
        prompt_path = Path(__file__).resolve().parents[1] / "prompts" / "graph_extraction_prompt.txt"
        self.prompt_template = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
        self.provider = settings.llm_provider.lower().strip()
        self.model = settings.openai_model

    async def analyze(self, article: ArticleData) -> LLMGraphOutput:
        payload = await self._analyze_with_provider(article)
        try:
            return LLMGraphOutput.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise LLMValidationError(f"Invalid LLM output: {exc}") from exc

    async def _analyze_with_provider(self, article: ArticleData) -> dict:
        if self.provider == "mock":
            return {
                "people": [{"name": author, "aliases": []} for author in article.authors],
                "relationships": [],
            }
        if self.provider in {"ollama", "openai"}:
            return await self._call_chat_completions(article)
        raise LLMValidationError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")

    async def _call_chat_completions(self, article: ArticleData) -> dict:
        if self.provider == "openai" and not settings.openai_api_key:
            raise LLMValidationError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

        user_prompt = (
            f"Article URL: {article.url}\n"
            f"Title: {article.title}\n"
            f"Authors: {', '.join(article.authors) if article.authors else 'unknown'}\n"
            f"Published At: {article.published_at or 'unknown'}\n\n"
            f"Article Text:\n{article.text}"
        )

        headers = {"Content-Type": "application/json"}
        if settings.llm_api_key:
            headers["Authorization"] = f"Bearer {settings.llm_api_key}"
        elif self.provider == "openai":
            headers["Authorization"] = f"Bearer {settings.openai_api_key}"

        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.prompt_template},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }

        endpoint = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
        timeout = settings.request_timeout_seconds
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(endpoint, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()

        try:
            content = data["choices"][0]["message"]["content"]
            if isinstance(content, dict):
                return content
            return json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LLMValidationError(f"Provider response is not valid graph JSON: {exc}") from exc
