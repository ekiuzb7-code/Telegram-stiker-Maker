"""Toza Pillow yordamida fonni o'chirish (AI kerak emas).

Fon rangi tasvirning 4 burchagidan avtomatik aniqlanadi, keyin shu
rangga yaqin pikseller shaffof qilinadi.
"""

from collections import deque

from PIL import Image

# Burchakdagi fon rangi bilan piksel orasidagi maksimal Evklid masofasi
DEFAULT_TOLERANCE = 40
# Burchakdan olingadagi namuna nuqtalar chegarasi
CORNER_SAMPLES = 10


class BgRemoveError(Exception):
    """Natija foydalanuvchiga ko'rsatish mumkin bo'lgan xatolik."""


def detect_background_color(image: Image.Image) -> tuple[int, int, int]:
    """Tasvirning 4 burchagidagi piksellardan eng ko'p uchraydigan rangni topadi."""
    rgb = image.convert("RGB")
    w, h = rgb.size
    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    counts: dict[tuple[int, int, int], int] = {}
    for x, y in corners:
        px = rgb.getpixel((x, y))
        counts[px] = counts.get(px, 0) + 1
    return max(counts, key=counts.get)


def _color_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def remove_background(
    image: Image.Image,
    color: tuple[int, int, int] | None = None,
    tolerance: float = DEFAULT_TOLERANCE,
) -> Image.Image:
    """Fon rangini (berilmasa avtomatik) shaffof qilib yangi RGBA rasm qaytaradi.

    Natija yaroqsiz bo'lsa (hammasi o'chsa yoki hech narsa o'chmasa)
    BgRemoveError ko'tariladi.
    """
    rgba = image.convert("RGBA")
    if color is None:
        color = detect_background_color(rgba)

    w, h = rgba.size
    pixels = rgba.load()
    removed = 0

    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            if _color_distance((r, g, b), color) <= tolerance:
                pixels[x, y] = (r, g, b, 0)
                removed += 1

    if removed == 0:
        raise BgRemoveError("Fon topilmadi. Rangni o'zingiz tanlab ko'ring.")
    if removed >= w * h * 0.98:
        raise BgRemoveError("Deyarli butun rasm fon bo'lib chiqdi. Boshqa rang tanlang.")

    return rgba


def remove_background_floodfill(
    image: Image.Image,
    color: tuple[int, int, int] | None = None,
    tolerance: float = DEFAULT_TOLERANCE,
) -> Image.Image:
    """Faqat chetlar bilan bog'langan fon piksellerini o'chiradi (flood-fill).

    Rasmdagi obyekt ichida fon rangiga o'xshash piksel bo'lsa, bu usul
    uni saqlab qoladi — global usuldan aniqroq.
    """
    rgba = image.convert("RGBA")
    if color is None:
        color = detect_background_color(rgba)

    w, h = rgba.size
    pixels = rgba.load()
    visited = [[False] * w for _ in range(h)]

    queue: deque[tuple[int, int]] = deque()
    # Chegara pikselleridan boshlaymiz
    for x in range(w):
        queue.append((x, 0))
        queue.append((x, h - 1))
    for y in range(h):
        queue.append((0, y))
        queue.append((w - 1, y))

    removed = 0
    total = 0

    while queue:
        x, y = queue.popleft()
        if not (0 <= x < w and 0 <= y < h) or visited[y][x]:
            continue
        visited[y][x] = True

        r, g, b, a = pixels[x, y]
        if a > 0 and _color_distance((r, g, b), color) <= tolerance:
            pixels[x, y] = (r, g, b, 0)
            removed += 1
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx]:
                    queue.append((nx, ny))
        total += 1

    if removed == 0:
        raise BgRemoveError("Fon topilmadi. Rangni o'zingiz tanlab ko'ring.")
    if removed >= w * h * 0.98:
        raise BgRemoveError("Deyarli butun rasm fon bo'lib chiqdi. Boshqa rang tanlang.")

    return rgba