"""Rasmlarni Telegram stiker formatiga o'girish (512x512 PNG)."""

import io

from PIL import Image

STICKER_SIZE = 512


def fit_to_512(image: Image.Image) -> Image.Image:
    """Rasmni 512x512 kvadratga sig'diradi (tomonlarning biri 512, qolgani <= 512)."""
    w, h = image.size
    if w == STICKER_SIZE and h == STICKER_SIZE:
        return image
    scale = STICKER_SIZE / max(w, h)
    new_w = max(1, round(w * scale))
    new_h = max(1, round(h * scale))
    return image.resize((new_w, new_h), Image.Resampling.LANCZOS)


def to_sticker_png(image: Image.Image) -> io.BytesIO:
    """Rasmni Telegram statik stiker talabiga mos PNG baytga o'giradi."""
    fitted = fit_to_512(image.convert("RGBA"))
    # Transparent fon bilan kvadrat canvasga joylashtiramiz
    canvas = Image.new("RGBA", (STICKER_SIZE, STICKER_SIZE), (0, 0, 0, 0))
    offset = ((STICKER_SIZE - fitted.width) // 2, (STICKER_SIZE - fitted.height) // 2)
    canvas.paste(fitted, offset, fitted)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return buf