"""Stiker-pack yordamchi funksiyalari (stateless)."""

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest


def pack_name(user_id: int, bot_username: str) -> str:
    """Har foydalanuvchi uchun bitta deterministik pack nomi."""
    return f"stikerbot_{user_id}_by_{bot_username}"


async def get_existing_pack(bot: Bot, name: str):
    """Pack mavjud bo'lsa StickerSet qaytaradi, aks holda None."""
    try:
        return await bot.get_sticker_set(name)
    except TelegramBadRequest:
        return None