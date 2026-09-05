import io

from PIL import Image

from bot.services.image import STICKER_SIZE, fit_to_512, to_sticker_png


def _solid(color, size=(800, 400)) -> Image.Image:
    return Image.new("RGBA", size, color)


def test_fit_to_512_landscape():
    img = fit_to_512(_solid((255, 0, 0, 255)))
    assert max(img.size) == STICKER_SIZE
    assert img.size[0] > img.size[1]


def test_fit_to_512_already_correct():
    img = _solid((0, 255, 0, 255), (512, 512))
    assert fit_to_512(img).size == (512, 512)


def test_to_sticker_png_output():
    buf = to_sticker_png(_solid((0, 0, 255, 255)))
    out = Image.open(buf)
    assert out.format == "PNG"
    assert out.size == (STICKER_SIZE, STICKER_SIZE)
    assert out.mode == "RGBA"


def test_to_sticker_png_keeps_transparency():
    buf = to_sticker_png(_solid((0, 0, 0, 0)))
    out = Image.open(buf)
    # To'liq shaffof rasm — burchak pikseli shaffof qoladi
    assert out.getpixel((0, 0))[3] == 0