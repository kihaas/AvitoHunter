
#Авито блокирует ботов -> случайный User-Agent + паузы между запросами.
#Если блокировки участятся — переходим на Playwright (отдельная ветка).


import base64
import logging
import random
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("avito_hunter.parser")

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
] #это что и почему мозила


def _headers() -> dict:
    return {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def _build_url(query: str, max_price: int | None = None) -> str:
    """Поиск по всей России, категория «Спорт и отдых»."""
    url = f"https://www.avito.ru/rossiya?q={quote(query)}&cid=9"
    if max_price:
        url += f"&pmax={max_price}"
    return url


def _fetch_html(url: str) -> str | None:
    try:
        r = requests.get(url, headers=_headers(), timeout=15)
        if r.status_code == 200:
            return r.text
        logger.warning(f"Авито → HTTP {r.status_code}")
        return None
    except requests.RequestException as e:
        logger.warning(f"Ошибка запроса Авито: {e}")
        return None


def _parse_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    items = soup.select("[data-marker='item']") or soup.select("article[class*='iva-item']")
    results = []

    for item in items:
        try:
            lid = item.get("data-item-id", "")
            if not lid:
                continue

            title_el = item.select_one("[data-marker='item-title']") or item.select_one("h3")
            title = title_el.get_text(strip=True) if title_el else ""

            price_el = item.select_one("[data-marker='item-price']")
            price_raw = price_el.get_text(strip=True) if price_el else ""
            price = int("".join(c for c in price_raw if c.isdigit()) or "0")

            link_el = item.select_one("a[data-marker='item-title']") or item.select_one("a[href]")
            href = link_el.get("href", "") if link_el else ""
            url = f"https://www.avito.ru{href}" if href.startswith("/") else href

            desc_el = item.select_one("[data-marker='item-description']")
            description = desc_el.get_text(strip=True)[:600] if desc_el else ""

            geo_el = item.select_one("[data-marker='item-address']")
            location = geo_el.get_text(strip=True) if geo_el else ""

            img_el = item.select_one("img[src]") or item.select_one("img[data-src]")
            img_url = ""
            if img_el:
                img_url = img_el.get("src") or img_el.get("data-src") or ""
                for small, big in [("140x105", "640x480"), ("208x156", "640x480"), ("80x60", "640x480")]:
                    img_url = img_url.replace(small, big)

            has_delivery = bool(item.select_one("[data-marker='item-delivery']"))

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


def _fetch_image_b64(img_url: str) -> str | None:
    if not img_url:
        return None
    try:
        r = requests.get(img_url, headers=_headers(), timeout=10)
        if r.status_code == 200:
            return base64.b64encode(r.content).decode()
    except Exception:
        pass
    return None


def get_listings(query: str, max_price: int | None = None) -> list[dict]:
    """Полный цикл: поиск -> парсинг -> скачивание фото."""
    url = _build_url(query, max_price)
    logger.info(f"Поиск: '{query}'")

    html = _fetch_html(url)
    if not html:
        return []

    listings = _parse_html(html)
    logger.info(f"  Найдено: {len(listings)}")

    for listing in listings:
        if listing["img_url"]:
            listing["img_b64"] = _fetch_image_b64(listing["img_url"])

    return listings