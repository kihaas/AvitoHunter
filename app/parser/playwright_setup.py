"""
parser/playwright_setup.py

Запускает Chromium через Playwright с анти-детект настройками.
Cookies сохраняются в data/browser_state.json — при следующем запуске
Авито не будет видеть нас как нового пользователя.
"""

import subprocess
import sys
import os
from pathlib import Path

from playwright.async_api import async_playwright, BrowserContext
from app.core.logger import logger

STORAGE_STATE_PATH = Path("data/browser_state.json")

# Скрипт обхода детекции автоматизации
_STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver',  { get: () => undefined });
Object.defineProperty(navigator, 'platform',   { get: () => 'Win32' });
Object.defineProperty(navigator, 'vendor',     { get: () => 'Google Inc.' });
Object.defineProperty(navigator, 'plugins',    { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages',  { get: () => ['ru-RU', 'ru', 'en-US'] });
window.chrome = { runtime: {} };
"""


def ensure_playwright_installed() -> None:
    """Устанавливает браузер Playwright если его нет."""
    try:
        ms_dir = Path.home() / "AppData" / "Local" / "ms-playwright"
        if not ms_dir.exists():
            logger.info("Устанавливаю Playwright Chromium...")
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                check=True,
            )
        else:
            logger.debug("Playwright Chromium уже установлен")
    except Exception as e:
        logger.warning(f"Не смог проверить Playwright: {e}")


async def get_browser_context(headless: bool = True) -> BrowserContext:
    """
    Создаёт браузерный контекст с сохранёнными cookies.
    Каждый вызов get_listings() создаёт свой контекст и закрывает его после.
    """
    ensure_playwright_installed()

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=headless,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--window-size=1920,1080",
        ],
    )

    context_kwargs = dict(
        viewport={"width": 1920, "height": 1080},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/134.0.0.0 Safari/537.36"
        ),
        locale="ru-RU",
        timezone_id="Europe/Moscow",
    )

    # Загружаем сохранённые cookies если есть
    if STORAGE_STATE_PATH.exists():
        context_kwargs["storage_state"] = str(STORAGE_STATE_PATH)
        logger.debug("Загружены сохранённые cookies")

    context = await browser.new_context(**context_kwargs)
    await context.add_init_script(_STEALTH_SCRIPT)

    return context


async def save_storage_state(context: BrowserContext) -> None:
    """Сохраняет cookies после успешного парсинга."""
    try:
        STORAGE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=str(STORAGE_STATE_PATH))
        logger.debug("Cookies сохранены")
    except Exception as e:
        logger.warning(f"Не смог сохранить cookies: {e}")