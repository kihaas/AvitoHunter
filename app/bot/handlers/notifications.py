import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.bot.keyboards.inline import listing_keyboard

logger = logging.getLogger("avito_hunter.bot")


def _format(listing: dict, ai: dict) -> str:
    brand = ai.get("brand", "?")
    model = ai.get("model") or "модель неизвестна"
    price = listing.get("price", 0)
    price_str = f"{price:,} ₽".replace(",", "\u202f") if price else "цена не указана"

    fake = ai.get("is_fake_risk")
    conf = ai.get("fake_confidence", "")
    conf_suffix = f" ({conf})" if conf and conf not in ("неизвестно", "") else ""

    if fake is True:
        fake_str = f"⚠️ риск подделки{conf_suffix}"
    elif fake is False:
        fake_str = f"✅ похоже на оригинал{conf_suffix}"
    else:
        fake_str = "❓ не определить по фото"

    damage_map = {
        "нет":        "✅ нет",
        "мелкие":     "🟡 мелкие",
        "серьёзные":  "🔴 серьёзные",
        "неизвестно": "❓ неизвестно",
    }
    damage_str   = damage_map.get(ai.get("damage", "неизвестно"), "❓")
    delivery_str = "✅ Авито.Доставка" if listing.get("has_delivery") else "❓ уточнить"

    price_map = {
        "отлично":               "🟢 отличная",
        "нормально":             "🟡 нормальная",
        "дорого":                "🔴 дороговато",
        "подозрительно дёшево":  "⚠️ подозрительно дёшево",
    }
    price_label = price_map.get(ai.get("price_verdict", ""), "")
    reason      = ai.get("reason", "")
    location    = listing.get("location", "")

    lines = [
        f"🏓 <b>{brand}</b> — {model}",
        f"💰 <b>{price_str}</b>" + (f"  {price_label}" if price_label else ""),
        "",
        f"Подлинность: {fake_str}",
        f"Состояние:   {damage_str}",
        f"Доставка:    {delivery_str}",
    ]
    if location:
        lines.append(f"📍 {location}")
    if reason:
        lines += ["", f"<i>{reason}</i>"]

    return "\n".join(lines)


async def send_listing(bot: Bot, chat_id: int, listing: dict, ai: dict) -> bool:

    text = _format(listing, ai)
    kb   = listing_keyboard(listing["url"])

    if listing.get("img_url"):
        try:
            await bot.send_photo(
                chat_id=chat_id,
                photo=listing["img_url"],
                caption=text,
                reply_markup=kb,
                parse_mode="HTML",
            )
            return True
        except TelegramAPIError as e:
            logger.debug(f"Фото не прошло ({e}), шлю текстом")

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=kb,
            parse_mode="HTML",
            disable_web_page_preview=False,
        )
        return True
    except TelegramAPIError as e:
        logger.error(f"Ошибка отправки: {e}")
        return False


async def send_text(bot: Bot, chat_id: int, text: str) -> None:
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
    except TelegramAPIError as e:
        logger.error(f"Служебное сообщение не отправилось: {e}")