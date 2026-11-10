"""Original DELTARUNE sprite and dialogue drawing helpers."""

from functools import lru_cache
import json
from os import environ
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(environ.get('DELTARUNE_PARTY_WORKSPACE') or Path(__file__).parent).expanduser().resolve()
ART = ROOT / 'assets/deltarune'
CHAPTER5 = ROOT / 'assets/chapter5'
NEAR = Image.Resampling.NEAREST
SIZE = (240, 180)


@lru_cache(maxsize=144)
def art(name):
    folder = CHAPTER5 if name.startswith('flowery-') else ART
    return Image.open(folder / f'{name}.png').convert('RGBA')


@lru_cache(maxsize=196)
def sprite(name, height):
    image = art(name)
    image = image.crop(image.getbbox())
    width = max(1, round(image.width * height / image.height))
    return image.resize((width, height), NEAR)


def paste(image, layer, x, y):
    image.paste(layer, (round(x), round(y)), layer)


def centered(image, layer, x, y):
    paste(image, layer, x - layer.width / 2, y - layer.height / 2)


def smooth(value):
    t = max(0, min(1, value))
    return t * t * (3 - 2 * t)


def mix(a, b, u):
    return a + (b - a) * u


def point(a, b, u):
    return tuple(mix(x, y, u) for x, y in zip(a, b))


class Text:
    def __init__(self):
        atlas = art('font')
        data = json.loads((ART / 'font.json').read_text())['glyphs']
        self.glyphs = {}
        for code, glyph in data.items():
            x, y, w, h = (glyph[key] for key in ('x', 'y', 'w', 'h'))
            self.glyphs[chr(int(code))] = (atlas.crop((x, y, x + w, y + h)), glyph['shift'] + 1, glyph['offset'])

    def width(self, line):
        return sum(self.glyphs[char][1] for char in line)

    def wrap(self, words, width):
        rows = ['']
        for word in words.split():
            candidate = f'{rows[-1]} {word}'.strip()
            if self.width(candidate) <= width:
                rows[-1] = candidate
            else:
                rows.append(word)
        return rows

    def draw(self, image, words, x, y):
        for char in words:
            glyph, advance, offset = self.glyphs[char]
            if char != ' ':
                paste(image, glyph, x + offset, y)
            x += advance


def stylus(image, x, y, *, press=0):
    """Draw the stylus with its tip attached to the simulated input point."""
    x, y = round(x), round(y)
    d = ImageDraw.Draw(image)
    d.polygon(((x + 1, y + 4), (x + 38, y + 31), (x + 42, y + 39),
               (x + 9, y + 15)), fill='#170f22')
    d.polygon(((x + 3, y + 2), (x + 39, y + 24), (x + 43, y + 32),
               (x + 36, y + 35), (x + 6, y + 9)), fill='#514d65', outline='#20172c')
    d.line((x + 10, y + 6, x + 37, y + 24), fill='#9f95a8', width=2)
    d.polygon(((x, y), (x + 9, y + 4), (x + 6, y + 9)), fill='#dbd4e0', outline='#2a233c')
    if press:
        r = 3 + round(7 * press)
        d.arc((x - r, y - r, x + r, y + r), 170, 390, fill='#fef2ad', width=2)
