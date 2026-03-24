import json
import logging

import requests

from app.core.prompts import SYSTEM_PROMPT, build_user_message

logger = logging.getLogger("avito_hunter.ai")

_URL = "https://openrouter.ai/api/v1/chat/completions"


def analyze(listing: dict, api_key: str, model: str) -> dict | None:

    #Анализирует объявление. Возвращает dict с полями из промпта или None при ошибке.

    content = build_user_message(listing)

    try:
        resp = requests.post(
            _URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/avito-hunter-bot",
                "X-Title": "AvitoHunter",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": content},
                ],
                "temperature": 0.1,
                "max_tokens": 600,
            },
            timeout=45,
        )
        resp.raise_for_status()

        raw: str = resp.json()["choices"][0]["message"]["content"].strip()

        # Убираем markdown-обёртку если модель добавила
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw

        result = json.loads(raw)
        logger.info(
            f"  AI → brand={result.get('brand')} "
            f"fake={result.get('is_fake_risk')} "
            f"damage={result.get('damage')} "
            f"notify={result.get('notify')}"
        )
        return result

    except json.JSONDecodeError as e:
        logger.warning(f"AI вернул не-JSON: {e} | ответ: {raw[:300]}")
    except Exception as e:
        logger.warning(f"Ошибка AI: {e}")

    return None