"""The Flower Castle toll event, staged in the board's world coordinates."""

from functools import lru_cache
from math import pi, sin

from PIL import Image, ImageDraw

from mpds_ui import ds_text, resized
from party_board import Pose
from reel_art import CHAPTER5, NEAR, centered, point, smooth

GUEST_ENTER = 5.60
AQUA_ENTER = 5.89
WINDUP = 10.76
THROW = 11.42
STARTLE = 11.46
DODGE = 11.52
DODGE_TIME = .19
RECOVER = 13.47
COIN_DROP, COIN_RECEIVE, EVENT_END = 16.15, 17.20, 18.50
AQUA_EXIT = 17.60

AQUA_SPOT = (-51, 1)
SETH_SPOT = (47, 1)
KNIFE_ORIGIN = (-38, -18)
KNIFE_SPEED = 134
KNIFE_TICKS = 120
ART = CHAPTER5 / 'action'


def _world(landing, offset):
    return landing[0] + offset[0], landing[1] + offset[1]


def _ralsei_offset(t, dodges):
    if not dodges:
        return 0, 0
    leap = smooth((t - DODGE) / DODGE_TIME) - smooth((t - RECOVER) / .48)
    return -3 * leap, 35 * leap


def knife_tip(t):
    """Leading pixel of the knife, relative to the question-mark space."""
    return KNIFE_ORIGIN[0] + KNIFE_SPEED * (t - THROW), KNIFE_ORIGIN[1]


def knife_contact(*, dodges=True):
    """Resolve the first body touched along the blade's actual travel."""
    for tick in range(1, KNIFE_TICKS + 1):
        t = THROW + tick / KNIFE_TICKS
        x0, _ = knife_tip(t - 1 / KNIFE_TICKS)
        x1, y = knife_tip(t)
        targets = (
            ('ralsei', _ralsei_offset(t, dodges), 8, 34),
            ('seth', SETH_SPOT, 10, 34),
        )
        for who, (bx, by), half_width, height in targets:
            if x0 <= bx + half_width and x1 >= bx - half_width and by - height <= y <= by - 6:
                return dict(t=round(t, 6), target=who, tip=(round(x1, 3), y),
                            body=(round(bx, 3), round(by, 3)))
    raise RuntimeError('Aqua’s throw crossed the board without reaching a body')


CONTACT = knife_contact()
HIT = CONTACT['t']
FALL = round(HIT + .76, 6)
FALL_END = round(FALL + .42, 6)

EVENT_DIALOGUE = (
    dict(speaker='ralsei', start=5.90, end=7.48, text="All right... who's there?",
         portrait='ralsei-worried-face'),
    dict(speaker='seth', start=8.47, end=9.79, text='Ten coins. Castle toll.'),
    dict(speaker='aqua', start=10.08, end=11.40, text='Okay. Catch!'),
    dict(speaker='ralsei', start=STARTLE, end=12.05, text='Whoa!',
         portrait='ralsei-surprised-face'),
    dict(speaker='seth', start=HIT + .12, end=HIT + .84, text='Not ME!'),
    dict(speaker='aqua', start=14.47, end=15.79, text='Uh... hazard pay?'),
)


def _walk(t, start, end, a, b):
    return point(a, b, smooth((t - start) / (end - start)))


def event_poses(poses, t, landing):
    """Add the two guests and choreograph Ralsei without changing board rules."""
    if not GUEST_ENTER <= t < EVENT_END:
        return poses

    if GUEST_ENTER <= t < HIT + .15:
        stride = 0
        if t < 8.30:
            if t < 7.29:
                offset = _walk(t, GUEST_ENTER, 7.29, (-140, 9), (-43, -21))
            elif t < 7.99:
                offset = _walk(t, 7.29, 7.99, (-43, -21), (29, -21))
            else:
                offset = _walk(t, 7.99, 8.30, (29, -21), SETH_SPOT)
            stride = int((t - GUEST_ENTER) * 12) % 4
            facing = 'right' if t < 7.99 else 'down'
        else:
            offset = SETH_SPOT
            facing = 'left'
        poses['seth'] = Pose(*_world(landing, offset), facing, stride,
                             sprite='seth-shock' if t >= HIT else None)

    if t >= AQUA_ENTER:
        facing, stride, lift, sprite_name = 'right', 0, 0, None
        if t < 7.48:
            offset = _walk(t, AQUA_ENTER, 7.48, (-145, 16), AQUA_SPOT)
            stride = int((t - AQUA_ENTER) * 12) % 4
        elif t >= AQUA_EXIT:
            offset = _walk(t, AQUA_EXIT, EVENT_END, AQUA_SPOT, (-145, 16))
            facing, stride = 'left', int((t - AQUA_EXIT) * 12) % 4
        else:
            offset = AQUA_SPOT
            if THROW <= t < THROW + .20:
                lift = 4 * sin(pi * (t - THROW) / .20)
                sprite_name = 'aqua-throw'
            elif FALL <= t < 14.47:
                glance = smooth((t - FALL) / .31) - smooth((t - 14.16) / .31)
                offset = AQUA_SPOT[0] + 8 * glance, AQUA_SPOT[1] + 3 * glance
                facing = 'down'
        poses['aqua'] = Pose(*_world(landing, offset), facing, stride, lift, sprite_name)

    if t < RECOVER + .48:
        offset = _ralsei_offset(t, True)
        if STARTLE <= t < DODGE + DODGE_TIME:
            age = (t - DODGE) / DODGE_TIME
            hop = 5 * sin(pi * max(0, age))
            poses['ralsei'] = Pose(*_world(landing, offset), 'left', lift=hop, sprite='ralsei-startled-left')
        elif t >= DODGE + DODGE_TIME:
            stride = int((t - RECOVER) * 12) % 4 if t >= RECOVER else 0
            facing = 'up' if t >= RECOVER else 'right'
            poses['ralsei'] = Pose(*_world(landing, offset), facing, stride)
        elif t >= AQUA_ENTER:
            poses['ralsei'] = Pose(*landing, 'left')
    elif t < COIN_DROP:
        poses['ralsei'] = Pose(*landing, 'left')

    return poses


