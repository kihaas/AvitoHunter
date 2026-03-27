"""
app/ai/analyzer.py

Использует google-genai SDK (новый, не google-generativeai).
response_mime_type="application/json" — Gemini гарантированно вернёт JSON.
"""

import json
import logging

from google import genai
from google.genai import types

from app.core.config import settings
from app.core.prompts import SYSTEM_PROMPT, build_user_message

logger = logging.getLogger("avito_hunter.ai")

# Клиент создаётся один раз при импорте модуля
_client = genai.Client(api_key=settings.gemini_api_key)

_GENERATION_CONFIG = types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT,
    temperature=0.1,
    max_output_tokens=800,
    response_mime_type="application/json",
    safety_settings=[
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
    ],
)


def analyze(listing: dict) -> dict | None:
    """
    Синхронный вызов Gemini (блокирующий).
    Вызывается из scheduler через asyncio.to_thread() чтобы не блокировать event loop.
    """
    parts = build_user_message(listing)

    try:
        response = _client.models.generate_content(
            model=settings.ai_model,
            contents=parts,
            config=_GENERATION_CONFIG,
        )

        raw = response.text.strip()

        # На случай если модель всё же добавила ```json
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()

        result: dict = json.loads(raw)

        logger.info(
            f"  AI → brand={result.get('brand')} | "
            f"fake={result.get('is_fake_risk')} | "
            f"damage={result.get('damage')} | "
            f"notify={result.get('notify')}"
        )
        return result

    except json.JSONDecodeError as e:
        raw_preview = locals().get("raw", "")[:400]
        logger.warning(f"Gemini вернул не-JSON: {e}\nОтвет: {raw_preview}")
    except Exception as e:
        msg = str(e)
        if "429" in msg or "quota" in msg.lower():
            logger.warning("Превышен лимит запросов Gemini — подожди 1–2 минуты.")
        else:
            logger.error(f"Ошибка Gemini: {type(e).__name__}: {e}")

    return None