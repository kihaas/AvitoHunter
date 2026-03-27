import asyncio
import json
import time
from dotenv import load_dotenv

load_dotenv()

# Импортируем новую версию анализатора
from app.ai.analyzer import analyze   # ← важно!

# Тестовое объявление
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
    "img_b64": None,   # будет загружено внутри анализатора
}

async def test_with_retry(max_attempts: int = 3):
    print("🚀 Запуск теста анализатора OpenRouter (Nemotron Nano 12B VL)...\n")

    for attempt in range(1, max_attempts + 1):
        print(f"Попытка {attempt}/{max_attempts}...")

        start_time = time.time()
        result = await analyze(test_listing)          # ← теперь async, без to_thread
        elapsed = time.time() - start_time

        if result:
            print(f"\n✅ Успешно! (время: {elapsed:.1f} сек)\n")
            print("Результат:")
            print(json.dumps(result, ensure_ascii=False, indent=2))

            # Дополнительно выводим ключевые поля
            print("\nКлючевые выводы:")
            print(f"   Бренд:          {result.get('brand')}")
            print(f"   Модель:         {result.get('model')}")
            print(f"   Релевантно:     {result.get('is_relevant')}")
            print(f"   Риск подделки:  {result.get('is_fake_risk')} ({result.get('fake_confidence')})")
            print(f"   Повреждения:    {result.get('damage')}")
            print(f"   Уведомлять:     {result.get('notify')}")
            print(f"   Ценовой вердикт:{result.get('price_verdict')}")
            return

        else:
            print(f"❌ AI вернул None (попытка {attempt})")
            if attempt < max_attempts:
                wait = 20 * attempt
                print(f"⏳ Ждём {wait} секунд перед повтором...\n")
                await asyncio.sleep(wait)

    print("\n❌ Не удалось получить валидный ответ после всех попыток.")


if __name__ == "__main__":
    asyncio.run(test_with_retry())