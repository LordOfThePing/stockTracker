from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    database_url: str = "sqlite:///./data/tracker.db"
    sync_interval_seconds: int = 900
    sync_jitter_seconds: int = 120

    binance_api_key: str = ""
    binance_api_secret: str = ""

    enable_mock: bool = False

    @property
    def binance_enabled(self) -> bool:
        return bool(self.binance_api_key and self.binance_api_secret)


@lru_cache
def get_settings() -> Settings:
    return Settings()
