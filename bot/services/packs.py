"""Stiker-pack yordamchi funksiyalari (stateless).

Packlar raqamlangan nomlar bilan saqlanadi: stikerbot_<user>_<n>_by_<bot>.
Birinchi versiyadagi indeksiz pack (legacy) ham qo'llab-quvvatlanadi.
"""

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

MAX_PACKS = 20


def pack_name(user_id: int, bot_username: str, index: int) -> str:
    """Foydalanuvchining raqamlangan pack nomi."""
    return f"stikerbot_{user_id}_{index}_by_{bot_username}"


def legacy_pack_name(user_id: int, bot_username: str) -> str:
    """Birinchi versiyada yaratilgan yagona pack nomi."""
    return f"stikerbot_{user_id}_by_{bot_username}"


async def get_existing_pack(bot: Bot, name: str):
    """Pack mavjud bo'lsa StickerSet qaytaradi, aks holda None."""
    try:
        return await bot.get_sticker_set(name)
    except TelegramBadRequest:
        return None


async def discover_packs(bot: Bot, user_id: int, bot_username: str) -> list:
    """Foydalanuvchining barcha packlarini topadi: [(nomi, StickerSet), ...]."""
    packs = []
    legacy = await get_existing_pack(bot, legacy_pack_name(user_id, bot_username))
    if legacy:
        packs.append((legacy_pack_name(user_id, bot_username), legacy))
    for i in range(1, MAX_PACKS + 1):
        name = pack_name(user_id, bot_username, i)
        pack = await get_existing_pack(bot, name)
        if pack is None:
            break
        packs.append((name, pack))
    return packs


async def next_pack_name(bot: Bot, user_id: int, bot_username: str):
    """Yangi pack uchun birinchi bo'sh raqamli nomni qaytaradi (chegara yetgan bo'lsa None)."""
    for i in range(1, MAX_PACKS + 1):
        name = pack_name(user_id, bot_username, i)
        if await get_existing_pack(bot, name) is None:
            return name
    return None