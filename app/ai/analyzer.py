# app/ai/analyzer.py
import json
import logging

from google import genai
from google.genai.types import HttpOptions, Part  # для удобства, если понадобится

from app.core.config import settings
from app.core.prompts import SYSTEM_PROMPT, build_user_message

logger = logging.getLogger("avito_hunter.ai")


# Создаём клиент один раз
client = genai.Client(api_key=settings.gemini_api_key)


def analyze(listing: dict) -> dict | None:
    """
    Анализирует объявление с помощью нового Google GenAI SDK.
    """
    try:
        model = client.models.get_model(model=settings.ai_model)  # или просто используем строку ниже

        contents = build_user_message(listing)

        response = client.models.generate_content(
            model=settings.ai_model,
            contents=contents,
            config={
                "system_instruction": SYSTEM_PROMPT,
                "temperature": 0.1,
                "max_output_tokens": 800,
                "response_mime_type": "application/json",
                # Отключаем цензуру
                "safety_settings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ],
            },
        )

        raw_text = response.text.strip()

        # Убираем возможную ```json обёртку
        if raw_text.startswith("```"):
            parts = raw_text.split("```", 2)
            raw_text = parts[1].lstrip("json").strip() if len(parts) > 1 else raw_text

        result: dict = json.loads(raw_text)

        logger.info(
            f"✅ Gemini → brand={result.get('brand')} | "
            f"fake={result.get('is_fake_risk')} | "
            f"damage={result.get('damage')} | "
            f"notify={result.get('notify')}"
        )
        return result

    except json.JSONDecodeError as e:
        logger.warning(f"Gemini вернул невалидный JSON: {e}\nОтвет: {raw_text[:600] if 'raw_text' in locals() else '—'}")
    except Exception as e:
        logger.error(f"❌ Ошибка Gemini: {type(e).__name__}: {e}")
        if "429" in str(e) or "quota" in str(e).lower():
            logger.warning("⚠️ Превышен лимит запросов Gemini. Подожди 1–2 минуты.")

    return None