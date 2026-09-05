# StikerBot 🎨

Telegram stiker yaratuvchi bot: rasm, GIF va videoni stiker formatiga o'giradi, rasmlar uchun fonni o'chiradi (toza Python, AI servisiz), stiker-pack yaratadi.

## Imkoniyatlar

- 📸 Rasm → 512×512 PNG stiker (ixtiyoriy fon o'chirish bilan)
- 🎞 GIF → animated WebP stiker
- 🎬 Video → WebM video stiker (≤3s)
- 🪄 Fon o'chirish: avtomatik aniqlash yoki rangni qo'lda tanlash
- 📦 Stiker-pack yaratish va qo'shish
- 🚂 Railway'da ishlash uchun stateless (ma'lumot bazasisiz)

## Lokal ishga tushirish

1. Python 3.11+ va FFmpeg o'rnatilgan bo'lishi kerak.
2. `@BotFather` dan bot token oling.
3. `.env.example` ni `.env` ga nusxalab, `BOT_TOKEN` ni to'ldiring.

```bash
pip install -r requirements.txt
python -m bot.main
```

## Testlar

```bash
pytest tests/
```

## Railway'da deploy

1. Repozitoriyani GitHub'ga yuklang.
2. Railway'da "New Project → Deploy from GitHub repo".
3. Variables bo'limiga `BOT_TOKEN` qo'shing.
4. Deploy avtomatik Dockerfile orqali bajariladi — boshqa sozlama kerak emas.

## Tuzilish

```
bot/
├── main.py            # entrypoint (long polling)
├── config.py          # BOT_TOKEN yuklash
├── states.py          # FSM holatlari
├── handlers/          # start, media, pack
└── services/          # image, video, bgremove
tests/                 # pytest unit testlar
```