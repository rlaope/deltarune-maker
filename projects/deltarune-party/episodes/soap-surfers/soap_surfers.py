"""Four D-pad replays on the original two-screen Soap Surfers sink."""

from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations
from math import atan2, ceil, cos, exp, hypot, pi, sin
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from mpds_ui import ds_text, stamp as ds_stamp
from soap_skills import SKILLS, SkillRound
from study_cast import PLAYERS


TICK_RATE = 120
GO_TICK = 126
ROUND_TICKS = 30 * TICK_RATE
FINISH_HOLD = 52
WIN_DELAY = 126
RIM = 1.0
BAR_DIAMETER = .235
ACCELERATION, DRAG, SPEED_LIMIT = 2.15, .72, 1.18
RESTITUTION = .28
PAD_NAMES = ('R', 'DR', 'D', 'DL', 'L', 'UL', 'U', 'UR')
PAD = tuple((round(cos(pi * i / 4), 12), round(sin(pi * i / 4), 12)) for i in range(8))
SIZE = (240, 180)
ROOT = Path(__file__).resolve().parent
ART = ROOT / 'assets/mpds/soap'
ACTION = ROOT / 'assets/chapter5/action'
NEAR = Image.Resampling.NEAREST
JARONA_BLUE = {
    (255, 240, 111): (166, 243, 255),
    (254, 229, 2): (77, 204, 245),
    (223, 115, 50): (51, 120, 193),
    (115, 106, 60): (42, 76, 134),
    (113, 88, 68): (49, 73, 135),
}
BAR_COLORS = dict(zip(PLAYERS, ('blue', 'red', 'green', 'yellow')))

# These are steering intentions, in local seconds and normalized sink units.
# The D-pad follows them through acceleration, drag and collisions.
STEER_PLANS = {
    'queen': (
        (1.05, -.48, -.39), (2.60, -.10, -.23), (3.85, -.35, -.35), (4.90, -.42, -.38),
        (6.20, .40, -.50), (7.50, .62, -.18), (9.25, .50, -.40), (11.00, .63, -.42),
        (12.00, .51, -.59), (13.80, .41, -.38), (15.50, .55, -.35), (17.35, .74, -.42),
        (19.20, .72, -.42), (21.50, -.33, -.45), (24.00, -.54, .18), (29.00, -.50, -.32),
    ),
    'gerson': (
        (1.05, -.49, .33), (2.60, -.46, .27), (3.60, -.18, .31), (5.30, -.47, .18),
        (6.40, -.60, -.26), (7.45, -.40, -.19), (8.20, -.49, .08), (9.60, -.34, .45),
        (11.10, -.63, .17), (12.70, -.37, .33), (13.72, -.07, -.62), (14.40, -.24, .13),
        (15.70, -.22, .17),
        (17.30, -.48, .05), (19.50, -.51, .35), (21.10, -.30, .34), (22.95, -.37, -.26),
        (24.31, .21, .12), (24.50, -.31, -.10), (25.60, -.18, .23), (26.50, -.13, -.14),
        (27.55, .28, -.15),
        (28.55, .40, -.20), (30.60, -.19, .25),
    ),
    'flowery': (
        (1.05, .50, -.39), (2.50, .05, -.18), (3.50, .51, -.50), (5.15, .55, .12),
        (6.85, .32, -.30), (7.42, .32, -.25), (8.70, .28, -.23), (10.20, .32, .31),
        (11.90, .34, .29), (13.40, -.21, -.42), (14.85, -.04, -.14), (15.48, .44, -.49), (16.20, .27, -.29),
        (17.80, .24, -.20), (19.75, .30, -.40), (21.85, .16, .16), (23.65, .12, .21),
        (25.30, .41, .12), (26.50, .65, -.10), (28.50, .68, -.12), (30.50, .45, -.36),
    ),
    'ralsei': (
        (1.05, .49, .37), (2.70, .20, .28), (3.77, .18, .07), (4.68, .16, .49),
        (5.50, .40, .56), (6.75, .43, .28), (8.15, .39, .51), (10.30, .30, .43),
        (11.40, .11, .21), (12.45, .15, .21), (13.70, .57, .34), (15.80, .37, .54),
        (17.23, .29, -.35), (17.50, .21, .17), (18.55, .25, .17), (20.35, .63, .41),
        (20.62, .77, .50), (21.65, .58, .55),
        (23.55, .64, .54), (25.10, .43, .38), (27.60, .23, .48), (30.80, .21, .38),
    ),
}


