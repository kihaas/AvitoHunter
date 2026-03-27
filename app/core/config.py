from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str
    admin_id: int

    gemini_api_key: str
    # gemini-3-flash-preview не существует — правильное название: gemini-2.0-flash
    ai_model: str = "gemini-2.0-flash"
    #ai_model: str = "gemini-3-flash-preview"

    max_price: int = 12000
    check_interval_minutes: int = 40

    avito_delay_min: float = 15.0
    avito_delay_max: float = 25.0

    log_level: str = "INFO"
    db_path: str = "data/hunter.db"

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


settings = Settings()