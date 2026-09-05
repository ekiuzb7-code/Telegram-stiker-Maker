"""Media qabul qilish va stiker tanlovlarini ko'rsatish."""

import asyncio
import io
import logging
import shutil
import tempfile
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from PIL import Image

from bot.services import bgremove, image, video
from bot.services.packs import get_existing_pack, pack_name
from bot.states import CreatePack, PickColor

logger = logging.getLogger(__name__)
router = Router(name="media")

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_VIDEO_BYTES = 20 * 1024 * 1024  # Bot API getFile cheklovi

# Telegram stiker formatlari (InputSticker uchun)
STICKER_FORMATS = {"photo": "static", "gif": "animated", "video": "video"}

PHOTO_KB = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="🪄 Fonni o'chirish", callback_data="action:bg"),
        InlineKeyboardButton(text="✅ Oddiy stiker", callback_data="action:plain"),
    ],
    [
        InlineKeyboardButton(text="🎨 Rangni o'zim tanlayman", callback_data="action:pickcolor"),
        InlineKeyboardButton(text="📦 Packga qo'shish", callback_data="action:pack"),
    ],
])

ANIM_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✅ Stiker qilish", callback_data="action:plain")],
    [InlineKeyboardButton(text="📦 Packga qo'shish", callback_data="action:pack")],
])


def register(dp: Dispatcher) -> None:
    dp.include_router(router)


@router.message(F.photo)
async def on_photo(message: Message, state: FSMContext) -> None:
    photo = message.photo[-1]
    if photo.file_size and photo.file_size > MAX_IMAGE_BYTES:
        await message.answer("⚠️ Rasm juda katta. 5 MB gacha rasm yuboring.")
        return
    await state.set_data({"file_id": photo.file_id, "kind": "photo"})
    await message.answer("Qanday stiker qilaylik?", reply_markup=PHOTO_KB)


@router.message(F.animation)
async def on_animation(message: Message, state: FSMContext) -> None:
    anim = message.animation
    if anim.file_size and anim.file_size > MAX_VIDEO_BYTES:
        await message.answer("⚠️ Fayl juda katta. 20 MB gacha yuboring.")
        return
    is_gif = (anim.mime_type or "") == "image/gif"
    await state.set_data({"file_id": anim.file_id, "kind": "gif" if is_gif else "video"})
    await message.answer("Qanday stiker qilaylik?", reply_markup=ANIM_KB)


@router.message(F.video)
async def on_video(message: Message, state: FSMContext) -> None:
    vid = message.video
    if vid.file_size and vid.file_size > MAX_VIDEO_BYTES:
        await message.answer("⚠️ Video juda katta. 20 MB gacha yuboring.")
        return
    await state.set_data({"file_id": vid.file_id, "kind": "video"})
    await message.answer("Qanday stiker qilaylik?", reply_markup=ANIM_KB)


# ---- Konvertatsiya yordamchilari (pack.py ham ishlatadi) ----

def process_photo(
    data: bytes,
    remove_bg: bool = False,
    color: tuple[int, int, int] | None = None,
) -> bytes:
    """Rasmdan PNG stiker baytlarini tayyorlaydi."""
    img = Image.open(io.BytesIO(data))
    if remove_bg:
        img = bgremove.remove_background_floodfill(img, color=color)
    return image.to_sticker_png(img).read()


def process_animated(data: bytes, kind: str) -> tuple[bytes, str]:
    """GIF/video faylni WebP/WebM stiker baytlariga o'giradi."""
    tmpdir = tempfile.mkdtemp(prefix="stikerbot_")
    try:
        src = Path(tmpdir) / ("in.gif" if kind == "gif" else "in.mp4")
        src.write_bytes(data)
        if kind == "gif":
            dst = Path(tmpdir) / "out.webp"
            video.gif_to_sticker_webp(src, dst)
            return dst.read_bytes(), "sticker.webp"
        dst = Path(tmpdir) / "out.webm"
        video.video_to_sticker_webm(src, dst)
        return dst.read_bytes(), "sticker.webm"
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


