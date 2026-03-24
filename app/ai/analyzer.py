# app/ai/analyzer.py
import json
import logging
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreso

from app.core.prompts import SYSTEM_PROMPT, build_user_message
from app.core.config import settings

logger = logging.getLogger("avito_hunter.ai")

# Настройка один раз при импорте
genai.configure(api_key=settings.gemini_api_key)

def analyze(listing: dict) -> dict | None:
    """Анализирует объявление через Gemini и возвращает dict или None."""
    try:
        model = genai.GenerativeModel(
            model_name=settings.ai_model,
            system_instruction=SYSTEM_PROMPT,
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )

        contents = build_user_message(listing)   # твоя функция, которая возвращает list с text + image_url (base64)

        response = model.generate_content(
            contents,
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 800,
                "response_mime_type": "application/json",   # просим JSON
            }
        )

        raw = response.text.strip()

        # Убираем возможную обёртку ```json
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()

        result = json.loads(raw)

        logger.info(
            f"Gemini → brand={result.get('brand')} fake={result.get('is_fake_risk')} "
            f"damage={result.get('damage')} notify={result.get('notify')}"
        )
        return result

    except json.JSONDecodeError as e:
        logger.warning(f"Gemini вернул невалидный JSON: {e} | ответ: {raw[:400]}")
    except Exception as e:
        logger.error(f"Ошибка Gemini: {e}")
        if "429" in str(e) or "quota" in str(e).lower():
            logger.warning("Достигнут лимит Gemini — подожди немного")

    return None