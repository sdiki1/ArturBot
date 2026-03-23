from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = Field(alias="BOT_TOKEN")
    bot_username: str = Field(alias="BOT_USERNAME")

    default_mentor_name: str = Field(default="Евгений Rembo", alias="DEFAULT_MENTOR_NAME")
    default_mentor_username: str = Field(default="charkrembo", alias="DEFAULT_MENTOR_USERNAME")

    postgres_db: str = Field(default="bot_db", alias="POSTGRES_DB")
    postgres_user: str = Field(default="bot_user", alias="POSTGRES_USER")
    postgres_password: str = Field(default="bot_pass", alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(default="db", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")

    redis_host: str = Field(default="redis", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")

    web_base_url: str = Field(default="http://localhost:8000", alias="WEB_BASE_URL")

    yoomoney_receiver: str = Field(default="", alias="YOOMONEY_RECEIVER")
    yoomoney_label_secret: str = Field(default="", alias="YOOMONEY_LABEL_SECRET")
    yoomoney_success_url: str = Field(default="", alias="YOOMONEY_SUCCESS_URL")
    yoomoney_fail_url: str = Field(default="", alias="YOOMONEY_FAIL_URL")

    subscription_price_rub: int = Field(default=199, alias="SUBSCRIPTION_PRICE_RUB")
    subscription_days: int = Field(default=30, alias="SUBSCRIPTION_DAYS")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
