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

    gemini_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("GEMINI_API_KEY"),
    )
    gemini_model: str = Field(
        default="gemini-3.1-flash-lite",
        validation_alias=AliasChoices("GEMINI_MODEL"),
    )

    max_concurrent_articles: int = Field(
        default=5,
        validation_alias=AliasChoices(
            "MAX_CONCURRENT_ARTICLES", "MAX_CONCURRENT_AGENTS"
        ),
    )
    request_timeout_seconds: int = 30
    max_llm_article_chars: int = 24000

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
