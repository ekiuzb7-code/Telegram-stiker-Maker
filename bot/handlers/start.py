"""/start va /help buyruqlari."""

from aiogram import Dispatcher, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router(name="start")

HELP_TEXT = (
    "👋 Salom! Men stiker yaratuvchi botman.\n\n"
    "📸 <b>Rasm</b> yuboring — stiker qilib beraman, xohlasangiz fonini o'chiraman.\n"
    "🎞 <b>GIF</b> yuborsangiz — animatsion stikerga aylantiraman.\n"
    "🎬 <b>Video</b> yuborsangiz — video stikerga aylantiraman.\n\n"
    "<b>Buyruqlar:</b>\n"
    "/mypacks — packlaringizni ko'rish\n"
    "/delsticker — packdan bitta stikerni o'chirish\n"
    "/delpack — butun packni o'chirish\n"
    "/cancel — davom etayotgan amalni bekor qilish\n"
    "/help — yordam\n\n"
    "Boshlash: istalgan media yuboring!"
)


def register(dp: Dispatcher) -> None:
    dp.include_router(router)


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("help"))
async def help_cmd(message: Message) -> None:
    await message.answer(HELP_TEXT)