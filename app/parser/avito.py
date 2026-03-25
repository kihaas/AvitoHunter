"""
parser/avito.py

Главные фиксы по сравнению с предыдущей версией:
  1. wait_for_selector с таймаутом 30с вместо 15с
  2. Несколько fallback-селекторов для items (Авито меняет классы)
  3. Проверка на капчу/блок перед парсингом
  4. Более мягкое ожидание страницы (domcontentloaded + случайная пауза)
  5. Каждый запрос — отдельный контекст браузера (не накапливаем память)
"""

import asyncio
import base64
import logging
import random
from urllib.parse import quote

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from app.parser.playwright_setup import get_browser_context, save_storage_state

logger = logging.getLogger("avito_hunter.parser")

# Авито часто меняет дата-атрибуты — проверяем несколько
_ITEM_SELECTORS = [
    "[data-marker='item']",
    "div[class*='iva-item']",
    "article[class*='item']",
]

# Признаки капчи/блока
_BLOCK_SIGNS = ["captcha", "blocked", "ошибка", "robot", "проблема с ip"]


def _build_url(query: str, max_price: int | None = None) -> str:
    url = f"https://www.avito.ru/rossiya?q={quote(query)}&cid=9"
    if max_price:
        url += f"&pmax={max_price}"
    return url


async def _check_for_block(page: Page) -> bool:
    """Проверяет, не заблокировал ли нас Авито."""
    title = (await page.title()).lower()
    url   = page.url.lower()
    return any(sign in title or sign in url for sign in _BLOCK_SIGNS)


async def _wait_for_items(page: Page) -> str | None:
    """
    Пробует несколько селекторов. Возвращает рабочий или None.
    Таймаут 30с — Авито иногда долго грузит JS.
    """
    for selector in _ITEM_SELECTORS:
        try:
            await page.wait_for_selector(selector, timeout=30_000)
            return selector
        except PlaywrightTimeout:
            continue
    return None


async def _parse_items(page: Page, selector: str) -> list[dict]:
    items = await page.query_selector_all(selector)
    results = []

    for item in items:
        try:
            lid = await item.get_attribute("data-item-id")
            if not lid:
                continue

            title_el = await item.query_selector("[data-marker='item-title']")
            title = (await title_el.inner_text()).strip() if title_el else ""

            price_el = await item.query_selector("[data-marker='item-price']")
            price_raw = (await price_el.inner_text()).strip() if price_el else "0"
            price = int("".join(c for c in price_raw if c.isdigit()) or "0")

            link_el = await item.query_selector("a[data-marker='item-title']")
            href = await link_el.get_attribute("href") if link_el else ""
            url = f"https://www.avito.ru{href}" if href and href.startswith("/") else ""

            desc_el = await item.query_selector("[data-marker='item-description']")
            description = ((await desc_el.inner_text()).strip())[:600] if desc_el else ""

            geo_el = await item.query_selector("[data-marker='item-address']")
            location = (await geo_el.inner_text()).strip() if geo_el else ""

            img_el = await item.query_selector("img")
            img_url = ""
            if img_el:
                img_url = await img_el.get_attribute("src") or await img_el.get_attribute("data-src") or ""
                for small, big in [("140x105", "640x480"), ("208x156", "640x480"), ("80x60", "640x480")]:
                    img_url = img_url.replace(small, big)

            has_delivery = bool(await item.query_selector("[data-marker='item-delivery']"))

            results.append({
                "id": str(lid),
                "title": title,
                "price": price,
                "url": url,
                "description": description,
                "location": location,
                "img_url": img_url,
                "img_b64": None,
                "has_delivery": has_delivery,
            })
        except Exception as e:
            logger.debug(f"Пропуск элемента: {e}")

    return results


async def _fetch_image_b64(page: Page, img_url: str) -> str | None:
    if not img_url:
        return None
    try:
        response = await page.request.get(img_url, timeout=10_000)
        if response.ok:
            return base64.b64encode(await response.body()).decode()
    except Exception:
        pass
    return None


async def get_listings(query: str, max_price: int | None = None) -> list[dict]:
    """Парсит одну страницу результатов Авито для заданного запроса."""
    logger.info(f"Поиск: '{query}'")
    url = _build_url(query, max_price)

    context = await get_browser_context(headless=True)
    page = await context.new_page()

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)

        # Человеческая пауза — ждём подгрузки JS
        await asyncio.sleep(random.uniform(2.5, 5.0))

        if await _check_for_block(page):
            logger.warning(f"Авито показал страницу блокировки для '{query}'")
            return []

        working_selector = await _wait_for_items(page)
        if not working_selector:
            logger.warning(
                f"Не нашёл объявления для '{query}' — возможно, Авито изменил разметку "
                f"или показал пустую страницу. URL: {page.url}"
            )
            return []

        listings = await _parse_items(page, working_selector)
        logger.info(f"  Найдено: {len(listings)}")

        for listing in listings:
            if listing["img_url"]:
                listing["img_b64"] = await _fetch_image_b64(page, listing["img_url"])
                await asyncio.sleep(0.3)

        await save_storage_state(context)
        return listings

    except Exception as e:
        logger.error(f"Ошибка при парсинге '{query}': {e}")
        return []

    finally:
        await page.close()
        await context.close()