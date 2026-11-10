"""Native Mario Party DS overlays for the Fast Food Frenzy short."""

from functools import lru_cache

from PIL import Image, ImageDraw

from mpds_ui import crop, ds_text, resized, stamp
from party_reel import ShortsReel
from reel_art import NEAR, ROOT, SIZE, centered, paste, smooth, stylus


NATIVE = ROOT / 'assets/fast-food-native'
ROULETTE_SHEET = 'minigame-roulettes-2'
ONE_VS_THREE_CROPS = {
    'frame': (258, 1, 514, 193),
    'label': (340, 193, 431, 219),
    'players': (322, 397, 449, 429),
}


@lru_cache(maxsize=24)
def native(name):
    with Image.open(NATIVE / f'{name}.png') as source:
        return source.convert('RGBA')


@lru_cache(maxsize=3)
def roulette_art(part):
    art = crop(ROULETTE_SHEET, ONE_VS_THREE_CROPS[part], (0, 128, 128))
    if part != 'frame':
        art = art.crop(art.getbbox())
    return art


@lru_cache(maxsize=1)
def preview_window():
    mask = stamp('preview-border').getchannel('A')
    ImageDraw.floodfill(mask, (85, 68), 128)
    mask = mask.point(lambda alpha: 255 if alpha == 128 else 0)
    ImageDraw.Draw(mask).rectangle((0, 0, 29, 30), fill=0)
    return mask


class DinerLayout(ShortsReel):
    def draw_roulette(self, screen, title, age, lock_at, selected_row):
        y = 90 - 178 * (1 - smooth(age / .42))
        centered(screen, roulette_art('frame').resize(SIZE, NEAR), 120, y)
        centered(screen, roulette_art('label').resize((65, 18), NEAR), 120, y - 59)
        centered(screen, roulette_art('players').resize((110, 27), NEAR), 120, y + 60)

        opening = smooth((age - .46) / .24)
        if opening == 0:
            return
        slots = resized('roulette-slots', 172, 72)
        if opening < 1:
            crop_height = max(1, round(72 * opening))
            slots = slots.crop((0, 0, 172, crop_height))
        paste(screen, slots, 34, y - 36)
        if age < .70:
            return

        locked = age >= lock_at
        if locked:
            row = selected_row
        else:
            spin = min(1, (age - .70) / (lock_at - .70))
            row = (selected_row + int(18 * (1 - (1 - spin) ** 1.55)) - 18) % 4
        for index in range(4):
            line_y = y - 26 + 17 * index
            active = index == row
            if active:
                centered(screen, resized('roulette-selected', 168, 16), 120, line_y)
            revealed = active and locked
            ds_text(screen, title if revealed else '? ' * 12, 120,
                    line_y - (8 if revealed else 6), height=12 if revealed else 8,
                    color='#31220a' if active else '#e3cf97', middle=True)

    def game_rules(self, preview, team, solo, until_start):
        lower = native('rules-solo').resize(SIZE, NEAR).convert('RGB')
        upper = native('rules-upper-clean').copy()
        window = preview_window()
        upper.paste(preview.resize(window.size, NEAR), (44, 36), window)
        upper = upper.resize(SIZE, NEAR).convert('RGB')
        for who, x, y, height in ((solo, 193, 59, 26), (team[0], 169, 112, 24),
                                 (team[1], 214, 111, 24), (team[2], 196, 144, 23)):
            centered(upper, self.sprite(f'{who}-face', height), x, y)
        if 0 <= until_start < .34:
            approach = smooth((.34 - until_start) / .34)
            stylus(lower, 210 + 31 * (1 - approach), 170 + 17 * (1 - approach),
                   press=approach)
        return lower, upper


def banner(screen, name, age, duration):
    enter = smooth(age / .14)
    leave = smooth((duration - age) / .22)
    width = round((127 if name == 'start' else 143) * (.76 + .24 * enter))
    art = resized(name, width, round(width / 4)).copy()
    art.putalpha(art.getchannel('A').point(lambda a: round(a * leave)))
    centered(screen, art, 120, 89 - 7 * (1 - enter))


def result_badge(screen, age):
    art = stamp('win')
    width = round(44 * (.75 + .25 * smooth(age / .25)))
    centered(screen, art.resize((width, round(width * art.height / art.width)), NEAR), 120, 72)


def winner_name(screen, name, x, y):
    for dx, dy in ((-1, 0), (0, -1), (1, 0), (0, 1), (1, 1)):
        ds_text(screen, name, x + dx, y + dy, height=15, color='#291c0f', middle=True)
    ds_text(screen, name, x, y, height=15, color='#fbea81', middle=True)
