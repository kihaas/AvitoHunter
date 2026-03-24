# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    bot_token: str
    admin_id: int

    # AI — теперь Gemini
    gemini_api_key: str
    ai_model: str = "gemini-2.5-flash"

    # Поиск
    max_price: int = 12000
    check_interval_minutes: int = 30

    # Парсер
    avito_delay_min: float = 3.0
    avito_delay_max: float = 7.0

    # Система
    log_level: str = "INFO"
    db_path: str = "data/hunter.db"

    # Поисковые запросы
    search_queries: list[str] = [
        "ракетка nox padel",
        "ракетка nox падел",
        "nox padel",
        "ракетка adidas padel",
        "adidas padel",
        "ракетка для падел",
        "padel ракетка",
        "падел ракетка",
    ]


# Создаём экземпляр
settings = Settings()