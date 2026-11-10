"""Green's covered menus on the Second Diner's lower DS screen."""

from functools import lru_cache
from math import pi, sin

from PIL import Image, ImageDraw

from mpds_ui import ds_text, number, resized
from reel_art import NEAR, SIZE, centered, mix, paste, smooth


FOOD_OPEN = .66
FOOD_FOCUS = (.99, 1.65, 2.40, 3.10)
FOOD_LOCK = 3.65
FOOD_REVEAL = 4.20
FOOD_CLOSE = 5.45
FOOD_X = (45, 120, 195)
MENU_SIZE = (47, 71)


@lru_cache(maxsize=2)
def menu_face(opened):
    card = Image.new('RGBA', MENU_SIZE)
    draw = ImageDraw.Draw(card)
    draw.rectangle((2, 2, 46, 70), fill='#20362a')
    draw.rectangle((1, 1, 45, 68), fill='#e9d19c', outline='#334338')
    draw.rectangle((0, 0, 43, 67), fill='#ebd9af' if opened else '#286448', outline='#20362a')
    draw.rectangle((1, 1, 5, 66), fill='#213f30')
    draw.rectangle((8, 6, 38, 61), outline='#b7884a' if opened else '#c6ac68')
    if not opened:
        draw.line((12, 25, 34, 25), fill='#c6ac68')
        draw.line((12, 42, 34, 42), fill='#c6ac68')
        ds_text(card, 'MENU', 23, 28, height=10, color='#fff3bd', middle=True)
    return card


def opening_menu(age, coins):
    turn = smooth((age - (FOOD_REVEAL - .26)) / .26)
    front = turn >= .5
    card = menu_face(front)
    if age >= FOOD_REVEAL:
        card = card.copy()
        centered(card, resized('coin', 17, 18), 23, 21)
        centered(card, resized('board-plus', 10, 12), 13, 45)
        number(card, coins, 27, 35, height=20, kind='coins')
    width = max(2, round(card.width * abs(1 - 2 * turn)))
    return card if width == card.width else card.resize((width, card.height), NEAR)


def focus(age, selected):
    active = 0
    cursor = FOOD_X[active]
    for start, index in zip(FOOD_FOCUS, (0, 1, 2, selected), strict=True):
        if age < start:
            break
        cursor = mix(FOOD_X[active], FOOD_X[index], smooth((age - start) / .21))
        active = index
    return active, cursor


def draw_food_event(screen, age, options, selected):
    """Mutate the 240×180 lower DS screen, from menu open through payout reveal."""
    if not FOOD_OPEN <= age < FOOD_CLOSE:
        return

    selected_index = [option['id'] for option in options].index(selected)
    active, cursor_x = focus(age, selected_index)
    locked = age >= FOOD_LOCK
    paper = Image.new('RGBA', SIZE)
    paste(paper, resized('rule-paper', 226, 109), 7, 43)
    paste(paper, resized('instruction-strip', 226, 24), 7, 22)
    ds_text(paper, 'Pick a menu!', 120, 26, height=14, color='#fff5dc', middle=True)

    for index, (x, option) in enumerate(zip(FOOD_X, options, strict=True)):
        current = index == active
        is_choice = locked and index == selected_index
        press = (age - FOOD_LOCK) / .29
        hop = 6 * sin(pi * press) if is_choice and 0 <= press <= 1 else 0
        card = opening_menu(age, option['coins']) if is_choice else menu_face(False)
        centered(paper, card, x, 94 - hop)
        if current:
            centered(paper, resized('roulette-selected', 40, 4), x, 138)

    if FOOD_FOCUS[0] <= age < FOOD_LOCK + .24:
        press = 1 - abs(age - FOOD_LOCK) / .15
        inset = 5 * max(0, press)
        paste(paper, resized('item-select-hand', 25, 22), cursor_x - 25, 43 + inset)
    if age < FOOD_LOCK + .17:
        press = 2 if locked else 0
        paste(paper, resized('item-select-ok', 61, 23), 179 + press, 153 + press)

    enter = smooth((age - FOOD_OPEN) / .26)
    leave = smooth((FOOD_CLOSE - age) / .24)
    if enter < 1 or leave < 1:
        opacity = min(enter, leave)
        paper.putalpha(paper.getchannel('A').point(lambda a: round(a * opacity)))
    paste(screen, paper, 0, 19 * (1 - enter) + 10 * (1 - leave))