@dataclass
class Rider:
    x: float
    y: float
    vx: float = 0
    vy: float = 0
    angle: float = pi / 2
    direction: int = -1
    fall_t: float | None = None
    place: int = 0
    hit_t: float | None = None
    hit_by: str | None = None
    near_rim: float = 0
    recovery: float = 0
    skill_hit_t: float | None = None
    bump_t: float | None = None
    bump_speed: float = 0

    @property
    def alive(self):
        return self.fall_t is None

    def snapshot(self):
        return dict(x=self.x, y=self.y, vx=self.vx, vy=self.vy, angle=self.angle, alive=self.alive,
                    direction=self.direction, fall_t=self.fall_t, fall_x=None if self.alive else self.x,
                    fall_y=None if self.alive else self.y, place=self.place, hit_t=self.hit_t, hit_by=self.hit_by,
                    skill_hit_t=self.skill_hit_t, bump_t=self.bump_t, bump_speed=self.bump_speed,
                    near_rim=self.near_rim)


def _steer(t, plan, rider):
    t += .17
    tx, ty = plan[-1][1:]
    dx = dy = 0
    for (a, x, y), (b, nx, ny) in zip(plan, plan[1:]):
        if t < b:
            u = min(1, max(0, (t - a) / (b - a)))
            tx, ty = x + (nx - x) * u, y + (ny - y) * u
            dx, dy = (nx - x) / (b - a), (ny - y) / (b - a)
            break
    ax = (tx - rider.x) * 4.2 + dx * .55 - rider.vx
    ay = (ty - rider.y) * 4.2 + dy * .55 - rider.vy
    return round(atan2(ay, ax) * 4 / pi) % 8 if hypot(ax, ay) > .13 else -1


def _move(rider, t):
    recovering = t < rider.recovery
    dx, dy = PAD[rider.direction] if rider.direction >= 0 and not recovering else (0, 0)
    damping = exp(-DRAG / TICK_RATE)
    rider.vx = (rider.vx + dx * ACCELERATION / TICK_RATE) * damping
    rider.vy = (rider.vy + dy * ACCELERATION / TICK_RATE) * damping
    speed = hypot(rider.vx, rider.vy)
    limit = 2.30 if recovering else SPEED_LIMIT
    if speed > limit:
        rider.vx *= limit / speed
        rider.vy *= limit / speed
    rider.x += rider.vx / TICK_RATE
    rider.y += rider.vy / TICK_RATE
    if speed > .12:
        rider.angle = atan2(rider.vy, rider.vx)


def _bump(first, second):
    dx, dy = second.x - first.x, second.y - first.y
    distance = hypot(dx, dy)
    if not 0 < distance < BAR_DIAMETER:
        return 0
    nx, ny = dx / distance, dy / distance
    separation = (BAR_DIAMETER - distance) / 2
    first.x -= nx * separation
    first.y -= ny * separation
    second.x += nx * separation
    second.y += ny * separation
    approach = (first.vx - second.vx) * nx + (first.vy - second.vy) * ny
    if approach > .03:
        impulse = approach * (1 + RESTITUTION) / 2
        first.vx -= nx * impulse
        first.vy -= ny * impulse
        second.vx += nx * impulse
        second.vy += ny * impulse
    return approach


