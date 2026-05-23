from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "news-kg-api"
    env: str = "development"

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "news_kg"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    llm_provider: str = "mock"
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = ""

    max_concurrent_articles: int = 5
    request_timeout_seconds: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
