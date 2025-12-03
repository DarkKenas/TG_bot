from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения с валидацией."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # === Telegram ===
    bot_token: str = Field(alias="TOKEN")

    # === Database ===
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_user: str = Field(alias="DB_USER")
    db_password: str = Field(alias="DB_PASSWORD")
    db_name: str = Field(alias="DB_NAME")

    @computed_field
    @property
    def pg_link(self) -> str:
        """Формирует строку подключения из отдельных параметров."""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    # === Service User ===
    default_service_user_id: int = Field(alias="DEFAULT_SERVICE_USER_ID")

    # === Secret Codes ===
    admin_secret_code: str = Field(alias="ADMIN_SECRET_CODE")
    service_secret_code: str = Field(alias="SERVICE_SECRET_CODE")

    # === Scheduler ===
    timezone: str = Field(default="Europe/Moscow")


@lru_cache
def get_settings() -> Settings:
    """
    Получить настройки (кэшируется).
    
    При первом вызове загружает и валидирует все переменные.
    Если что-то не так — приложение не запустится.
    """
    return Settings()
