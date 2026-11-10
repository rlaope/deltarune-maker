"""Compose the original Fast Food Frenzy DS screens from the live replay."""

from functools import lru_cache
from math import ceil, floor, hypot, pi, sin

from PIL import Image, ImageChops, ImageDraw

from fast_simulation import DURATION, DROPS, END, FEED, FPS, READY, RUSH_TIME, TEAM, belt_speed, clamp, simulate
from reel_art import NEAR, ROOT, SIZE, centered, mix, paste, smooth

NATIVE = ROOT / 'assets/fast-food-native'
JARONA = ROOT / 'assets/deltarune/jarona-aura'
JARONA_TICK = 1 / 30
JARONA_AFTERIMAGE_TICKS = 12
JARONA_TRAIL_COLOR = '#0040bf'
JARONA_FOG_COLOR = '#004999'
TRAY = {
    'shake': (13, 106),
    'burger': (60, 113),
    'pancakes': (112, 100),
    'hot-dog': (112, 147),
    'fries': (206, 100),
    'ice-cream': (204, 146),
}
HEIGHT = {
    'burger': 62, 'shake': 66, 'hot-dog': 37,
    'pancakes': 40, 'ice-cream': 36, 'fries': 47,
}
RUNNER_HEIGHT = {'susie': 32, 'lancer': 31, 'noelle': 30}


@lru_cache(maxsize=100)
def asset(name):
    with Image.open(NATIVE / f'{name}.png') as source:
        return source.convert('RGBA')


def screen(name):
    return asset(name).resize(SIZE, NEAR).convert('RGB')


@lru_cache(maxsize=260)
def art_at_height(name, height):
    item = asset(name)
    return item.resize((max(1, round(item.width * height / item.height)), height), NEAR)


def perspective(x, z):
    """Project horizontal lanes and one shared belt depth into the DS upper screen."""
    depth = clamp(z / END, 0, 1)
    ratio = (1.40 * depth) / (1 + .40 * depth)
    scale = 1.02 - .48 * ratio
    y = 180 - 168 * ratio + 1.8 * max(0, -z) - .85 * max(0, z - END)
    return 119 + 2 * depth + 66.5 * x * scale, y, scale


def feed(x):
    return 120 + 55.5 * x


def panel_sequence(folder, pattern='*.png'):
    return tuple(screen(f'{folder}/{path.stem}') for path in sorted((NATIVE / folder).glob(pattern)))


@lru_cache(maxsize=4)
def jarona_fog(color, left):
    with Image.open(JARONA / 'punch-00.png') as source:
        silhouette = source.convert('RGBA').getchannel('A')
    silhouette = silhouette.crop(silhouette.getbbox())
    silhouette = silhouette.resize((round(silhouette.width * 44 / silhouette.height), 44), NEAR)
    if not left:
        silhouette = silhouette.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    fog = Image.new('RGBA', silhouette.size, color)
    fog.putalpha(silhouette)
    return fog


def fog_opacity(fog, opacity):
    frame = fog.copy()
    frame.putalpha(fog.getchannel('A').point(lambda alpha: round(alpha * opacity)))
    return frame


