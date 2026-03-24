# app/parser/playwright_setup.py
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright, Browser, BrowserContext

from app.core.config import settings

# Путь для хранения состояния браузера (cookies, localStorage)
STORAGE_STATE_PATH = Path("data/browser_state.json")


async def get_browser_context(headless: bool = True) -> BrowserContext:
    playwright = await async_playwright().start()
    browser: Browser = await playwright.chromium.launch(
        headless=headless,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled",
        ],
    )

    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        locale="ru-RU",
    )

    # Обходим обнаружение автоматизации
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    """)

    # Загружаем cookies, если есть
    if STORAGE_STATE_PATH.exists():
        await context.storage_state(path=str(STORAGE_STATE_PATH))

    return context


async def save_storage_state(context: BrowserContext):
    await context.storage_state(path=str(STORAGE_STATE_PATH))