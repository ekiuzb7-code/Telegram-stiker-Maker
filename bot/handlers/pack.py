"""Stiker-pack boshqaruvi: yaratish, qo'shish, /mypacks, /delsticker, /delpack, /cancel."""

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
from bot.services.packs import discover_packs, get_existing_pack, next_pack_name
from bot.states import CreatePack

logger = logging.getLogger(__name__)
router = Router(name="pack")


def register(dp: Dispatcher) -> None:
    dp.include_router(router)


def pack_select_kb(packs, prefix: str) -> InlineKeyboardMarkup:
    """Packlar ro'yxati — inline tugmalar."""
    rows = []
    for name, pack in packs:
        rows.append([
            InlineKeyboardButton(
                text=f"📦 {pack.title} ({len(pack.stickers)} ta)",
                callback_data=f"{prefix}:{name}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---- Packga qo'shish: pack tanlash va emoji ----

@router.callback_query(F.data.startswith("topack:"))
async def choose_pack(callback: CallbackQuery, state: FSMContext) -> None:
    name = callback.data.split(":", 1)[1]
    pack = await get_existing_pack(callback.bot, name)
    if not pack:
        await callback.answer("Pack topilmadi", show_alert=True)
        return
    await state.update_data(pack_name=name)
    await state.set_state(CreatePack.emoji)
    await callback.message.answer(
        f"📦 «{pack.title}» packiga qo'shaman. 🙂 Bitta emoji yuboring:"
    )
    await callback.answer()


@router.callback_query(F.data == "newpack")
async def new_pack(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CreatePack.title)
    await callback.message.answer("📦 Yangi pack nomini yozing:")
    await callback.answer()


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
    sticker = InputSticker(sticker=sticker_file, emoji_list=[emoji], format=fmt)
    target_name = data.get("pack_name")

    try:
        if target_name:
            existing = await get_existing_pack(bot, target_name)
            if not existing:
                await message.answer("⚠️ Pack topilmadi. Qaytadan urinib ko'ring.")
                return
            before = len(existing.stickers)
            await bot.add_sticker_to_set(
                user_id=message.from_user.id, name=target_name, sticker=sticker
            )
            # Telegram dublikat stikerni qo'shmaydi — haqiqiy sonni tekshiramiz
            updated = await get_existing_pack(bot, target_name)
            after = len(updated.stickers) if updated else before
            pack_url = f"https://t.me/addstickers/{target_name}"
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
            name = await next_pack_name(bot, message.from_user.id, me.username)
            if not name:
                await message.answer("⚠️ Packlar soni chegaraga yetdi (20 ta).")
                return
            await bot.create_new_sticker_set(
                user_id=message.from_user.id,
                name=name,
                title=data.get("title", "Stikerlarim"),
                stickers=[sticker],
            )
            await message.answer(
                f"🎉 Pack yaratildi: https://t.me/addstickers/{name}"
            )
    except TelegramBadRequest as e:
        logger.exception("Pack amaliyotida Telegram xatosi")
        await message.answer(f"⚠️ Telegram xatosi: {e.message}")
    except Exception:
        logger.exception("Pack amaliyotida kutilmagan xato")
        await message.answer("⚠️ Xatolik yuz berdi. Qaytadan urinib ko'ring.")
    finally:
        await state.clear()


# ---- Packlarni ko'rish ----

@router.message(Command("mypacks"))
async def mypacks(message: Message, bot: Bot) -> None:
    me = await bot.get_me()
    packs = await discover_packs(bot, message.from_user.id, me.username)
    if not packs:
        await message.answer(
            "📭 Sizda hali pack yo'q. Media yuborib, «📦 Packga qo'shish» tugmasini bosing."
        )
        return
    blocks = []
    for name, pack in packs:
        emoji_list = " ".join(s.emoji or "❓" for s in pack.stickers[:10])
        blocks.append(
            f"📦 <b>{pack.title}</b> — {len(pack.stickers)} ta\n"
            f"   {emoji_list}\n"
            f"   https://t.me/addstickers/{name}"
        )
    await message.answer("\n\n".join(blocks))


# ---- Stikerni o'chirish (avval pack, keyin stiker tanlanadi) ----

@router.message(Command("delsticker"))
async def delsticker(message: Message, bot: Bot) -> None:
    me = await bot.get_me()
    packs = await discover_packs(bot, message.from_user.id, me.username)
    if not packs:
        await message.answer("📭 Sizda pack yo'q.")
        return
    await message.answer(
        "Qaysi packdan stiker o'chiray?",
        reply_markup=pack_select_kb(packs, "delstickerpick"),
    )


@router.callback_query(F.data.startswith("delstickerpick:"))
async def delsticker_pick(callback: CallbackQuery) -> None:
    name = callback.data.split(":", 1)[1]
    pack = await get_existing_pack(callback.bot, name)
    if not pack:
        await callback.answer("Pack topilmadi", show_alert=True)
        return
    rows = []
    for i, s in enumerate(pack.stickers[:20]):
        rows.append([
            InlineKeyboardButton(
                text=f"🗑 {i + 1}. {s.emoji or '❓'}",
                callback_data=f"delsticker:{name}:{i}",
            )
        ])
    rows.append([InlineKeyboardButton(text="❌ Bekor", callback_data="delsticker:no")])
    await callback.message.answer(
        f"📦 «{pack.title}» — qaysi stikerni o'chiray? (jami {len(pack.stickers)} ta)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delsticker:"))
async def delsticker_confirm(callback: CallbackQuery) -> None:
    if callback.data == "delsticker:no":
        await callback.answer("Bekor qilindi")
        return

    _, name, idx = callback.data.split(":", 2)
    index = int(idx)
    pack = await get_existing_pack(callback.bot, name)
    if not pack or index >= len(pack.stickers):
        await callback.answer("Pack o'zgargan. Qaytadan /delsticker bosing.", show_alert=True)
        return

    sticker = pack.stickers[index]
    try:
        await callback.bot.delete_sticker_from_set(sticker=sticker.file_id)
        await callback.message.answer(
            f"🗑 {index + 1}-stiker ({sticker.emoji or '❓'}) o'chirildi. "
            f"Packda endi {len(pack.stickers) - 1} ta qoldi."
        )
    except TelegramBadRequest as e:
        await callback.message.answer(f"⚠️ O'chirishda xato: {e.message}")
    await callback.answer()


# ---- Packni o'chirish (avval pack tanlanadi) ----

@router.message(Command("delpack"))
async def delpack(message: Message, bot: Bot) -> None:
    me = await bot.get_me()
    packs = await discover_packs(bot, message.from_user.id, me.username)
    if not packs:
        await message.answer("📭 Sizda pack yo'q.")
        return
    await message.answer(
        "Qaysi packni o'chiray? Buni qaytarib bo'lmaydi!",
        reply_markup=pack_select_kb(packs, "delpackpick"),
    )


@router.callback_query(F.data.startswith("delpackpick:"))
async def delpack_pick(callback: CallbackQuery) -> None:
    name = callback.data.split(":", 1)[1]
    pack = await get_existing_pack(callback.bot, name)
    if not pack:
        await callback.answer("Pack topilmadi", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🗑 Ha, o'chirish", callback_data=f"delpack:{name}:yes"),
            InlineKeyboardButton(text="❌ Bekor", callback_data="delpack:no"),
        ],
    ])
    await callback.message.answer(
        f"🗑 «{pack.title}» packini o'chiraymi? Buni qaytarib bo'lmaydi!",
        reply_markup=kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delpack:"))
async def delpack_confirm(callback: CallbackQuery) -> None:
    if callback.data == "delpack:no":
        await callback.answer("Bekor qilindi")
        return
    name = callback.data.split(":", 2)[1]
    try:
        await callback.bot.delete_sticker_set(name)
        await callback.message.answer("🗑 Pack o'chirildi.")
    except TelegramBadRequest as e:
        await callback.message.answer(f"⚠️ O'chirishda xato: {e.message}")
    await callback.answer()


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Amal bekor qilindi.")