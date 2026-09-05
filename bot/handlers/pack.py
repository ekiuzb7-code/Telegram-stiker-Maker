"""Stiker-pack boshqaruvi: yaratish, qo'shish, /mypacks, /delpack, /cancel."""

import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputSticker,
    Message,
)

from bot.handlers.media import build_sticker
from bot.services.packs import get_existing_pack, pack_name
from bot.states import CreatePack

logger = logging.getLogger(__name__)
router = Router(name="pack")

DELETE_KB = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="🗑 Ha, o'chirish", callback_data="delpack:yes"),
        InlineKeyboardButton(text="❌ Bekor", callback_data="delpack:no"),
    ],
])


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
        await message.answer(
            "⚠️ Oddiy matn emoji yuboring (masalan 😀). "
            "Stiker yoki custom emoji qabul qilinmaydi."
        )
        return

    data = await state.get_data()
    if "file_id" not in data:
        await state.clear()
        await message.answer("⚠️ Avval media yuboring.")
        return

    try:
        sticker_file, fmt = await build_sticker(bot, data)
    except Exception:
        logger.exception("Stiker tayyorlashda xato")
        await message.answer("⚠️ Xatolik yuz berdi. Qaytadan urinib ko'ring.")
        return

    me = await bot.get_me()
    name = pack_name(message.from_user.id, me.username)
    existing = await get_existing_pack(bot, name)
    sticker = InputSticker(sticker=sticker_file, emoji_list=[emoji], format=fmt)
    pack_url = f"https://t.me/addstickers/{name}"

    try:
        if existing:
            before = len(existing.stickers)
            await bot.add_sticker_to_set(
                user_id=message.from_user.id, name=name, sticker=sticker
            )
            # Telegram dublikat stikerni qo'shmaydi — haqiqiy sonni tekshiramiz
            updated = await get_existing_pack(bot, name)
            after = len(updated.stickers) if updated else before
            if after > before:
                await message.answer(
                    f"✅ Stiker qo'shildi (packda jami {after} ta): {pack_url}"
                )
            else:
                await message.answer(
                    "⚠️ Bu stiker packda allaqachon bor (bir xil rasm qayta "
                    f"qo'shilmaydi). Packda jami {after} ta: {pack_url}"
                )
        else:
            await bot.create_new_sticker_set(
                user_id=message.from_user.id,
                name=name,
                title=data.get("title", "Stikerlarim"),
                stickers=[sticker],
            )
            await message.answer(f"🎉 Pack yaratildi: {pack_url}")
    except TelegramBadRequest as e:
        logger.exception("Pack amaliyotida Telegram xatosi")
        await message.answer(f"⚠️ Telegram xatosi: {e.message}")
    except Exception:
        logger.exception("Pack amaliyotida kutilmagan xato")
        await message.answer("⚠️ Xatolik yuz berdi. Qaytadan urinib ko'ring.")
    finally:
        await state.clear()


@router.message(Command("mypacks"))
async def mypacks(message: Message, bot: Bot) -> None:
    me = await bot.get_me()
    name = pack_name(message.from_user.id, me.username)
    pack = await get_existing_pack(bot, name)
    if not pack:
        await message.answer(
            "📭 Sizda hali pack yo'q. Media yuborib, «📦 Packga qo'shish» tugmasini bosing."
        )
        return
    # Diagnostika uchun har bir stiker emojisini ko'rsatamiz
    emoji_list = " ".join(s.emoji or "❓" for s in pack.stickers[:20])
    await message.answer(
        f"📦 <b>{pack.title}</b>\n"
        f"Stikerlar soni: {len(pack.stickers)} ta\n"
        f"Stikerlar: {emoji_list}\n"
        f"Havola: https://t.me/addstickers/{name}\n\n"
        "Agar havolada kamroq ko'rinsa, Telegram keshi sabab bo'lishi mumkin — "
        "havolani boshqa qurilmada yoki 1–2 daqiqadan keyin ochib ko'ring."
    )


@router.message(Command("delsticker"))
async def delsticker(message: Message, bot: Bot) -> None:
    me = await bot.get_me()
    name = pack_name(message.from_user.id, me.username)
    pack = await get_existing_pack(bot, name)
    if not pack:
        await message.answer("📭 Sizda pack yo'q.")
        return

    # Har stiker uchun inline tugma: emoji + tartib raqami
    rows = []
    for i, s in enumerate(pack.stickers[:20]):
        rows.append([
            InlineKeyboardButton(
                text=f"🗑 {i + 1}. {s.emoji or '❓'}",
                callback_data=f"delsticker:{i}",
            )
        ])
    rows.append([InlineKeyboardButton(text="❌ Bekor", callback_data="delsticker:no")])
    await message.answer(
        f"📦 «{pack.title}» — qaysi stikerni o'chiray? (jami {len(pack.stickers)} ta)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("delsticker:"))
async def delsticker_confirm(callback: CallbackQuery, bot: Bot) -> None:
    if callback.data == "delsticker:no":
        await callback.answer("Bekor qilindi")
        return

    index = int(callback.data.split(":", 1)[1])
    me = await bot.get_me()
    name = pack_name(callback.from_user.id, me.username)
    pack = await get_existing_pack(bot, name)
    if not pack or index >= len(pack.stickers):
        await callback.answer("Pack o'zgargan. Qaytadan /delsticker bosing.", show_alert=True)
        return

    sticker = pack.stickers[index]
    try:
        await bot.delete_sticker_from_set(sticker=sticker.file_id)
        await callback.message.answer(
            f"🗑 {index + 1}-stiker ({sticker.emoji or '❓'}) o'chirildi. "
            f"Packda endi {len(pack.stickers) - 1} ta qoldi."
        )
    except TelegramBadRequest as e:
        await callback.message.answer(f"⚠️ O'chirishda xato: {e.message}")
    await callback.answer()


@router.message(Command("delpack"))
async def delpack(message: Message, bot: Bot) -> None:
    me = await bot.get_me()
    name = pack_name(message.from_user.id, me.username)
    pack = await get_existing_pack(bot, name)
    if not pack:
        await message.answer("📭 Sizda pack yo'q.")
        return
    await message.answer(
        f"🗑 «{pack.title}» packini o'chiraymi? Buni qaytarib bo'lmaydi!",
        reply_markup=DELETE_KB,
    )


@router.callback_query(F.data.startswith("delpack:"))
async def delpack_confirm(callback: CallbackQuery, bot: Bot) -> None:
    if callback.data == "delpack:no":
        await callback.answer("Bekor qilindi")
        return
    me = await bot.get_me()
    name = pack_name(callback.from_user.id, me.username)
    try:
        await bot.delete_sticker_set(name)
        await callback.message.answer("🗑 Pack o'chirildi.")
    except TelegramBadRequest as e:
        await callback.message.answer(f"⚠️ O'chirishda xato: {e.message}")
    await callback.answer()


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Amal bekor qilindi.")