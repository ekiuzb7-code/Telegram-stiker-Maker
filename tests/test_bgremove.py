import pytest
from PIL import Image

from bot.services.bgremove import (
    BgRemoveError,
    detect_background_color,
    remove_background,
    remove_background_floodfill,
)


def _img_with_object(bg=(255, 255, 255), obj=(255, 0, 0), size=100):
    """Bir rang fon, markazda boshqa rang kvadrat."""
    img = Image.new("RGB", (size, size), bg)
    px = img.load()
    for y in range(30, 70):
        for x in range(30, 70):
            px[x, y] = obj
    return img


def test_detect_background_white():
    img = _img_with_object()
    assert detect_background_color(img) == (255, 255, 255)


def test_remove_background_white():
    out = remove_background(_img_with_object())
    # Burchak shaffof, markazdagi obyekt saqlanadi
    assert out.getpixel((0, 0))[3] == 0
    assert out.getpixel((50, 50))[3] == 255


def test_floodfill_keeps_island_of_same_color():
    # Obyekt ichida fon rangiga o'xshash "orolcha" bo'lsa, flood-fill uni saqlaydi
    img = _img_with_object(obj=(200, 200, 200))
    px = img.load()
    for y in range(40, 50):
        for x in range(40, 50):
            px[x, y] = (255, 255, 255)  # fon rangidagi orolcha
    out = remove_background_floodfill(img)
    assert out.getpixel((45, 45))[3] == 255  # orolcha saqlandi


def test_explicit_color():
    out = remove_background(_img_with_object(bg=(0, 128, 0)), color=(0, 128, 0))
    assert out.getpixel((0, 0))[3] == 0


def test_nothing_removed_raises():
    img = Image.new("RGB", (50, 50), (10, 20, 30))
    with pytest.raises(BgRemoveError):
        remove_background(img, color=(255, 0, 0), tolerance=5)


def test_everything_removed_raises():
    img = Image.new("RGB", (50, 50), (255, 255, 255))
    with pytest.raises(BgRemoveError):
        remove_background(img)