def _run(duration, *, tape=None, contacts=True, skills=True):
    riders = {who: Rider(*STEER_PLANS[who][0][1:]) for who in PLAYERS}
    timeline, events, effects = [], [], []
    combat = SkillRound(TICK_RATE)
    finish_tick = resolve_tick = None
    winners = []

    def emit(t, kind, who, **fields):
        events.append(dict(t=t, type=kind, id=who, **fields))

    for tick in range(ceil(duration * TICK_RATE)):
        t = tick / TICK_RATE
        if tick == GO_TICK:
            emit(t, 'go', 'host')
        if tick >= GO_TICK and resolve_tick is None:
            active = [(who, rider) for who, rider in riders.items() if rider.alive]
            for who, rider in active:
                direction = rider.direction
                if tape is not None:
                    direction = tape[who].get(tick, direction)
                elif tick % 10 == 0:
                    direction = _steer(t, STEER_PLANS[who], rider)
                if direction != rider.direction:
                    rider.direction = direction
                    emit(t, 'steer', who, direction=direction, control=PAD_NAMES[direction] if direction >= 0 else None)
                _move(rider, t)
            if contacts:
                for (who, rider), (other, opponent) in combinations(active, 2):
                    speed = _bump(rider, opponent)
                    if speed > .15:
                        x, y = (rider.x + opponent.x) / 2, (rider.y + opponent.y) / 2
                        strength = min(1, speed / 1.2)
                        normal = (opponent.x - rider.x) / BAR_DIAMETER, (opponent.y - rider.y) / BAR_DIAMETER
                        for participant, source in ((rider, other), (opponent, who)):
                            participant.hit_t, participant.hit_by = t, source
                            participant.bump_t, participant.bump_speed = t, speed
                            if speed > .35:
                                participant.recovery = max(participant.recovery, t + .08 + .07 * strength)
                        emit(t, 'bump', who, other=other, speed=speed, strength=strength, x=x, y=y,
                             impulse=speed * (1 + RESTITUTION) / 2, normal=normal)
                        effects.append(dict(t=t, x=x, y=y, speed=speed, normal=normal))
            if skills:
                combat.step(t, tick, riders, emit)
            fallen = []
            for who, rider in active:
                radius = hypot(rider.x, rider.y)
                if radius > RIM:
                    fallen.append((who, rider))
                elif radius >= .90:
                    rider.near_rim = max(rider.near_rim, radius)
                elif radius < .82 and rider.near_rim:
                    emit(t, 'save', who, radius=rider.near_rim, x=rider.x, y=rider.y)
                    rider.near_rim = 0
            for who, rider in fallen:
                rider.fall_t, rider.place, rider.direction = t, len(active), -1
                by = rider.hit_by if rider.hit_t is not None and t - rider.hit_t < 1.0 else None
                emit(t, 'fall', who, by=by, x=rider.x, y=rider.y, radius=hypot(rider.x, rider.y), place=rider.place)
            remaining = [who for who, rider in active if rider.alive]
            expired = tick >= GO_TICK + ROUND_TICKS
            if len(remaining) <= 1 or expired:
                winners = remaining if len(remaining) < len(PLAYERS) else []
                for who in winners:
                    riders[who].place = 1
                resolve_tick = tick
        winner = winners[0] if len(winners) == 1 else None
        if resolve_tick is not None and tick == resolve_tick + FINISH_HOLD:
            finish_tick = tick
            emit(t, 'finish', winner, winners=winners.copy())
        if winner is not None and finish_tick is not None and tick == finish_tick + WIN_DELAY:
            emit(t, 'win', winner)
        phase = 'finish' if finish_tick is not None else 'settle' if resolve_tick is not None else 'play' if tick >= GO_TICK else 'ready'
        effects = [effect for effect in effects if t - effect['t'] < .26]
        timeline.append(dict(t=t, phase=phase, ring=RIM, sponge=None, winner=winner, winners=winners.copy(),
                             finish_t=None if finish_tick is None else finish_tick / TICK_RATE,
                             time_left=max(0, ceil(30 - max(0, (min(tick, resolve_tick or tick) - GO_TICK) / TICK_RATE))),
                             scores={who: rider.place for who, rider in riders.items()}, effects=effects.copy(),
                             players={who: rider.snapshot() for who, rider in riders.items()},
                             **combat.snapshot(t, riders)))
    return timeline, events


def simulate(fps, duration, mode='show'):
    """Sample fixed-tick physics, preserving the native 30-second limit."""
    if fps <= 0 or duration <= 0:
        raise ValueError('Soap Surfers requires a positive frame rate and duration')
    if mode == 'show':
        timeline, events = _run(duration)
    else:
        tape = {who: {} for who in PLAYERS}
        if mode in ('no-contact', 'no-skills'):
            for event in _run(duration)[1]:
                if event['type'] in ('steer', 'fall'):
                    tape[event['id']][round(event['t'] * TICK_RATE)] = event.get('direction', -1)
        elif mode != 'no-input':
            raise ValueError(f'Unknown Soap Surfers replay: {mode}')
        timeline, events = _run(duration, tape=tape, contacts=mode != 'no-contact', skills=mode == 'no-contact')
    frames = [dict(timeline[int(n * TICK_RATE / fps)], t=n / fps) for n in range(round(fps * duration))]
    return frames, events


@lru_cache(maxsize=42)
def _art(name):
    return Image.open(ART / f'{name}.png').convert('RGBA')


