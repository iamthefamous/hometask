from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "News People Knowledge Graph API"
    app_env: str = "development"

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "news_people_kg"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()