@lru_cache(maxsize=12)
def _native(name):
    with Image.open(ART / f'{name}.png') as source:
        sprite = source.convert('RGBA')
    return sprite.crop(sprite.getbbox())


def _draw_knife(panel, t, x, y):
    dx, dy = knife_tip(t)
    tip_x, tip_y = x + dx, y + dy
    draw = ImageDraw.Draw(panel)
    flight = KNIFE_SPEED * (t - THROW)
    if flight > 20:
        tail = min(28, flight)
        draw.line((tip_x - tail, tip_y, tip_x - 10, tip_y), fill='#47c4bd', width=1)
        draw.line((tip_x - tail / 2, tip_y, tip_x - 8, tip_y), fill='#a5f9eb', width=1)
    blade = _native('aqua-knife' if int((t - THROW) * 24) % 2 == 0 else 'aqua-knife-1')
    shown = min(blade.width, 7 + round(flight))
    blade = blade.crop((blade.width - shown, 0, blade.width, blade.height))
    centered(panel, blade, tip_x - shown / 2 + 1, tip_y)


def _draw_tell(panel, t, x, y):
    age = t - WINDUP
    frame = 0 if t < WINDUP + .14 else 1 if t < THROW - .12 else 2
    knife = _native(f'aqua-ready-{frame}').transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    knife = knife.resize((round(knife.width * .63), round(knife.height * .63)), NEAR)
    cx, cy = x + AQUA_SPOT[0] + 10, y - 19 - 6 * smooth(age / .22)
    centered(panel, knife, cx, cy)
    if .20 <= age < .44:
        centered(panel, resized('star', 5, 5), cx + 6, cy + 1)


def _draw_hit(panel, age, x, y):
    dx, dy = CONTACT['tip']
    cx, cy = x + dx, y + dy
    effect = _native(f'aqua-knife-break-{min(3, int(age * 19))}')
    centered(panel, effect.resize((round(effect.width * .76), round(effect.height * .76)), NEAR), cx, cy)


def _draw_fall(panel, t, x, y):
    age = t - HIT
    if t < FALL:
        # The contact pushes Seth toward the foreground rail before gravity takes over.
        u = (age - .15) / (FALL - HIT - .15)
        dx = SETH_SPOT[0] + 25 * smooth(u)
        foot = SETH_SPOT[1] + 51 * u - 11 * sin(pi * u)
    else:
        u = (t - FALL) / (FALL_END - FALL)
        dx = SETH_SPOT[0] + 25 + 7 * u
        foot = SETH_SPOT[1] + 51 + 51 * u * u
    sprite = _native(f'seth-fall-{min(4, int((age - .15) * 8))}')
    sprite = sprite.resize((max(1, round(sprite.width * 36 / sprite.height)), 36), NEAR)
    if t < FALL:
        draw = ImageDraw.Draw(panel)
        draw.ellipse((x + dx - 6, y + foot - 2, x + dx + 6, y + foot + 2), fill='#2a1520')
    center_y = y + foot - 18
    if t >= FALL:
        visible_height = max(0, min(sprite.height, round(157 - center_y + sprite.height / 2)))
        if visible_height:
            sprite = sprite.crop((0, 0, sprite.width, visible_height))
            center_y += (visible_height - 36) / 2
        else:
            return
    centered(panel, sprite, x + dx, center_y)


def draw_action(panel, camera, t, landing):
    """Overlay the throw, impact and fall on the board surface."""
    x, y = landing[0] - camera, landing[1]
    if WINDUP <= t < THROW:
        _draw_tell(panel, t, x, y)
    if THROW <= t < HIT:
        _draw_knife(panel, t, x, y)
    if STARTLE <= t < STARTLE + .34:
        offset = _ralsei_offset(t, True)
        ds_text(panel, '!', x + offset[0], y + offset[1] - 54, height=14,
                middle=True, outline='#2c2440')
    if HIT + .15 <= t < FALL_END:
        _draw_fall(panel, t, x, y)
    if HIT <= t < HIT + .23:
        _draw_hit(panel, t - HIT, x, y)


def action_events():
    """Expose the same action timings and contact witness to the mix and QA."""
    steps = ((6.27, 'seth'), (6.60, 'seth'), (6.73, 'aqua'), (7.06, 'aqua'),
             (7.60, 'seth'), (7.93, 'seth'), (17.94, 'aqua'))
    return [
        dict(t=GUEST_ENTER, type='board_event', action='guests_enter', guests=['seth', 'aqua'],
             id='seth', edge='left'),
        dict(t=WINDUP, type='board_knife', action='windup', id='aqua'),
        dict(t=THROW, type='board_knife', action='throw', id='aqua', origin=KNIFE_ORIGIN),
        dict(t=DODGE, type='board_knife', action='dodge', id='ralsei', end=round(DODGE + DODGE_TIME, 2)),
        dict(t=HIT, type='board_knife', action='hit', id='seth', source='aqua',
             tip=CONTACT['tip'], body=CONTACT['body']),
        dict(t=FALL, type='board_knife', action='fall', id='seth', edge='foreground'),
        dict(t=EVENT_END, type='board_event', action='guests_leave', guests=['seth', 'aqua'], id='aqua'),
        *(dict(t=time, type='guest_step', id=who) for time, who in steps),
    ]