@lru_cache(maxsize=100)
def _action(name, height, facing='left'):
    with Image.open(ACTION / f'{name}.png') as image:
        art = image.convert('RGBA')
    art = art.crop(art.getbbox())
    if name == 'flowery-jarona-punch-0':
        data = [(*JARONA_BLUE.get(pixel[:3], pixel[:3]), pixel[3]) for pixel in art.get_flattened_data()]
        art.putdata(data)
    art = art.resize((max(1, round(art.width * height / art.height)), height), NEAR)
    return art.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if facing == 'right' else art


@lru_cache(maxsize=2)
def _fire_frame(index):
    sprite = _action(f'ralsei-fire-{index}', 18)
    alpha = Image.new('L', (sprite.width + 4, sprite.height + 4))
    alpha.paste(sprite.getchannel('A'), (2, 2))
    outline = Image.new('RGBA', alpha.size, '#b83b36')
    outline.putalpha(alpha.filter(ImageFilter.MaxFilter(3)))
    warm = Image.new('RGBA', alpha.size, '#f48348')
    warm.putalpha(alpha)
    core = Image.new('RGBA', alpha.size, '#fff0a8')
    core.putalpha(alpha.filter(ImageFilter.MinFilter(3)))
    return Image.alpha_composite(Image.alpha_composite(outline, warm), core)


@lru_cache(maxsize=8)
def _dash_ghost(facing, opacity):
    actor = _action('flowery-jarona-punch-0', 37, facing)
    ghost = Image.new('RGBA', actor.size, '#329bdb')
    ghost.putalpha(actor.getchannel('A').point(lambda a: round(a * opacity)))
    return ghost


@lru_cache(maxsize=3)
def _dash_petal(index):
    petal = _action(f'flowery-petal-{index}', 6 + index * 2)
    ink = Image.new('RGBA', petal.size, '#0080ff')
    ink.putalpha(petal.getchannel('A'))
    return ink


def _paste(image, layer, x, y):
    image.paste(layer, (round(x), round(y)), layer if layer.mode == 'RGBA' else None)


def _center(image, layer, x, y):
    _paste(image, layer, x - layer.width / 2, y - layer.height / 2)


def _screen_xy(x, y):
    return 120 + 115 * x, 96 + 79 * y


