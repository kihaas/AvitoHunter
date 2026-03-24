# app/parser/avito.py
import asyncio
import base64
import logging
import random
from urllib.parse import quote

from playwright.async_api import Page

from app.core.config import settings
from app.parser.playwright_setup import get_browser_context, save_storage_state

logger = logging.getLogger("avito_hunter.parser")


async def _build_url(query: str, max_price: int | None = None) -> str:
    url = f"https://www.avito.ru/rossiya?q={quote(query)}&cid=9"
    if max_price:
        url += f"&pmax={max_price}"
    return url


async def _parse_page(page: Page) -> list[dict]:
    await page.wait_for_selector("[data-marker='item']", timeout=15000)

    items = await page.query_selector_all("[data-marker='item']")

    results = []
    for item in items:
        try:
            lid = await item.get_attribute("data-item-id")
            if not lid:
                continue

            title_el = await item.query_selector("[data-marker='item-title']")
            title = await title_el.inner_text() if title_el else ""

            price_el = await item.query_selector("[data-marker='item-price']")
            price_raw = await price_el.inner_text() if price_el else "0"
            price = int("".join(c for c in price_raw if c.isdigit()) or "0")

            link_el = await item.query_selector("a[data-marker='item-title']")
            href = await link_el.get_attribute("href") if link_el else ""
            url = f"https://www.avito.ru{href}" if href and href.startswith("/") else href

            desc_el = await item.query_selector("[data-marker='item-description']")
            description = (await desc_el.inner_text() if desc_el else "")[:600]

            location_el = await item.query_selector("[data-marker='item-address']")
            location = await location_el.inner_text() if location_el else ""

            img_el = await item.query_selector("img")
            img_url = await img_el.get_attribute("src") if img_el else ""
            if img_url and "140x105" in img_url:
                img_url = img_url.replace("140x105", "640x480")

            has_delivery = bool(await item.query_selector("[data-marker='item-delivery']"))

            results.append({
                "id": str(lid),
                "title": title.strip(),
                "price": price,
                "url": url,
                "description": description.strip(),
                "location": location.strip(),
                "img_url": img_url,
                "img_b64": None,
                "has_delivery": has_delivery,
            })
        except Exception as e:
            logger.debug(f"Ошибка парсинга элемента: {e}")

    return results


async def _fetch_image_b64(page: Page, img_url: str) -> str | None:
    if not img_url:
        return None
    try:
        response = await page.request.get(img_url)
        if response.ok:
            content = await response.body()
            return base64.b64encode(content).decode()
    except Exception:
        pass
    return None


async def get_listings(query: str, max_price: int | None = None) -> list[dict]:
    logger.info(f"Поиск на Авито: '{query}'")

    context = await get_browser_context(headless=True)
    page = await context.new_page()

    try:
        url = await _build_url(query, max_price)
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        await asyncio.sleep(random.uniform(2, 4))  # человеческая пауза

        listings = await _parse_page(page)

        logger.info(f"  Найдено объявлений: {len(listings)}")

        # Скачиваем фото
        for listing in listings:
            if listing["img_url"]:
                listing["img_b64"] = await _fetch_image_b64(page, listing["img_url"])
                await asyncio.sleep(0.5)

        await save_storage_state(context)  # сохраняем cookies
        return listings

    except Exception as e:
        logger.error(f"Ошибка при парсинге '{query}': {e}")
        return []
    finally:
        await context.close()