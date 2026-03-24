from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="data/.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    bot_token: str
    admin_id: int

    # AI
    openrouter_api_key: str
    ai_model: str = "qwen/qwen2.5-vl-72b-instruct:free"

    # Поиск
    max_price: int = 12000
    check_interval_minutes: int = 30

    # Система
    log_level: str = "INFO"
    db_path: str = "data/hunter.db"

    # Поисковые запросы (фиксированный список, менять здесь)
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

    # Задержки между запросами к Авито (сек)
    avito_delay_min: float = 3.0
    avito_delay_max: float = 7.0


settings = Settings()