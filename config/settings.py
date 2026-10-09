from functools import lru_cache
from typing import Literal
from urllib.parse import quote_plus

from pydantic import BaseModel, Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Database(BaseModel):
    host: str = Field(default="localhost", min_length=1)
    port: int = Field(default=5432, ge=1, le=65535)
    user: str = Field(default="postgres", min_length=1)
    password: SecretStr
    name: str = Field(default="transfers", min_length=1)

    @property
    def url(self) -> str:
        password = quote_plus(self.password.get_secret_value())
        return (
            f"postgresql+asyncpg://{self.user}:{password}"
            f"@{self.host}:{self.port}/{self.name}"
        )


class Webhook(BaseModel):
    url: HttpUrl
    api_key: SecretStr
    timeout_sec: float = Field(default=10, gt=0)
    max_retries: int = Field(default=5, ge=0)
    signature_header: str = "X-Signature"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__",
    )

    environment: Literal["dev", "test", "prod"] = "dev"
    debug: bool = True

    database: Database
    webhook: Webhook

    api_token: SecretStr
    from_address: str = Field(min_length=1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
