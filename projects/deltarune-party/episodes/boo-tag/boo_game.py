"""Play the 30-second Boo Tag replay on the original DS chest camera."""

from dataclasses import dataclass
from functools import lru_cache
from math import ceil, cos, hypot, pi, sin

from PIL import Image, ImageDraw

from boo_chase import Chase, INITIAL_ENTRY, START, gap

from reel_art import NEAR, ROOT, SIZE, centered, mix, paste, smooth

PLAYERS = ('kris', 'susie', 'ralsei', 'gerson')
HEIGHTS = (23, 27, 23, 23)
COLORS = ('blue', 'red', 'green', 'yellow')
NATIVE = ROOT / 'assets/boo-native'
READY, LIMIT = 2.75, 30
GO, FINISH = READY, READY + LIMIT
RUNOUT = 1.65
TAG_RADIUS = 8.25
TAG_LOCK = .65
SPAWN_LOCK = .38
BACK_TAG_LOCK = 1.15
WORLD_FPS = 60

# Convex ground footprints in the settled cartridge camera, at DS layout scale.
TREASURE = (
    ('upper ingot', ((69, 76), (83, 53), (97, 47), (99, 57), (85, 84), (75, 87))),
    ('bowl', ((121, 53), (129, 45), (146, 46), (157, 54), (155, 64), (146, 70), (130, 69), (121, 63))),
    ('cup', ((42, 107), (48, 102), (56, 102), (62, 108), (60, 116), (52, 120), (44, 116))),
    ('lower ingot', ((61, 130), (113, 130), (114, 147), (60, 147))),
    ('sword', ((172, 70), (192, 63), (213, 63), (225, 73), (224, 77), (174, 78))),
    ('right ingot', ((188, 123), (198, 116), (232, 145), (234, 154), (225, 162), (188, 133))),
    ('gem', ((148, 134), (155, 130), (163, 133), (164, 141), (158, 145), (149, 141))),
)
ENTRY = INITIAL_ENTRY
INITIAL_FACING = ('right', 'left', 'up', 'up')


@dataclass(frozen=True)
class Frame:
    positions: tuple
    directions: tuple
    strides: tuple
    owners: tuple
    score: tuple
    phasing: tuple


def inside(xy, polygon):
    x, y = xy
    sign = None
    for (x0, y0), (x1, y1) in zip(polygon, (*polygon[1:], polygon[0])):
        side = (x1 - x0) * (y - y0) - (y1 - y0) * (x - x0)
        if abs(side) < .0001:
            continue
        if sign is not None and (side > 0) != sign:
            return False
        sign = side > 0
    return True


def in_treasure(xy):
    return next((i for i, (_, polygon) in enumerate(TREASURE) if inside(xy, polygon)), None)


def direction(delta, previous):
    dx, dy = delta
    if hypot(dx, dy) < .035:
        return previous
    if abs(dx) >= abs(dy):
        return 'right' if dx > 0 else 'left'
    return 'down' if dy > 0 else 'up'


def move_to(position, desired, can_phase, distance):
    """Collide with the exact treasure silhouettes and slide along them."""
    x, y = position
    dx, dy = desired[0] - x, desired[1] - y
    amount = min(1, distance / max(.0001, hypot(dx, dy)))
    yn = max(29, min(158, y + dy * amount))
    xn = max(27 - (yn - 29) * .108, min(230, x + dx * amount))
    if can_phase or in_treasure((xn, yn)) is None:
        return xn, yn
    if in_treasure((xn, y)) is None:
        return xn, y
    if in_treasure((x, yn)) is None:
        return x, yn
    return position


def simulate(fps=WORLD_FPS):
    """Sample the same fixed-step match at the requested output frame rate."""
    frames, events, winner, scores = _simulate_match()
    if fps != WORLD_FPS:
        frames = [frames[round(index * WORLD_FPS / fps)] for index in range(LIMIT * fps + 1)]
    return frames, events, winner, scores


