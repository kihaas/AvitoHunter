import json
import logging
import base64
from typing import Any

import httpx

from app.core.config import settings
from app.core.prompts import SYSTEM_PROMPT

logger = logging.getLogger("avito_hunter.ai")

_client = httpx.AsyncClient(timeout=70.0)


async def analyze(listing: dict) -> dict | None:
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "HTTP-Referer": "https://github.com/AvitoHunter",
        "X-Title": "AvitoHunter",
        "Content-Type": "application/json",
    }

    user_content: list[dict[str, Any]] = [
        {"type": "text", "text": _build_user_text(listing)}
    ]

    if listing.get("img_b64"):
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{listing['img_b64']}"}
        })

    payload = {
        "model": settings.ai_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.2,
        "max_tokens": 1000,
    }

    try:
        response = await _client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        message = data["choices"][0]["message"]
        raw = message.get("content")

        if not raw or not isinstance(raw, str):
            logger.warning("Модель вернула пустой или не строковый content")
            # Попробуем reasoning, если есть
            if "reasoning" in message:
                logger.info("Найден reasoning контент")
                raw = message.get("reasoning")
            if not raw or not isinstance(raw, str):
                return None

        raw = raw.strip()

        if raw.startswith("```"):
            raw = raw.split("```", 2)[1].lstrip("json").strip()

        try:
            result: dict = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"Не чистый JSON. Пробуем извлечь:\n{raw[:600]}")
            import re
            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(0))
                except:
                    return None
            else:
                return None

        logger.info(
            f"AI → brand={result.get('brand')} | "
            f"fake={result.get('is_fake_risk')} | "
            f"damage={result.get('damage')} | "
            f"notify={result.get('notify')}"
        )
        return result

    except httpx.HTTPStatusError as e:
        logger.error(f"OpenRouter HTTP {e.response.status_code}: {e.response.text[:400]}")
    except Exception as e:
        logger.error(f"Ошибка при запросе к OpenRouter: {type(e).__name__}: {e}")

    return None


def _build_user_text(listing: dict) -> str:
    price = listing.get("price", 0)
    price_str = f"{price:,} ₽".replace(",", "\u00a0") if price else "не указана"

    return (
        f"Объявление с Авито:\n\n"
        f"Заголовок: {listing.get('title', '—')}\n"
        f"Цена: {price_str}\n"
        f"Описание: {listing.get('description') or '(не указано)'}\n"
        f"Характеристики: {listing.get('params') or '(не указаны)'}\n"
        f"Авито.Доставка: {'да' if listing.get('has_delivery') else 'нет/неизвестно'}\n"
        f"Город: {listing.get('location') or 'не указан'}\n"
        f"Ссылка: {listing.get('url', '—')}\n\n"
        f"Проанализируй фото и текст. Ответь строго JSON по инструкции."
    )