class SoapSurfers:
    """Native sink gameplay below the bathroom mirror and its reflections."""

    def __init__(self, sprite):
        self.sprite = sprite
        self.sink = _art('sink').resize(SIZE, NEAR).convert('RGB')
        self.mirror = _art('mirror').resize(SIZE, NEAR).convert('RGB')
        self.start = ds_stamp('start').resize((87, 22), NEAR)
        self.finish = ds_stamp('finish').resize((99, 25), NEAR)
        self.timer = _art('timer-ref').resize((37, 22), NEAR)

    @lru_cache(maxsize=90)
    def _soap(self, who, tilt):
        art = _art(f'soap-{BAR_COLORS[who]}')
        bar = art.resize((27, max(8, round(art.height * 27 / art.width))), NEAR)
        return bar.rotate(tilt, resample=NEAR, expand=True)

    @lru_cache(maxsize=100)
    def _body(self, who, facing, stride, tilt):
        height = {'queen': 31, 'gerson': 29, 'flowery': 34, 'ralsei': 28}[who]
        pose = f'{who}-{facing}-{stride}'
        if who == 'gerson' and facing == 'up':
            pose = f'gerson-down-{stride}'
        if who == 'flowery' and tilt:
            pose = 'flowery-panic-0'
        body = self.sprite(pose, height).convert('RGBA')
        return body.rotate(tilt, resample=NEAR, expand=True) if tilt else body

    @staticmethod
    def _facing(angle):
        return ('right', 'down', 'left', 'up')[round(angle / (pi / 2)) % 4]

    def _rider(self, image, who, player, t, cheer_age, cast):
        x, y = player['x'], player['y']
        fall = player['fall_t']
        age = None if fall is None else t - fall
        if age is not None and age >= .58:
            return
        angle = player['angle']
        if age is None:
            speed = hypot(player['vx'], player['vy'])
            tilt = 0
        else:
            speed = 0
            x += player['vx'] * age * .80
            y += player['vy'] * age * .55 + 2.7 * age * age
            tilt = -30 - round(age * 6) * 12
        sx, sy = _screen_xy(x, y)
        heading = round((-angle * 180 / pi + 90) / 15) * 15
        if age is not None:
            heading += tilt
        pose = self._facing(angle)
        stride = int(t * 8) % 4 if speed > .54 else 0
        lift = 0
        if cheer_age is not None:
            pose = 'laugh' if who == 'gerson' else 'down'
            stride = int(cheer_age * 8) % (3 if who == 'gerson' else 4)
            lift = 7 * abs(sin(cheer_age * 8))
        hit = player['skill_hit_t']
        if age is None and hit is not None and 0 <= t - hit < .28:
            tilt = round(23 * (1 - (t - hit) / .28)) * (-1 if player['vx'] > 0 else 1)
            lift = round(6 * sin(pi * (t - hit) / .28))
        bump = player['bump_t']
        if age is None and not tilt and bump is not None and player['bump_speed'] > .35:
            recoil = 1 - (t - bump) / .19
            if recoil > 0:
                sign = -1 if player['vx'] > 0 else 1
                tilt = sign * round(20 * min(1, player['bump_speed']) * recoil)
                heading += 15 * round(tilt / 15)
                lift = max(lift, round(4 * sin(pi * recoil)))
        bar = self._soap(who, heading)
        actor = self._body(who, pose, stride, tilt)
        if cast and age is None and not tilt:
            actor = self._cast_actor(cast, t)
            lift = 2 if cast['skill'] == 'jarona' else 0
        if age is not None:
            alpha = round(255 * max(0, 1 - age / .58))
            bar, actor = bar.copy(), actor.copy()
            for layer in (bar, actor):
                layer.putalpha(layer.getchannel('A').point(lambda p: p * alpha // 255))
        if age is None and speed > .64:
            self._wake(image, player, sx, sy, speed)
        _center(image, bar, sx, sy)
        _paste(image, actor, sx - actor.width / 2, sy - actor.height - 1 - lift)


    @staticmethod
    def _wake(image, player, sx, sy, speed):
        dx, dy = player['vx'] * 115, player['vy'] * 79
        length = hypot(dx, dy)
        dx, dy = dx / length, dy / length
        span = min(24, 12 + speed * 6)
        # Near the edge, the same wake gets brighter as the rider digs back in.
        edge = player['near_rim'] and player['x'] * player['vx'] + player['y'] * player['vy'] < 0
        ink = '#72b9cf' if edge else '#a0bfcb'
        draw = ImageDraw.Draw(image)
        for side in (-1, 1):
            x, y = sx + side * 5 * dy, sy - side * 5 * dx
            draw.line((x - 8 * dx, y - 8 * dy, x - span * dx, y - span * dy), fill=ink, width=2)
            draw.point((round(x - (span + 4) * dx), round(y - (span + 4) * dy)), fill='#f6fcff')

    def _cast_actor(self, cast, t):
        age = t - cast['at']
        charging = age < cast['windup']
        facing = 'right' if cos(cast['angle']) > 0 else 'left'
        skill = cast['skill']
        if skill == 'jarona':
            if charging:
                pose = min(4, int(age / cast['windup'] * 5))
                return _action(f'flowery-jarona-windup-{pose}', 38, facing)
            return _action('flowery-jarona-punch-0', 37, facing)
        if skill == 'hammer':
            pose = min(2, int(age / cast['windup'] * 3)) if charging else 3
            return _action(f'gerson-hammer-slam-{pose}', 37, facing)
        if skill == 'fire':
            return _action('ralsei-fire-cast', 31, facing)
        return self._body('queen', facing, 0, 0)

    @staticmethod
    def _telegraphs(image, game, t):
        draw = ImageDraw.Draw(image)
        for caster, cast in game['casts'].items():
            age = t - cast['at']
            if age >= cast['windup']:
                continue
            u = min(1, age / cast['windup'])
            skill = SKILLS[caster]
            x, y = cast['x'], cast['y']
            if skill.name == 'hammer':
                x += .18 * cos(cast['angle'])
                y += .18 * sin(cast['angle'])
                sx, sy = _screen_xy(x, y)
                for i in range(12):
                    a = pi * i / 6 + u * .22
                    px = sx + 47 * cos(a)
                    py = sy + 32 * sin(a)
                    draw.line((px, py, px + 4 * cos(a), py + 3 * sin(a)), fill='#c5aa73', width=2)
                continue
            ink = {'energy': '#4c88c2', 'fire': '#e66d45', 'jarona': '#3b7991'}[skill.name]
            dx, dy = cos(cast['angle']), sin(cast['angle'])
            for i in range(1, 10):
                distance = i / 9 * min(skill.reach, 1.05)
                px, py = _screen_xy(x + distance * dx, y + distance * dy)
                if hypot(x + distance * dx, y + distance * dy) < 1.01:
                    draw.rectangle((px - 2, py - 1, px + 2, py + 1), fill=ink)
            sx, sy = _screen_xy(x, y)
            if skill.name == 'energy' and u > .30:
                _center(image, _action('queen-attack', 9), sx + 12 * dx, sy + 7 * dy)
            if u > .71:
                width = 2 + round(4 * (u - .71) / .29)
                draw.line((sx - width, sy - 31, sx + width, sy - 31), fill='white', width=1)
                draw.line((sx, sy - 31 - width, sx, sy - 31 + width), fill='white', width=1)

    @staticmethod
    def _attacks(image, game, t):
        draw = ImageDraw.Draw(image)
        for shot in game['shots']:
            skill = shot['skill']
            sx, sy = _screen_xy(shot['x'], shot['y'])
            dx, dy = cos(shot['angle']), sin(shot['angle'])
            if skill == 'hammer':
                radius = shot['radius']
                draw.ellipse((sx - 115 * radius, sy - 79 * radius,
                              sx + 115 * radius, sy + 79 * radius),
                             outline='#a67245', width=3)
                draw.ellipse((sx - 115 * radius, sy - 79 * radius,
                              sx + 115 * radius, sy + 79 * radius),
                             outline='#fff1b1', width=1)
                if radius < .16:
                    head = _action('gerson-hammer-0', 18).rotate(round(t * 840) % 360, NEAR, expand=True)
                    _center(image, head, sx, sy - 9)
            elif skill == 'jarona':
                facing = 'right' if dx > 0 else 'left'
                for distance, opacity in ((.29, .22), (.18, .34)):
                    if shot['radius'] > distance:
                        ghost = _dash_ghost(facing, opacity)
                        _center(image, ghost, sx - dx * 115 * distance, sy - dy * 79 * distance - 22)
                for i in range(1, 4):
                    if shot['radius'] > i * .09:
                        petal = _dash_petal(i)
                        _center(image, petal, sx - dx * (8 + 11 * i), sy - dy * (8 + 7 * i) - 7 + (-1)**i * 4)
            else:
                sy -= 13
                if skill == 'fire':
                    span = min(35, 115 * shot['radius'])
                    angle = atan2(dy * 79, dx * 115)
                    fx, fy = cos(angle), sin(angle)
                    tail = (sx - fx * span, sy - fy * span, sx - fx * 4, sy - fy * 4)
                    draw.line(tail, fill='#bf4034', width=5)
                    draw.line(tail, fill='#f58145', width=2)
                    fire = _fire_frame(int(t * 15) % 2)
                    fire = fire.rotate(-angle * 180 / pi - 90, resample=NEAR, expand=True)
                    _center(image, fire, sx, sy)
                else:
                    span = 19
                    draw.line((sx - dx * span, sy - dy * span * .69,
                               sx + dx * 5, sy + dy * 4), fill='#315780', width=8)
                    beam = _action('queen-laser-beam', 5).resize((25, 5), NEAR)
                    angle = atan2(dy * 79, dx * 115) * 180 / pi
                    _center(image, beam.rotate(-angle, NEAR, expand=True), sx - 6 * dx, sy - 4 * dy)
        for impact in game['impacts']:
            age = t - impact['t']
            if not 0 <= age < .23:
                continue
            sx, sy = _screen_xy(impact['x'], impact['y'])
            offset = 7 + 32 * age
            ink = {'energy': '#96edff', 'fire': '#ffc179',
                   'jarona': '#7bd8e8', 'hammer': '#ffe5a5'}[impact['skill']]
            for i in range(5):
                a = i * 2 * pi / 5 + age
                dx, dy = cos(a), sin(a)
                draw.line((sx + dx * offset, sy - 8 + dy * offset,
                           sx + dx * (offset + 5), sy - 8 + dy * (offset + 5)), fill=ink, width=2)
            if age < .10:
                _center(image, ds_stamp('board-star').resize((14, 14), NEAR), sx, sy - 8)


    def _reflection(self, game, t):
        image = self.mirror.copy()
        layer = Image.new('RGBA', SIZE)
        for who, player in game['players'].items():
            if not player['alive']:
                continue
            x, y = 120 + 46 * player['x'], 87 + 19 * player['y']
            cast = game['casts'].get(who)
            silhouette = self._cast_actor(cast, t) if cast else self._body(who, self._facing(player['angle']), 0, 0)
            silhouette = silhouette.resize((max(2, silhouette.width // 2), silhouette.height // 2), NEAR)
            shadow = Image.new('RGBA', silhouette.size, '#444960')
            shadow.putalpha(silhouette.getchannel('A').point(lambda p: p // 5))
            _paste(layer, shadow, x - shadow.width / 2, y - shadow.height)
        for i, (x, y) in enumerate(((92, 104), (139, 117), (115, 129), (153, 98))):
            y -= (t * (8 + i) + i * 7) % 40
            x += 3 * sin(t * 1.8 + i)
            width = 5 + 2 * (i % 2)
            bubble = _art('bubble').resize((width, width), NEAR)
            bubble.putalpha(bubble.getchannel('A').point(lambda p: p * 3 // 5))
            _center(layer, bubble, x, y)
        _paste(image, layer, 0, 0)
        return image

    def _draw_timer(self, image, seconds):
        _paste(image, self.timer, 198, 3)
        draw = ImageDraw.Draw(image)
        draw.rectangle((202, 7, 230, 21), fill='#121521')
        for index, char in enumerate(f'{seconds:02d}'):
            glyph = ds_stamp(f'board-number-blue-{char}')
            _center(image, glyph.resize((12, 13), NEAR), 209 + 13 * index, 14)

    @staticmethod
    def _impact(image, game, t):
        draw = ImageDraw.Draw(image)
        for effect in game['effects']:
            age = t - effect['t']
            if not 0 <= age < .26:
                continue
            sx, sy = _screen_xy(effect['x'], effect['y'])
            force = min(1, effect['speed'])
            width = round(14 + 8 * force + age * 63)
            splash = _art('splash').resize((width, width), NEAR)
            splash.putalpha(splash.getchannel('A').point(lambda p: round(p * (1 - age / .26))))
            _center(image, splash, sx, sy)
            if age < .12:
                size = round(9 + 8 * force)
                flash = ds_stamp('board-star').resize((size, size), NEAR)
                _center(image, flash, sx, sy - 5)
            if force > .35:
                nx, ny = effect['normal']
                for side in (-1, 1):
                    vx, vy = side * ny, -side * nx
                    reach = 5 + (18 + 46 * age) * force
                    draw.line((sx + vx * (reach - 5), sy + vy * (reach - 5),
                               sx + vx * reach, sy + vy * reach), fill='#74b3c9', width=2)
        for player in game['players'].values():
            fall = player['fall_t']
            if fall is not None and 0 <= t - fall < .33:
                sx, sy = _screen_xy(player['fall_x'], player['fall_y'])
                age = t - fall
                width = round(18 + age * 56)
                splash = _art('splash').resize((width, width), NEAR)
                splash.putalpha(splash.getchannel('A').point(lambda p: round(p * (1 - age / .33))))
                _center(image, splash, sx, sy)

    def screens(self, frame):
        game, t = frame['soap'], frame['u']
        lower = self.sink.copy()
        cheer_age = None if game['finish_t'] is None else t - game['finish_t'] - WIN_DELAY / TICK_RATE
        self._telegraphs(lower, game, t)
        for who, player in sorted(game['players'].items(), key=lambda item: item[1]['y']):
            cheer = cheer_age if cheer_age is not None and cheer_age >= 0 and who in game['winners'] else None
            self._rider(lower, who, player, t, cheer, game['casts'].get(who))
        self._impact(lower, game, t)
        self._attacks(lower, game, t)
        if game['phase'] in ('play', 'settle'):
            self._draw_timer(lower, game['time_left'])
        elif game['phase'] == 'ready' and t >= .20:
            _center(lower, self.start, 120, 86)
        elif game['phase'] == 'finish':
            age = t - game['finish_t']
            if age < WIN_DELAY / TICK_RATE:
                _center(lower, self.finish, 120, 86)
            elif game['winner']:
                ds_text(lower, game['winner'].capitalize(), 120, 48, height=18, middle=True, outline='#32252c')
                _center(lower, ds_stamp('wins').resize((56, 19), NEAR), 120, 79)
            elif not game['winners']:
                _center(lower, ds_stamp('tie'), 120, 82)
        return lower, self._reflection(game, t)
