"""Four D-pad replays on the original two-screen Soap Surfers sink."""

from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations
from math import atan2, ceil, cos, exp, hypot, pi, sin
from pathlib import Path

from PIL import Image, ImageDraw

from mpds_ui import ds_text, stamp as ds_stamp
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
ART = Path(__file__).resolve().parent / 'assets/mpds/soap'
NEAR = Image.Resampling.NEAREST
BAR_COLORS = dict(zip(PLAYERS, ('blue', 'red', 'green', 'yellow')))

# These are steering intentions, in local seconds and normalized sink units.
# The D-pad follows them through acceleration, drag and collisions.
STEER_PLANS = {
    'queen': (
        (1.05, -.48, -.39), (2.60, -.05, -.21), (3.10, .48, .06), (4.20, -.38, -.34),
        (5.20, -.25, -.54), (7.00, 1.14, -.54),
    ),
    'gerson': (
        (1.05, -.49, .33), (2.60, -.46, .27), (3.50, -.17, .32), (4.40, -.25, .15),
        (5.90, -.40, .28), (7.00, -.24, .17), (9.20, -.20, .18), (11.50, -.13, .12),
        (12.80, .22, .02), (14.20, .57, .24), (15.05, .57, .24), (16.35, .60, .20),
        (16.85, .54, .57), (18.35, .02, -.12),
    ),
    'flowery': (
        (1.05, .50, -.39), (2.50, .05, -.18), (3.50, .60, -.55), (4.30, .45, .02),
        (5.20, .50, -.49), (6.05, .67, -.48), (6.60, .43, -.25), (7.50, .32, .25),
        (8.75, .30, .28), (9.70, -.15, .28), (10.75, -.18, 1.08), (11.30, .26, .48),
        (12.20, -.45, -.37), (14.00, -.17, .05), (14.85, -.17, .05), (16.15, .44, .37),
        (17.10, 1.21, .39),
    ),
    'ralsei': (
        (1.05, .49, .37), (2.70, .20, .28), (3.65, .35, .37), (4.65, .72, .60),
        (5.30, .42, .32), (6.40, .07, .38), (7.50, -.34, .43), (8.90, -.24, .48),
        (10.40, -.18, .81), (11.50, -.13, .81), (13.70, .02, .21), (16.20, -.34, .16),
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

    @property
    def alive(self):
        return self.fall_t is None

    def snapshot(self):
        return dict(x=self.x, y=self.y, vx=self.vx, vy=self.vy, angle=self.angle, alive=self.alive,
                    direction=self.direction, fall_t=self.fall_t, fall_x=None if self.alive else self.x,
                    fall_y=None if self.alive else self.y, place=self.place, hit_t=self.hit_t, hit_by=self.hit_by)


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


def _move(rider):
    dx, dy = PAD[rider.direction] if rider.direction >= 0 else (0, 0)
    damping = exp(-DRAG / TICK_RATE)
    rider.vx = (rider.vx + dx * ACCELERATION / TICK_RATE) * damping
    rider.vy = (rider.vy + dy * ACCELERATION / TICK_RATE) * damping
    speed = hypot(rider.vx, rider.vy)
    if speed > SPEED_LIMIT:
        rider.vx *= SPEED_LIMIT / speed
        rider.vy *= SPEED_LIMIT / speed
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


def _run(duration, *, tape=None, contacts=True):
    riders = {who: Rider(*STEER_PLANS[who][0][1:]) for who in PLAYERS}
    timeline, events, effects = [], [], []
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
                _move(rider)
            if contacts:
                for (who, rider), (other, opponent) in combinations(active, 2):
                    speed = _bump(rider, opponent)
                    if speed > .15:
                        x, y = (rider.x + opponent.x) / 2, (rider.y + opponent.y) / 2
                        rider.hit_t, rider.hit_by = t, other
                        opponent.hit_t, opponent.hit_by = t, who
                        emit(t, 'bump', who, other=other, speed=speed, strength=min(1, speed / 1.2), x=x, y=y)
                        effects.append(dict(t=t, x=x, y=y, speed=speed))
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
                             players={who: rider.snapshot() for who, rider in riders.items()}))
    return timeline, events


def simulate(fps, duration, mode='show'):
    """Sample fixed-tick physics, preserving the native 30-second limit."""
    if fps <= 0 or duration <= 0:
        raise ValueError('Soap Surfers requires a positive frame rate and duration')
    if mode == 'show':
        timeline, events = _run(duration)
    else:
        tape = {who: {} for who in PLAYERS}
        if mode == 'no-contact':
            for event in _run(duration)[1]:
                if event['type'] in ('steer', 'fall'):
                    tape[event['id']][round(event['t'] * TICK_RATE)] = event.get('direction', -1)
        elif mode != 'no-input':
            raise ValueError(f'Unknown Soap Surfers replay: {mode}')
        timeline, events = _run(duration, tape=tape, contacts=mode != 'no-contact')
    frames = [dict(timeline[int(n * TICK_RATE / fps)], t=n / fps) for n in range(round(fps * duration))]
    return frames, events


@lru_cache(maxsize=42)
def _art(name):
    return Image.open(ART / f'{name}.png').convert('RGBA')


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

    def _rider(self, image, who, player, t, cheer_age):
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
        bar = self._soap(who, heading)
        pose = self._facing(angle)
        stride = int(t * 8) % 4 if speed > .54 else 0
        lift = 0
        if cheer_age is not None:
            pose = 'laugh' if who == 'gerson' else 'down'
            stride = int(cheer_age * 8) % (3 if who == 'gerson' else 4)
            lift = 7 * abs(sin(cheer_age * 8))
        actor = self._body(who, pose, stride, tilt)
        if age is not None:
            alpha = round(255 * max(0, 1 - age / .58))
            bar, actor = bar.copy(), actor.copy()
            for layer in (bar, actor):
                layer.putalpha(layer.getchannel('A').point(lambda p: p * alpha // 255))
        _center(image, bar, sx, sy)
        _paste(image, actor, sx - actor.width / 2, sy - actor.height - 1 - lift)

    def _reflection(self, game, t):
        image = self.mirror.copy()
        layer = Image.new('RGBA', SIZE)
        for who, player in game['players'].items():
            if not player['alive']:
                continue
            x, y = 120 + 46 * player['x'], 87 + 19 * player['y']
            silhouette = self._body(who, self._facing(player['angle']), 0, 0)
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
        for effect in game['effects']:
            age = t - effect['t']
            if not 0 <= age < .26:
                continue
            sx, sy = _screen_xy(effect['x'], effect['y'])
            width = round(17 + age * 63)
            splash = _art('splash').resize((width, width), NEAR)
            splash.putalpha(splash.getchannel('A').point(lambda p: round(p * (1 - age / .26))))
            _center(image, splash, sx, sy)
            if age < .12:
                flash = ds_stamp('board-star').resize((13, 13), NEAR)
                _center(image, flash, sx, sy - 5)
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
        for who, player in sorted(game['players'].items(), key=lambda item: item[1]['y']):
            cheer = cheer_age if cheer_age is not None and cheer_age >= 0 and who in game['winners'] else None
            self._rider(lower, who, player, t, cheer)
        self._impact(lower, game, t)
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
