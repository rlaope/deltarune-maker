"""Compose the DS screens from the game's extracted HUD and instruction art."""

from functools import lru_cache
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ART = Path(__file__).resolve().parent / 'assets/mpds'
FONT = json.loads((ART / 'font.json').read_text())['glyphs']
NEAR = Image.Resampling.NEAREST
SIZE = (240, 180)
COLORS = ('#4386df', '#e46356', '#64b773', '#e1bf43')

SPRITES = {
    'coin': 'board-coin', 'star': 'board-star', 'hex-10': 'hex-10-coin',
    'results': 'results-heading', 'results-paper': 'results-card',
}
CROPS = {
    'turn-blue': ('misc-3', (24, 22, 200, 54), (153, 217, 234)),
    'turn-green': ('misc-3', (24, 64, 200, 96), (153, 217, 234)),
    'board-map-button': ('board-misc', (424, 275, 453, 307), (0, 128, 128)),
    'board-item-button': ('board-misc', (454, 275, 483, 307), (0, 128, 128)),
    'board-place': ('board-misc', (1, 486, 65, 509), (0, 128, 128)),
    'board-cancel': ('board-misc', (1, 461, 65, 484), (0, 128, 128)),
    'board-ok': ('board-misc', (1, 361, 65, 385), (0, 128, 128)),
    'board-hand': ('board-misc', (488, 168, 518, 189), (0, 0, 0)),
    'hit-button': ('minigame-roulettes-2', (796, 712, 861, 739), (0, 128, 128)),
    'roulette-slots': ('minigame-roulettes-2', (624, 633, 796, 705), (0, 128, 128)),
    'roulette-selected': ('minigame-roulettes-2', (624, 706, 792, 722), (0, 128, 128)),
    'roulette-players': ('minigame-roulettes-2', (66, 397, 191, 429), (0, 128, 128)),
    'rules': ('minigame-menu', (24, 262, 200, 285), (255, 0, 128)),
    'rule-paper': ('minigame-menu', (876, 498, 1108, 566), (255, 0, 128)),
    'control-paper': ('minigame-menu', (876, 570, 1108, 639), (255, 0, 128)),
    'practice-button': ('minigame-menu', (1066, 426, 1130, 450), (255, 0, 128)),
    'start-button': ('minigame-menu', (1066, 451, 1130, 475), (255, 0, 128)),
    'pad-control': ('minigame-menu', (99, 4, 134, 40), (255, 0, 128)),
    'instruction-strip': ('minigame-menu', (232, 8, 488, 38), (255, 0, 128)),
    'preview-border': ('minigame-menu', (886, 339, 1056, 476), (255, 0, 128)),
    'results-continue': ('results-2', (1, 426, 64, 448), (0, 128, 128)),
}


@lru_cache(maxsize=30)
def sheet(name):
    return Image.open(ART / 'raw' / f'{name}.png').convert('RGBA')


def crop(sheet_name, box, key=None):
    image = sheet(sheet_name).crop(box)
    if key:
        pixels = np.asarray(image).copy()
        pixels[(pixels[:, :, :3] == key).all(axis=2), 3] = 0
        return Image.fromarray(pixels)
    return image


@lru_cache(maxsize=110)
def stamp(name):
    if name in CROPS:
        image = crop(*CROPS[name])
        return image.crop(image.getbbox())
    return Image.open(ART / f'{SPRITES.get(name, name)}.png').convert('RGBA')


def paste(image, layer, x, y):
    image.paste(layer, (round(x), round(y)), layer)


def centered(image, layer, x, y):
    paste(image, layer, x - layer.width / 2, y - layer.height / 2)


@lru_cache(maxsize=180)
def resized(name, width, height):
    return stamp(name).resize((width, height), NEAR)


@lru_cache(maxsize=45)
def board_glyph(digit, kind):
    variant = f'board-number-{"gold" if kind == "coins" else "blue"}'
    glyph = stamp(f'{variant if kind != "die" else "dice"}-{digit}')
    return glyph.crop(glyph.getbbox())


@lru_cache(maxsize=128)
def letters(char):
    meta = FONT[str(ord(char))]
    x, y, w, h = (meta[key] for key in ('x', 'y', 'w', 'h'))
    return stamp('font').crop((x, y, x + w, y + h)), meta['top']


def ds_text(image, text, x, y, *, height=10, color=None, middle=False, outline=None):
    glyphs = []
    for char in text:
        if char == ' ':
            glyphs.append((None, max(3, height // 3), 0))
            continue
        glyph, top = letters(char)
        if color:
            mask = glyph.getchannel('R') if not outline else glyph.getchannel('A')
            glyph = Image.new('RGBA', glyph.size, color)
            glyph.putalpha(mask)
        width = max(1, round(glyph.width * height / 13))
        glyphs.append((glyph.resize((width, max(1, round(glyph.height * height / 13))), NEAR), width + 1, round(top * height / 13)))
    if middle:
        x -= sum(width for _, width, _ in glyphs) / 2
    for glyph, width, top in glyphs:
        if glyph:
            if outline:
                shadow = Image.new('RGBA', glyph.size, outline)
                shadow.putalpha(glyph.getchannel('A'))
                for ox, oy in ((-1, 0), (0, -1), (1, 0), (0, 1)):
                    paste(image, shadow, x + ox, y + oy + top)
            paste(image, glyph, x, y + top)
        x += width


def number(image, value, x, y, *, height, kind='die'):
    raw = [board_glyph(c, kind) for c in str(value)]
    digits = [glyph.resize((max(1, round(glyph.width * height / glyph.height)), height), NEAR) for glyph in raw]
    x -= sum(glyph.width for glyph in digits) / 2
    for glyph in digits:
        paste(image, glyph, x, y)
        x += glyph.width


def checkered(colors):
    canvas = Image.new('RGB', SIZE, colors[0])
    draw = ImageDraw.Draw(canvas)
    for y in range(0, SIZE[1], 15):
        for x in range(0, SIZE[0], 15):
            if (x // 15 + y // 15) % 2:
                draw.rectangle((x, y, x + 14, y + 14), fill=colors[1])
    return canvas
