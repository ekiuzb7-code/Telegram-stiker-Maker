"""Stiker-pack yaratish va packga qo'shish (stateless, deterministik nom)."""

import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import InputSticker, Message

from bot.handlers.media import build_sticker
from bot.states import CreatePack

logger = logging.getLogger(__name__)
router = Router(name="pack")


def register(dp: Dispatcher) -> None:
    dp.include_router(router)


@router.message(CreatePack.title)
async def on_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title or len(title) > 64:
        await message.answer("⚠️ Nom 1–64 belgi bo'lsin.")
        return
    await state.update_data(title=title)
    await state.set_state(CreatePack.emoji)
    await message.answer("🙂 Pack uchun bitta emoji yuboring:")


@router.message(CreatePack.emoji)
async def on_emoji(message: Message, bot: Bot, state: FSMContext) -> None:
    emoji = (message.text or "").strip()
    if not emoji:
        await message.answer("⚠️ Emoji yuboring.")
        return

    data = await state.get_data()
    if "file_id" not in data:
        await state.clear()
        await message.answer("⚠️ Avval media yuboring.")
        return

    await state.clear()

    try:
        sticker_file, fmt = await build_sticker(bot, data)
    except Exception:
        logger.exception("Stiker tayyorlashda xato")
        await message.answer("⚠️ Xatolik yuz berdi. Qaytadan urinib ko'ring.")
        return

    me = await bot.get_me()
    name = f"stikerbot_{message.from_user.id}_by_{me.username}"
    sticker = InputSticker(sticker=sticker_file, emoji_list=[emoji], format=fmt)
    pack_url = f"https://t.me/addstickers/{name}"

    try:
        try:
            await bot.add_sticker_to_set(
                user_id=message.from_user.id, name=name, sticker=sticker
            )
            await message.answer(f"✅ Stiker packga qo'shildi: {pack_url}")
        except TelegramBadRequest as e:
            if "STICKERSET_INVALID" in str(e).upper():
                await bot.create_new_sticker_set(
                    user_id=message.from_user.id,
                    name=name,
                    title=data.get("title", "Stikerlarim"),
                    stickers=[sticker],
                )
                await message.answer(f"🎉 Pack yaratildi: {pack_url}")
            else:
                raise
    except TelegramBadRequest as e:
        await message.answer(f"⚠️ Telegram xatosi: {e.message}")