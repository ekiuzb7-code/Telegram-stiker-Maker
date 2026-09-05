import os

from dotenv import load_dotenv

# Loyiha ildizidagi .env faylni yuklaydi (lokal ishlatish uchun)
load_dotenv()


def load_token() -> str:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "BOT_TOKEN topilmadi. Loyiha papkasida .env fayl yarating va "
            "BOT_TOKEN=<tokeningiz> deb yozing."
        )
    return token