class FastGame:
    ready = READY
    duration = DURATION
    team = TEAM

    def __init__(self, sprite):
        self.sprite = sprite
        self.frames, self.events, self.winner, self.survivors = simulate()
        self.finish = self.events[-1]['t']
        self.intro = panel_sequence('intro')
        self.motion = tuple(zip(panel_sequence('motion', 'lower-*.png'),
                                panel_sequence('motion', 'upper-*.png'), strict=True))
        if not self.motion:
            raise ValueError('The cartridge conveyor motion plates are missing')
        self.tray = {}
        for name, (x, y) in TRAY.items():
            art = asset(name)
            w, h = (round(art.width * 15 / 16), round(art.height * 15 / 16))
            self.tray[name] = art.resize((w, h), NEAR), (x * 15 / 16, y * 15 / 16)
        self.food_models = {name: f'{name}-lane' for name in TRAY}
        self.contact = tuple(event for event in self.events if event['type'] == 'impact')
        self.dashes = tuple(event['t'] for event in self.events if event['type'] == 'dash')
        self.jarona = tuple(plan for plan in DROPS if plan.quick)

    def draw_clock(self, upper, elapsed):
        remaining = max(0, ceil(DURATION - elapsed))
        clock = asset(f'clocks/{remaining:02}').resize((37, 23), NEAR)
        paste(upper, clock, 4, 4)

    def draw_tray(self, lower, elapsed, world):
        for name, (art, (x, y)) in self.tray.items():
            missing = any(plan.kind == name and plan.pickup <= elapsed < plan.t + 1.04 for plan in DROPS)
            if missing:
                continue
            paste(lower, art, x, y)
        for _, kind, x, depth in world.food:
            if FEED <= depth < 0:
                p = smooth((depth + 16) / 16)
                sx, _, scale = perspective(x, 0)
                width = mix(feed(x), sx, p)
                item = art_at_height(self.food_models[kind], round(HEIGHT[kind] * mix(.72, scale, p)))
                y = mix((69 + item.height / 2) * depth / FEED, -1.8 * depth, p)
                paste(lower, item, width - item.width / 2, y - item.height + 2)
        self.draw_flowery(lower, elapsed)

    def carry(self, plan, progress):
        art, (slot_x, slot_y) = self.tray[plan.kind]
        source_x, source_y = slot_x + art.width / 2, slot_y + art.height / 2
        lane_x = feed(plan.x)
        if plan.quick:
            duration = plan.t - plan.pickup
            lead = plan.rush_start - plan.pickup
            age = progress * duration - lead
            u = smooth(age / RUSH_TIME)
            land = smooth((age - RUSH_TIME) / (duration - lead - RUSH_TIME))
            windup = 5 * sin(pi * clamp((age + lead) / lead, 0, 1))
            lift = 29 * sin(pi * u) + 15 * u * (1 - land) - windup
        else:
            u = smooth((progress - .11) / .89)
            lift = 13 * sin(pi * u)
        x = mix(source_x, lane_x, u)
        y = mix(source_y, 69, u) - lift
        side = 1 if source_x >= lane_x else -1
        reach = min(32, 9 + art.width * .36)
        body = clamp(x + side * reach, 15, 224), y + 15
        food = art_at_height(plan.kind, round(art.height * mix(1, .82, u)))
        return body, (x, y), food

    def delivery_lean(self, plan, progress, x, y):
        before, _, _ = self.carry(plan, progress - .045 / (plan.t - plan.pickup))
        dx, dy = x - before[0], y - before[1]
        speed = hypot(dx, dy)
        return -17 * dx / speed if speed >= 3 else 0

    def draw_jarona(self, lower, plan, elapsed):
        age = elapsed - plan.rush_start
        duration = plan.t - plan.pickup
        lead = plan.rush_start - plan.pickup
        left = self.carry(plan, 1)[0][0] < self.carry(plan, 0)[0][0]
        fog = jarona_fog(JARONA_TRAIL_COLOR, left)
        # The Chapter 5 attack leaves a new tinted silhouette each tick.
        last = floor(age / JARONA_TICK)
        for tick in range(max(0, last - JARONA_AFTERIMAGE_TICKS + 1),
                          min(last, floor(RUSH_TIME / JARONA_TICK)) + 1):
            lag = age / JARONA_TICK - tick
            (x, y), _, _ = self.carry(plan, (lead + tick * JARONA_TICK) / duration)
            drift = lag * (3 if left else -3)
            echo = fog_opacity(fog, 1 - lag / JARONA_AFTERIMAGE_TICKS)
            centered(lower, echo, x + drift, y - 22)
        if age <= RUSH_TIME:
            (x, y), _, _ = self.carry(plan, (lead + age) / duration)
            fog = fog_opacity(jarona_fog(JARONA_FOG_COLOR, left), .8)
            centered(lower, fog, x, y - 22)
            additive = Image.new('RGB', lower.size)
            centered(additive, fog, x, y - 22)
            lower.paste(ImageChops.add(lower, additive))

    def draw_flowery(self, lower, elapsed):
        """Link every grab and release with a continuous flight across the station."""
        if elapsed < -.31:
            return
        for plan in self.jarona:
            age = elapsed - plan.rush_start
            if 0 <= age < RUSH_TIME + JARONA_AFTERIMAGE_TICKS * JARONA_TICK:
                self.draw_jarona(lower, plan, elapsed)
        following = next((plan for plan in DROPS if elapsed < plan.t), None)
        if following and elapsed >= following.pickup:
            progress = (elapsed - following.pickup) / (following.t - following.pickup)
            (x, y), (fx, fy), food = self.carry(following, progress)
            face = self.sprite(f'flowery-clap-{int(elapsed * 12) % 4}', 44)
            if following.quick and 0 <= elapsed - following.rush_start <= RUSH_TIME:
                lean = self.delivery_lean(following, progress, x, y)
                if lean:
                    face = face.rotate(lean, resample=NEAR, expand=True)
            paste(lower, face, x - face.width / 2, y - face.height)
            centered(lower, food, fx, fy)
            return
        previous = next((plan for plan in reversed(DROPS) if elapsed >= plan.t), None)
        start = self.carry(previous, 1)[0] if previous else (254, 82)
        end = self.carry(following, 0)[0] if following else (213, 84)
        begin = previous.t if previous else -.31
        arrive = following.pickup if following else DROPS[-1].t + .90
        u = smooth((elapsed - begin) / (arrive - begin))
        x = mix(start[0], end[0], u)
        ground = mix(start[1], end[1], u)
        lift = sin(pi * u)
        y = ground - 29 * lift
        face = 'right' if end[0] > start[0] else 'left'
        height = 42
        if following is None and u == 1:
            face = 'down'
            y += 2 * sin(elapsed * 5)
        actor = self.sprite(f'flowery-{face}-{int(elapsed * 11) % 4}', height)
        if lift > .22:
            ImageDraw.Draw(lower, 'RGBA').ellipse(
                (round(x) - 6, round(ground), round(x) + 6, round(ground) + 2),
                fill=(47, 27, 17, round(56 * lift)),
            )
        tilt = (8 if face == 'left' else -8) * lift
        if tilt:
            actor = actor.rotate(tilt, resample=NEAR, expand=True)
        paste(lower, actor, x - actor.width / 2, y - actor.height)

    def draw_food(self, image, kind, x, z):
        sx, sy, scale = perspective(x, z)
        art = art_at_height(self.food_models[kind], round(HEIGHT[kind] * scale))
        paste(image, art, sx - art.width / 2, sy - art.height + 2)

    def draw_runner(self, image, pose, elapsed, contact=None):
        fallen = elapsed - pose.out if pose.out is not None else 0
        if fallen > .65:
            return
        sx, sy, scale = perspective(pose.x, pose.z)
        if fallen:
            progress = smooth(fallen / .65)
            sy -= 8 * progress + 5 * sin(pi * progress)
            scale *= 1 - .68 * progress
        lift = pose.height * scale
        if contact and contact['status'] == 'sticky':
            age = elapsed + READY - contact['t']
            lift = max(lift, 11 * (1 - smooth(age / .32)) * scale)
        draw = ImageDraw.Draw(image)
        if not fallen:
            width = 5.3 * scale
            draw.ellipse((sx - width, sy - 2, sx + width, sy + 1),
                         fill='#67401c')
            if pose.status == 'sticky':
                draw.ellipse((sx - 7 * scale, sy - 3, sx + 7 * scale, sy + 2),
                             fill='#d58116', outline='#824609')
                draw.line((sx - 3 * scale, sy - 1, sx + 2 * scale, sy - 2),
                          fill='#ffc05a', width=1)
                if lift > 4:
                    draw.line((sx + 2 * scale, sy - 1, sx, sy - min(lift, 8)),
                              fill='#d98926', width=1)
        step = int(pose.stride / 3.1) % 4
        if pose.status in ('blocked', 'frozen', 'stunned'):
            step = 0
        facing = pose.facing
        if pose.status == 'blocked':
            facing = 'up'
        height = max(5, round(RUNNER_HEIGHT[pose.id] * scale))
        actor = self.sprite(f'{pose.id}-{facing}-{step}', height)
        if pose.id == 'lancer' and facing in ('left', 'right'):
            dash = next((elapsed + READY - t for t in self.dashes
                         if 0 <= elapsed + READY - t < .37), None)
            if dash is not None:
                lean = (13 if facing == 'left' else -13) * sin(pi * dash / .37)
                actor = actor.rotate(lean, resample=NEAR, expand=True)
        if contact and contact['food'] == 'burger':
            age = elapsed + READY - contact['t']
            angle = 17 * (1 - smooth(age / .27))
            actor = actor.rotate(angle, resample=NEAR, expand=True)
        elif fallen:
            direction = -1 if pose.id == 'susie' else 1
            actor = actor.rotate(direction * fallen * 125, resample=NEAR, expand=True)
        paste(image, actor, sx - actor.width / 2, sy - actor.height - lift)
        if pose.status == 'frozen':
            draw.polygon(((sx - 7, sy - 4), (sx - 7, sy - 13), (sx - 1, sy - 19),
                          (sx + 6, sy - 16), (sx + 7, sy - 5), (sx + 2, sy)),
                         outline='#d8f9ff', width=1)

    def draw_field(self, upper, world, elapsed):
        food = [(z, 0, (kind, x, z)) for _, kind, x, z in world.food if 0 <= z <= END + 9]
        support = {
            event['player']: event for event in self.contact
            if -1 / (2 * FPS) <= elapsed + READY - event['t'] < .27
        }
        actors = [(pose.z, 1, pose) for pose in world.runners if pose.id not in support]
        for _, actor, value in sorted((*food, *actors), key=lambda layer: (-layer[0], layer[1])):
            if actor:
                self.draw_runner(upper, value, elapsed)
            else:
                self.draw_food(upper, *value)
        for pose in world.runners:
            if pose.id in support:
                self.draw_runner(upper, pose, elapsed, support[pose.id])

    def opening(self, t, upper):
        if not self.intro or t >= 1.82:
            return upper
        dark = Image.new('RGB', SIZE, '#10101a')
        if t < 1.48:
            index = min(len(self.intro) - 1, max(0, int(t * len(self.intro) / 1.21)))
            plate = self.intro[index].copy()
            progress = smooth(t / 1.28)
            x, y = mix(96, 79, progress), mix(149, 150, progress)
            pose = self.sprite(f'flowery-down-{int(t * 8) % 4}', 42)
            paste(plate, pose, x - pose.width / 2, y - pose.height)
            return Image.blend(plate, dark, smooth((t - 1.26) / .22))
        progress = smooth((t - 1.48) / .34)
        inset = round(13 * (1 - progress))
        camera = upper.crop((inset, inset, SIZE[0] - inset, SIZE[1] - inset)).resize(SIZE, NEAR)
        return Image.blend(dark, camera, smooth((t - 1.48) / .23))

    def screens(self, local):
        elapsed = clamp(local - READY, 0, len(self.frames) / FPS - 1 / FPS)
        frame = self.frames[round(elapsed * FPS)]
        idle = max(0, local - self.finish)
        travel = frame.travel + frame.speed * (.25 * (1 - (1 - min(idle / .5, 1)) ** 2))
        motion = int(travel * len(self.motion) / belt_speed(0)) % len(self.motion)
        lower_base, upper_base = self.motion[motion]
        lower, upper = lower_base.copy(), upper_base.copy()
        self.draw_tray(lower, local - READY, frame)
        self.draw_field(upper, frame, elapsed + idle)
        if local >= 1.82:
            self.draw_clock(upper, elapsed)
        return lower, self.opening(local, upper)
