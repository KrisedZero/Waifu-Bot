from aiogram import Router, F
from aiogram.types import CallbackQuery

from app.services.user_service import get_user_language
from app.services.waifu_service import get_waifu_details, get_waifu_media
from app.services.category_service import get_category_path
from app.services.waifu_ui import build_card_text, build_close_keyboard
from app.services.waifu_media import send_waifu_media

router = Router()


@router.callback_query(F.data.startswith("wc:open:"))
async def open_waifu_card(call: CallbackQuery):
    if not call.from_user or not call.message:
        return

    await call.answer()

    parts = call.data.split(":")
    if len(parts) < 4:
        return

    _, _, source, waifu_id_str = parts[:4]
    waifu_id = int(waifu_id_str)

    user_id = call.from_user.id
    user_lang = await get_user_language(user_id)

    waifu = await get_waifu_details(waifu_id)
    if not waifu:
        text = "❌ Waifu not found" if user_lang == "en" else "❌ Вайфу не найдена"
        await call.message.answer(text)
        return

    category_rows = await get_category_path(waifu["category_id"])
    media = await get_waifu_media(waifu_id)

    text = build_card_text(waifu, user_lang, category_rows)
    markup = build_close_keyboard(user_lang)

    if waifu.get("is_active", True) and media and len(text) <= 900:
        sent = await send_waifu_media(call.message, media, text, reply_markup=markup)
        if sent:
            return

    await call.message.answer(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data == "wc:close")
async def close_waifu_card(call: CallbackQuery):
    if call.message:
        try:
            await call.message.delete()
        except Exception:
            pass

    await call.answer()