def _simulate_match():
    fps = WORLD_FPS
    count = LIMIT * fps
    owners = [None, None]
    touched = [-fps, -fps]
    positions = START
    velocity = ((0., 0.),) * 4
    steering = Chase(TREASURE, lambda q: in_treasure(q) is not None, fps)
    last_sources = [None, None]
    stage = 0
    adopted = False
    directions = INITIAL_FACING
    distance = (0.,) * 4
    totals = [0] * 4
    phasing = (None,) * 4
    events = [dict(t=GO, type='go')]
    frames = [Frame(positions, directions, distance, tuple(owners), tuple(totals), phasing)]

    def event(kind, i, **detail):
        events.append(dict(t=round(GO + i / fps, 6), type=kind, **detail))

    for i in range(1, count + 1):
        for owner in owners:
            if owner is not None:
                totals[owner] += 1
        previous = positions
        def report(kind, who, **detail):
            for key in ('target', 'threat'):
                if key in detail:
                    detail[key] = PLAYERS[detail[key]]
            if detail.get('cover') is not None:
                detail['cover'] = TREASURE[detail['cover']][0]
            if 'gap' in detail:
                detail['gap'] = round(detail['gap'], 2)
            event(kind, i, id=PLAYERS[who], **detail)

        protected = [last_sources[ghost] if i - touched[ghost] < round(BACK_TAG_LOCK * fps) else None
                     for ghost in range(2)]
        elapsed = i / fps
        offer = not adopted and elapsed >= 12.4
        if not adopted and owners[0] == 2 and elapsed >= 13.15:
            adopted = True
            event('adopt_boo', i, ghost=0, id='ralsei')
        goals = steering.steer(i, positions, velocity, owners, protected, stage, adopted, offer, report)
        positions = tuple(move_to(pos, goal, who in owners, speed / fps)
                          for who, (pos, (goal, speed)) in enumerate(zip(positions, goals)))
        deltas = tuple((xn - x, yn - y) for (x, y), (xn, yn) in zip(previous, positions))
        directions = tuple(direction(delta, face) for delta, face in zip(deltas, directions))
        distance = tuple(total + hypot(*delta) for total, delta in zip(distance, deltas))
        velocity = tuple((dx * fps, dy * fps) for dx, dy in deltas)

        for ghost, arrival, delay, host in ((0, .10, .41, 0), (1, 20, .43, 3)):
            if i == round(arrival * fps):
                event('boo_spawn', i, ghost=ghost, id=PLAYERS[host])
            if i == round((arrival + delay) * fps):
                owners[ghost] = host
                touched[ghost] = i - round((TAG_LOCK - SPAWN_LOCK) * fps)
                event('boo_attach', i, ghost=ghost, id=PLAYERS[host])

        for ghost, owner in enumerate(tuple(owners)):
            if owner is None or i - touched[ghost] < round(TAG_LOCK * fps):
                continue
            if in_treasure(positions[owner]) is not None:
                continue
            choices = [
                (hypot(positions[owner][0] - x, positions[owner][1] - y), other)
                for other, (x, y) in enumerate(positions)
                if other not in owners and other != protected[ghost] and in_treasure((x, y)) is None
            ]
            separation, other = min(choices, default=(float('inf'), None))
            if separation > TAG_RADIUS:
                continue
            owners[ghost] = other
            last_sources[ghost] = owner
            touched[ghost] = i
            if ghost == 0:
                stage += 1
            event('tag', i, ghost=ghost, id=PLAYERS[other], source=PLAYERS[owner],
                  at=tuple(round(value, 2) for value in positions[other]), distance=round(separation, 2))

        if i % max(1, fps // 2) == 0:
            for owner in owners:
                if owner is None or steering.modes[owner] != 'chase':
                    continue
                chase_target = steering.targets[owner]
                if chase_target is None or chase_target in owners:
                    continue
                cover = steering.nav.cover(positions[owner], positions[chase_target])
                event('chase_sample', i, id=PLAYERS[owner], target=PLAYERS[chase_target],
                      gap=round(gap(positions[owner], positions[chase_target]), 2),
                      speed=round(hypot(*velocity[owner]), 2),
                      runner_speed=round(hypot(*velocity[chase_target]), 2),
                      pursuer=tuple(round(value, 2) for value in positions[owner]),
                      runner=tuple(round(value, 2) for value in positions[chase_target]),
                      cover=TREASURE[cover][0] if cover is not None else None,
                      route=steering.routes[chase_target])
        phase = tuple(in_treasure(pos) if who in owners else None for who, pos in enumerate(positions))
        for who, (old, new) in enumerate(zip(phasing, phase)):
            if old != new:
                event('phase_wall' if new is not None else 'phase_exit', i, id=PLAYERS[who],
                      treasure=TREASURE[new if new is not None else old][0])
        phasing = phase
        frames.append(Frame(positions, directions, distance, tuple(owners), tuple(totals), phasing))

    winner = min(range(4), key=totals.__getitem__)
    scores = {who: round(total / fps, 3) for who, total in zip(PLAYERS, totals)}
    events += [dict(t=FINISH, type='finish'), dict(t=FINISH, type='win', id=PLAYERS[winner], scores=scores)]
    return frames, events, PLAYERS[winner], scores


@lru_cache(maxsize=48)
def native_asset(name):
    with Image.open(NATIVE / f'{name}.png') as image:
        return image.convert('RGBA')


@lru_cache(maxsize=30)
def ghost_sprite(height, left=False):
    image = native_asset('boo-alt' if left else 'boo')
    image = image.crop(image.getbbox())
    return image.resize((round(image.width * height / image.height), height), NEAR)


# Front-facing parts of the original solid objects, for occlusion by depth.
OCCLUDERS = (
    (81, ((68, 78), (70, 64), (83, 43), (93, 43), (100, 49), (98, 60), (87, 81), (79, 85))),
    (63, ((121, 47), (127, 39), (140, 34), (152, 38), (158, 48), (156, 60),
          (149, 68), (133, 69), (123, 62))),
    (113, ((40, 104), (46, 98), (55, 98), (60, 103), (61, 113), (55, 119), (47, 118), (41, 113))),
    (143, ((60, 130), (64, 126), (110, 126), (114, 130), (114, 147), (60, 147))),
    (72, ((170, 68), (185, 65), (193, 61), (199, 37), (207, 33), (214, 35),
          (214, 53), (210, 65), (224, 69), (230, 76), (174, 78))),
    (153, ((184, 128), (187, 121), (198, 115), (208, 124), (230, 147), (234, 152), (227, 161))),
    (141, ((149, 134), (153, 131), (159, 132), (164, 136), (162, 142), (157, 145), (151, 141))),
)


def silhouette(plate, poly):
    mask = Image.new('L', SIZE)
    ImageDraw.Draw(mask).polygon(poly, fill=255)
    art = plate.convert('RGBA')
    art.putalpha(mask)
    return art


def walk_scale(who, y):
    """Match the size change between the rear and the front of the DS chest."""
    return round(HEIGHTS[who] * mix(.78, 1.10, (y - 29) / 129))


def crop_camera(image, focus, zoom):
    width, height = SIZE
    x, y = focus
    w, h = width / zoom, height / zoom
    return image.transform(SIZE, Image.Transform.AFFINE,
                           (w / width, 0, x - w / 2, 0, h / height, y - h / 2), NEAR)


class BooGame:
    def __init__(self, sprite, fps=60):
        self.fps = fps
        self.sprite = sprite
        self.frames, self.events, self.winner, self.scores = simulate(fps)
        self.chest = native_asset('arena-clean').resize(SIZE, NEAR).convert('RGB')
        self.night = native_asset('night').resize(SIZE, NEAR).convert('RGB')
        self.opening = tuple(native_asset(f'opening/{path.stem}').resize(SIZE, NEAR).convert('RGB')
                             for path in sorted((NATIVE / 'opening').glob('*.png')))
        self.props = tuple((depth, silhouette(self.chest, poly)) for depth, poly in OCCLUDERS)
        self.score_faces = tuple(sprite(f'{who}-face', 12) for who in PLAYERS)
        self.spawn = tuple(event for event in self.events if event['type'] == 'boo_spawn')
        self.attach = tuple(event for event in self.events if event['type'] == 'boo_attach')
        self.tags = tuple(event for event in self.events if event['type'] == 'tag')
        self.adoption = next(event['t'] for event in self.events if event['type'] == 'adopt_boo')
        self.has_up = (ROOT / 'assets/cast/gerson-up-0.png').is_file()

    def draw_counter(self, screen, who, seconds, x, y):
        """Draw an original DS possession strip with the crossover portrait."""
        if isinstance(who, str):
            who = PLAYERS.index(who)
        plate = native_asset(f'hud-counter-{COLORS[who]}').copy()
        start = 16 if who % 2 == 0 else 8
        for i, digit in enumerate(f'{seconds:05.2f}'):
            glyph = native_asset(f'score-glyphs/{"dot" if digit == "." else digit}')
            paste(plate, glyph, start + i * 8, 2)
        paste(screen, plate.resize((60, 11), NEAR), x, y)
        offset = 3 if who % 2 == 0 else 56
        centered(screen, self.score_faces[who], x + offset, y + 5)

    def counters(self, screen, frame, elapsed, alpha):
        overlay = screen.copy() if alpha < 1 else screen
        for who, (x, y) in enumerate(((30, 6), (150, 6), (30, 163), (150, 163))):
            self.draw_counter(overlay, who, frame.score[who] / WORLD_FPS, x, y)
        remaining = max(0, ceil(LIMIT - elapsed))
        clock_name = f'clocks/{remaining:02}' if remaining else 'hud-clock'
        clock = native_asset(clock_name).resize((38, 23), NEAR)
        paste(overlay, clock, 101, 4)
        return Image.blend(screen, overlay, alpha) if alpha < 1 else screen

    def stand(self, local):
        first = self.frames[0]
        u = smooth((local - 1.94) / .69)
        poses = tuple((mix(a[0], b[0], u), mix(a[1], b[1], u))
                      for a, b in zip(ENTRY, first.positions))
        strides = tuple(u * hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(ENTRY, first.positions))
        return Frame(poses, first.directions, strides, first.owners, first.score, first.phasing)

    def runout(self, age):
        end = self.frames[-1]
        samples = max(1, round(self.fps / 9))
        prev = self.frames[-1 - samples]
        per_second = self.fps / samples
        speed = tuple(((x - ox) * per_second, (y - oy) * per_second)
                      for (x, y), (ox, oy) in zip(end.positions, prev.positions))
        # Decelerate without advancing the clock or changing ownership.
        coast = .29 * (1 - (1 - min(age / .46, 1)) ** 2)
        points = tuple(move_to(pos, (pos[0] + dx * coast, pos[1] + dy * coast), i in end.owners,
                               hypot(dx, dy) * coast)
                       for i, (pos, (dx, dy)) in enumerate(zip(end.positions, speed)))
        directions = end.directions if age < .58 else ('down',) * 4
        strides = tuple(stride + hypot(x - ox, y - oy) for stride, (x, y), (ox, oy)
                        in zip(end.strides, points, end.positions))
        return Frame(points, directions, strides, end.owners, end.score, end.phasing)

    def shoulder(self, frame, owner, ghost, local):
        x, y = frame.positions[owner]
        face = frame.directions[owner]
        height = walk_scale(owner, y)
        sign = 1 if face == 'left' else -1
        bob = sin((local * 2.5 + ghost * .36) * pi) * 2
        if owner == 2:
            u = smooth((local - self.adoption) / 1.3)
            return x + mix(sign * 5, 13, u), y - mix(height + 8, height * .74, u) + bob
        return x + sign * 5, y - height - 8 + bob

    def boo_position(self, frame, ghost, local):
        host = frame.owners[ghost]
        if local >= FINISH and host is not None:
            age = local - FINISH - .14 - ghost * .11
            x, y = self.shoulder(frame, host, ghost, local)
            if age >= .78:
                return
            u = smooth(age / .78)
            return mix(x, 104 + 63 * ghost, u), mix(y, -14, u)
        if host is None:
            start, end = self.spawn[ghost]['t'], self.attach[ghost]['t']
            if not start <= local < end:
                return
            host = PLAYERS.index(self.attach[ghost]['id'])
            x, y = self.shoulder(frame, host, ghost, local)
            u = smooth((local - start) / (end - start))
            return mix(70 if ghost == 0 else 159, x, u), mix(-10, y, u)
        x, y = self.shoulder(frame, host, ghost, local)
        for tag in self.tags:
            age = local - tag['t']
            if tag['ghost'] == ghost and 0 <= age < .14:
                source = PLAYERS.index(tag['source'])
                sx, sy = self.shoulder(frame, source, ghost, local)
                u = smooth(age / .14)
                return mix(sx, x, u), mix(sy, y, u) - 4 * sin(pi * u)
        return x, y

    def upper_window(self, local):
        upper = self.night.copy()
        for ghost, spawn in enumerate(self.spawn):
            until_drop = spawn['t'] - local
            since_finish = local - FINISH - .82 - ghost * .10
            if until_drop <= 0 and since_finish < 0:
                continue
            phase = local * (1.48 if ghost == 0 else 1.18) + ghost * 2.4
            x = (81 if ghost == 0 else 163) + 43 * sin(phase)
            y = (63 if ghost == 0 else 45) + 17 * cos(phase * .71)
            if until_drop > 0:
                descend = smooth(1 - until_drop / .88)
                x = mix(x, 70 if ghost == 0 else 159, descend)
                y = mix(y, 196, descend)
            else:
                enter = smooth(since_finish / .66)
                x = mix(104 + 63 * ghost, x, enter)
                y = mix(195, y, enter)
            centered(upper, ghost_sprite(41, cos(phase) < 0), x, y)
        return upper

    def draw_field(self, frame, local, previous=None):
        screen = self.chest.copy()
        draw = ImageDraw.Draw(screen)
        for x, y in frame.positions:
            radius = mix(3, 5, (y - 29) / 129)
            draw.ellipse((x - radius, y - 2, x + radius, y + 1), fill='#674220')
        layers = [(depth, 0, i) for i, (depth, _) in enumerate(self.props)]
        layers += [(y, 1, i) for i, (_, y) in enumerate(frame.positions)]
        for _, actor, i in sorted(layers):
            if not actor:
                paste(screen, self.props[i][1], 0, 0)
                continue
            x, y = frame.positions[i]
            facing = frame.directions[i]
            who = PLAYERS[i]
            if who == 'gerson' and facing == 'up' and not self.has_up:
                facing = 'left'
            if who == 'ralsei' and self.adoption + 1.15 < local < self.adoption + 2.55:
                facing = 'right'
            walk = previous is not None and frame.strides[i] > previous.strides[i] + .1
            if 1.98 < local < 2.58:
                walk = True
            step = int(frame.strides[i] / 2.6) % 4 if walk else 0
            pose = self.sprite(f'{who}-{facing}-{step}', walk_scale(i, y))
            if frame.phasing[i] is not None:
                pose = pose.copy()
                pose.putalpha(pose.getchannel('A').point(lambda value: round(value * .66)))
            paste(screen, pose, x - pose.width / 2, y - pose.height)
        for ghost in (0, 1):
            point = self.boo_position(frame, ghost, local)
            if point:
                owner = frame.owners[ghost]
                y = frame.positions[owner][1] if owner is not None else 90
                height = round(mix(12, 17, (y - 29) / 129))
                left = owner is not None and frame.directions[owner] == 'left'
                centered(screen, ghost_sprite(height, left), *point)
        return screen

    def screens(self, local):
        upper = self.upper_window(local)
        if local < 1.51:
            index = min(len(self.opening) - 1, max(0, int(local / 1.51 * len(self.opening))))
            return self.opening[index].copy(), upper
        if local < READY:
            frame = self.stand(local)
            progress = smooth((local - 1.77) / .78)
            focus = mix(106, 120, progress), mix(87, 90, progress)
            lower = crop_camera(self.draw_field(frame, local), focus, mix(1.51, 1, progress))
            if local < 1.83:
                zoom = smooth((local - 1.51) / .32)
                opening = crop_camera(self.opening[-1], (mix(120, 78, zoom), mix(90, 63, zoom)),
                                      mix(1, 1.61, zoom))
                lower = Image.blend(opening, lower, smooth((local - 1.57) / .26))
            alpha = smooth((local - 2.38) / .34)
            return self.counters(lower, frame, 0, alpha) if alpha > 0 else lower, upper
        elapsed = min(LIMIT, local - READY)
        i = round(elapsed * self.fps)
        frame = self.frames[i] if local <= FINISH else self.runout(local - FINISH)
        previous = self.frames[max(0, i - 1)] if local <= FINISH else self.runout(max(0, local - FINISH - 1 / self.fps))
        lower = self.draw_field(frame, local, previous)
        return self.counters(lower, frame, elapsed, 1), upper