async def build_sticker(
    bot: Bot,
    state_data: dict,
    remove_bg: bool = False,
    color: tuple[int, int, int] | None = None,
) -> tuple[BufferedInputFile, str]:
    """Telegram'dagi faylni yuklab olib, stiker faylini tayyorlaydi.

    (stiker_fayli, telegram_formati) qaytaradi.
    """
    kind = state_data["kind"]
    buf = await bot.download(state_data["file_id"])
    data = buf.read()
    if kind == "photo":
        out = await asyncio.to_thread(process_photo, data, remove_bg, color)
        return BufferedInputFile(out, filename="sticker.png"), STICKER_FORMATS[kind]
    out, filename = await asyncio.to_thread(process_animated, data, kind)
    return BufferedInputFile(out, filename=filename), STICKER_FORMATS[kind]


# ---- Inline tugmalar ----

@router.callback_query(F.data.startswith("action:"))
async def on_action(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    action = callback.data.split(":", 1)[1]
    data = await state.get_data()
    if not data or "file_id" not in data:
        await callback.answer("Avval rasm, GIF yoki video yuboring", show_alert=True)
        return

    if action == "pickcolor":
        await state.set_state(PickColor.color)
        await callback.message.answer(
            "🎨 Fon rangi kodini yuboring (masalan, <code>#FFFFFF</code>)"
        )
        await callback.answer()
        return

    if action == "pack":
        me = await bot.get_me()
        name = pack_name(callback.from_user.id, me.username)
        existing = await get_existing_pack(bot, name)
        if existing:
            # Pack allaqachon bor — faqat emoji so'rab, o'sha packga qo'shamiz
            await state.set_state(CreatePack.emoji)
            await callback.message.answer(
                f"📦 «{existing.title}» packiga qo'shaman. 🙂 Bitta emoji yuboring:"
            )
        else:
            await state.set_state(CreatePack.title)
            await callback.message.answer("📦 Yangi pack nomini yozing:")
        await callback.answer()
        return

    await callback.answer("Ishlanmoqda...")
    try:
        sticker_file, _ = await build_sticker(
            bot, data, remove_bg=(action == "bg")
        )
        await bot.send_sticker(chat_id=callback.message.chat.id, sticker=sticker_file)
        await callback.message.answer(
            "✅ Tayyor! Packga qo'shmoqchi bo'lsangiz «📦 Packga qo'shish» tugmasini bosing."
        )
    except bgremove.BgRemoveError as e:
        await callback.message.answer(f"⚠️ {e}")
    except video.FFmpegMissing:
        await callback.message.answer(
            "⚠️ FFmpeg o'rnatilmagan — GIF/video stikerlar hozircha ishlamaydi."
        )
    except Exception:
        logger.exception("Stiker yaratishda xato")
        await callback.message.answer("⚠️ Xatolik yuz berdi. Boshqa fayl bilan urinib ko'ring.")


@router.message(PickColor.color)
async def on_color(message: Message, bot: Bot, state: FSMContext) -> None:
    data = await state.get_data()
    if "file_id" not in data:
        await state.clear()
        await message.answer("⚠️ Avval rasm yuboring.")
        return

    text = (message.text or "").strip().lstrip("#")
    try:
        if len(text) != 6:
            raise ValueError
        color = (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
    except ValueError:
        await message.answer("⚠️ Rang kodini to'g'ri yozing, masalan <code>#FFFFFF</code>")
        return

    await state.clear()
    try:
        sticker_file, _ = await build_sticker(bot, data, remove_bg=True, color=color)
        await bot.send_sticker(chat_id=message.chat.id, sticker=sticker_file)
    except bgremove.BgRemoveError as e:
        await message.answer(f"⚠️ {e}")
    except Exception:
        logger.exception("Stiker yaratishda xato")
        await message.answer("⚠️ Xatolik yuz berdi. Boshqa rang bilan urinib ko'ring.")