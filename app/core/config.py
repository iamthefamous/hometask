from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "news-kg-api"
    env: str = "development"

    mongodb_uri: str = Field(
        default="mongodb://localhost:27017",
        validation_alias=AliasChoices("MONGODB_URI", "MONGO_URI"),
    )
    mongodb_db_name: str = Field(
        default="news_kg",
        validation_alias=AliasChoices("MONGODB_DB_NAME", "MONGO_DB_NAME"),
    )

    openai_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("OPENAI_API_KEY"),
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices("OPENAI_MODEL", "LLM_MODEL", "GEMINI_MODEL"),
    )
    llm_provider: str = Field(
        default="mock",
        validation_alias=AliasChoices("LLM_PROVIDER"),
    )
    llm_base_url: str = Field(
        default="http://localhost:11434/v1",
        validation_alias=AliasChoices(
            "LLM_BASE_URL", "OPENAI_BASE_URL", "GEMINI_BASE_URL"
        ),
    )
    llm_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("LLM_API_KEY", "GEMINI_API_KEY"),
    )

    max_concurrent_articles: int = 5
    request_timeout_seconds: int = 30
    max_llm_article_chars: int = 24000
    llm_max_retries: int = 4
    llm_retry_base_delay_seconds: float = 1.0
    llm_fallback_models: str = ""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
