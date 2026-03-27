import asyncio
import json
import time
from dotenv import load_dotenv

load_dotenv()

from app.ai.analyzer import analyze

# Тестовое объявление (то самое, которое ты показал)
test_listing = {
    "id": "7953963032",
    "title": "Ракетка для падел тенниса",
    "price": 7500,
    "url": "https://www.avito.ru/peresvet/sport_i_otdyh/raketka_dlya_padel_tennisa_7953963032",
    "description": "Новая ракетка для падел тенниса",
    "params": "Подвид товара: Падел и сквош, Состояние: Новое",
    "location": "Пересвет",
    "has_delivery": False,
    "img_url": "https://40.img.avito.st/image/1/1.qrLdL7a4BlvrhsRehRn4z--PBF1jjoRTq4sEWW2GDlFr.IEGvMwtcMfh8Ly0bj067y2wkqGMUitbGcHtLBYq1XWQ",
    "img_b64": None,
}

async def test_with_retry(max_attempts=3):
    print("🚀 Тест анализатора с повторными попытками...\n")

    for attempt in range(1, max_attempts + 1):
        print(f"Попытка {attempt}/{max_attempts}...")

        result = await asyncio.to_thread(analyze, test_listing)

        if result:
            print("\n✅ Успешно! Результат от Gemini:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return
        else:
            print("❌ AI вернул None")
            if attempt < max_attempts:
                wait = 25 * attempt
                print(f"⏳ Ждём {wait} секунд перед следующей попыткой...\n")
                await asyncio.sleep(wait)

    print("\n❌ Не удалось получить ответ от Gemini после всех попыток.")

if __name__ == "__main__":
    asyncio.run(test_with_retry())