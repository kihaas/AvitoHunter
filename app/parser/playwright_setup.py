"""
parser/playwright_setup.py

Фикс: playwright.stop() вызывается явно после закрытия браузера.
Без этого при остановке бота вылетает:
  "Connection closed while reading from the driver"
"""

import subprocess
import sys
from pathlib import Path

from playwright.async_api import async_playwright, BrowserContext, Playwright
from app.core.logger import logger

STORAGE_STATE_PATH = Path("data/browser_state.json")

_STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver',  { get: () => undefined });
Object.defineProperty(navigator, 'platform',   { get: () => 'Win32' });
Object.defineProperty(navigator, 'vendor',     { get: () => 'Google Inc.' });
Object.defineProperty(navigator, 'plugins',    { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages',  { get: () => ['ru-RU', 'ru', 'en-US'] });
window.chrome = { runtime: {} };
"""


def ensure_playwright_installed() -> None:
    try:
        ms_dir = Path.home() / "AppData" / "Local" / "ms-playwright"
        if not ms_dir.exists():
            logger.info("Устанавливаю Playwright Chromium...")
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                check=True,
            )
    except Exception as e:
        logger.warning(f"Не смог проверить Playwright: {e}")


class BrowserSession:
    """
    Контекстный менеджер для браузера.
    Гарантирует вызов playwright.stop() даже при исключении.

    Использование:
        async with BrowserSession() as ctx:
            page = await ctx.new_page()
            ...
    """

    def __init__(self):
        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None

    async def __aenter__(self) -> BrowserContext:
        ensure_playwright_installed()

        self._playwright = await async_playwright().start()
        browser = await self._playwright.chromium.launch(
            headless=True,
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

        if STORAGE_STATE_PATH.exists():
            context_kwargs["storage_state"] = str(STORAGE_STATE_PATH)
            logger.debug("Загружены сохранённые cookies")

        self._context = await browser.new_context(**context_kwargs)
        await self._context.add_init_script(_STEALTH_SCRIPT)

        return self._context

    async def __aexit__(self, exc_type, exc, tb) -> None:
        # Сохраняем cookies перед закрытием
        if self._context:
            try:
                STORAGE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
                await self._context.storage_state(path=str(STORAGE_STATE_PATH))
                logger.debug("Cookies сохранены")
            except Exception as e:
                logger.debug(f"Не смог сохранить cookies: {e}")

            try:
                await self._context.close()
            except Exception:
                pass

        # Останавливаем playwright — это убирает "Connection closed" при завершении
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass