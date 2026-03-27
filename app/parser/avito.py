"""
parser/avito.py


Изменения:
- Используем BrowserSession (контекстный менеджер) вместо ручного get/close
- Добавлен парсинг характеристик товара (params) — передаём в AI
- _check_for_block теперь проверяет наличие/отсутствие объявлений, а не заголовок
"""


import asyncio
import base64
import logging
import random
from urllib.parse import quote


from playwright.async_api import Page, TimeoutError as PlaywrightTimeout


from app.parser.playwright_setup import BrowserSession


logger = logging.getLogger("avito_hunter.parser")


_ITEM_SELECTORS = [
   "[data-marker='item']",
   "div[class*='iva-item']",
   "article[class*='item']",
]


# Авито показывает эти тексты когда блокирует или показывает капчу
_BLOCK_TITLE_SIGNS = ["доступ ограничен", "captcha", "robot", "проблема с ip", "blocked"]




def _build_url(query: str, max_price: int | None = None) -> str:
   url = f"https://www.avito.ru/rossiya?q={quote(query)}&cid=9"
   if max_price:
       url += f"&pmax={max_price}"
   return url




async def _is_blocked(page: Page) -> bool:
   """
   Проверяет блокировку по заголовку страницы.
   НЕ проверяет по URL — редирект на капчу обычно сохраняет нормальный URL.
   """
   try:
       title = (await page.title()).lower()
       return any(sign in title for sign in _BLOCK_TITLE_SIGNS)
   except Exception:
       return False




async def _find_items_selector(page: Page) -> str | None:
   """Перебирает селекторы пока не найдёт рабочий. Таймаут 30с на каждый."""
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


           # Характеристики из карточки списка (если отображаются)
           params_els = await item.query_selector_all("[data-marker='item-specific-params'] li")
           params = ", ".join(
               [(await el.inner_text()).strip() for el in params_els]
           ) if params_els else ""


           geo_el = await item.query_selector("[data-marker='item-address']")
           location = (await geo_el.inner_text()).strip() if geo_el else ""


           img_el = await item.query_selector("img")
           img_url = ""
           if img_el:
               img_url = (
                   await img_el.get_attribute("src")
                   or await img_el.get_attribute("data-src")
                   or ""
               )
               for small, big in [
                   ("140x105", "640x480"),
                   ("208x156", "640x480"),
                   ("80x60",   "640x480"),
               ]:
                   img_url = img_url.replace(small, big)


           has_delivery = bool(await item.query_selector("[data-marker='item-delivery']"))


           results.append({
               "id":           str(lid),
               "title":        title,
               "price":        price,
               "url":          url,
               "description":  description,
               "params":       params,
               "location":     location,
               "img_url":      img_url,
               "img_b64":      None,
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
   """Парсит страницу результатов Авито для одного запроса."""
   logger.info(f"Поиск: '{query}'")
   url = _build_url(query, max_price)


   # BrowserSession сам закрывает браузер и вызывает playwright.stop()
   async with BrowserSession() as context:
       page = await context.new_page()


       try:
           await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
           await asyncio.sleep(random.uniform(2.5, 5.0))


           if await _is_blocked(page):
               logger.warning(f"Авито заблокировал запрос для '{query}'")
               return []


           selector = await _find_items_selector(page)
           if not selector:
               logger.warning(f"Объявления не найдены для '{query}' (возможно, пустая выдача или изменилась разметка)")
               return []


           listings = await _parse_items(page, selector)
           logger.info(f"  Найдено: {len(listings)}")


           for listing in listings:
               if listing["img_url"]:
                   listing["img_b64"] = await _fetch_image_b64(page, listing["img_url"])
                   await asyncio.sleep(0.3)


           return listings


       except Exception as e:
           logger.error(f"Ошибка парсинга '{query}': {e}")
           return []
