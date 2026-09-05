import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from bot import config
from bot.handlers import media, pack, start


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    token = config.load_token()

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()

    start.register(dp)
    media.register(dp)
    pack.register(dp)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())