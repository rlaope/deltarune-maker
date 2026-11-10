"""Shared Mario Party DS board, player panels, dice, and results."""

from dataclasses import dataclass
from functools import lru_cache
from math import pi, sin

from PIL import Image, ImageDraw, ImageFilter

from mpds_ui import COLORS, checkered, ds_text, number, resized, stamp
from reel_art import NEAR, SIZE, centered, paste, point, smooth, stylus


PLAYER_COLORS = ('blue', 'red', 'green', 'yellow')
SPACES = {'blue': '#589fe5', 'red': '#f76d78', 'event': '#77b86e'}
MAP_SPACES = {'blue': '#3359ff', 'red': '#f94042', 'event': '#4da85b'}
CASTLE_LOOP = ((29, 142), (66, 125), (111, 130), (157, 115), (199, 106), (240, 96),
               (259, 72), (217, 59), (170, 54), (125, 58), (83, 68), (44, 77))
CASTLE_SPACES = ('blue', 'blue', 'blue', 'red', 'event', 'blue',
                 'blue', 'red', 'blue', 'blue', 'red', 'blue')


@dataclass(frozen=True)
class Pose:
    x: float
    y: float
    facing: str = 'down'
    stride: int = 0
    lift: float = 0
    sprite: str | None = None


@dataclass(frozen=True)
class Roll:
    face: int
    hit_age: float
    remaining: int | None = None


@dataclass(frozen=True)
class BoardState:
    poses: dict[str, Pose]
    coins: dict[str, int]
    stars: dict[str, int]
    active: str
    turn: int
    total_turns: int
    roll: Roll | None = None
    banner_age: float | None = None
    markers: tuple[tuple[int, str], ...] = ()


class PartyBoard:
    def __init__(self, background, route, spaces, players, sprite, heights):
        if len(route) < 3 or len(route) != len(spaces):
            raise ValueError('Each point on a closed board must have a space type')
        if len(players) != 4 or len(set(players)) != 4:
            raise ValueError('The DS layout expects four distinct players')
        if background.height != SIZE[1] or background.width < SIZE[0]:
            raise ValueError('Use a board plate at least 240 pixels wide and 180 pixels high')
        self.route = tuple(route)
        self.spaces = tuple(spaces)
        self.players = tuple(players)
        self.sprite = sprite
        self.heights = heights
        self.plate = background.convert('RGB')
        self.map = self._draw_map(self.plate)
        self._draw_route(self.plate)

    def route_position(self, node, progress=0):
        if not 0 <= progress <= 1:
            raise ValueError('Space progress must be between 0 and 1')
        start = node % len(self.route)
        return point(self.route[start], self.route[(start + 1) % len(self.route)], progress)

    def _draw_route(self, image):
        draw = ImageDraw.Draw(image)
        loop = self.route + (self.route[0],)
        draw.line(loop, fill='#594451', width=8, joint='curve')
        draw.line(loop, fill='#d4b5a4', width=4, joint='curve')
        for (x, y), kind in zip(self.route, self.spaces):
            draw.ellipse((x - 11, y - 5, x + 11, y + 7), fill='#25213a')
            draw.ellipse((x - 11, y - 7, x + 11, y + 5), fill='#c0a472', outline='#edd4a1')
            draw.ellipse((x - 9, y - 5, x + 9, y + 3), fill=SPACES[kind])
            draw.line((x - 5, y - 4, x + 4, y - 4), fill='#eee3ef')
            if kind == 'event':
                ds_text(image, '?', x, y - 9, height=9, middle=True, outline='#315434')

    def map_point(self, x, y):
        left, top, right, bottom = self.map_crop
        return 41 + (x - left) * 158 / (right - left), 21 + (y - top) * 134 / (bottom - top)

    def _draw_map(self, background):
        image = checkered(('#f3e7e2', '#e4cbcc'))
        xs, ys = zip(*self.route)
        self.map_crop = (min(xs) - 13, min(ys) - 23, max(xs) + 19, max(ys) + 18)
        miniature = background.crop(self.map_crop).resize((158, 134), NEAR)
        miniature = Image.blend(miniature, Image.new('RGB', miniature.size, '#fbece2'), .73)
        mask = Image.new('L', miniature.size)
        ImageDraw.Draw(mask).ellipse((0, 0, 157, 133), fill=255)
        image.paste(miniature, (41, 21), mask)
        draw = ImageDraw.Draw(image)
        draw.ellipse((41, 21, 198, 154), outline='#bc8c91', width=2)
        points = tuple(self.map_point(*p) for p in self.route)
        draw.line(points + (points[0],), fill='#b78991', width=9, joint='curve')
        draw.line(points + (points[0],), fill='#f5efff', width=5, joint='curve')
        for (x, y), kind in zip(points, self.spaces):
            draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=MAP_SPACES[kind], outline='white')
        return image

    def standings(self, state):
        totals = {who: (state.stars[who], state.coins[who]) for who in self.players}
        ordered = sorted(self.players, key=totals.get, reverse=True)
        return [(who, 1 + sum(other > totals[who] for other in totals.values())) for who in ordered]

    def upper(self, state):
        image = self.map.copy()
        draw = ImageDraw.Draw(image)
        paste(image, stamp('board-turn'), 71, 164)
        ds_text(image, str(state.turn), 119, 162, height=9)
        ds_text(image, str(state.total_turns), 148, 162, height=9)
        places = dict(self.standings(state))
        for i, who in enumerate(self.players):
            pose = state.poses[who]
            nx, ny = self.map_point(pose.x, pose.y)
            draw.ellipse((nx - 5, ny - 5, nx + 5, ny + 5), fill=COLORS[i], outline='white')
            centered(image, self.sprite(f'{who}-face', 8), nx, ny)
        for index, asset in state.markers:
            x, y = self.map_point(*self.route[index])
            centered(image, resized(asset, 12, 12), x, y - 8)
        for i, who in enumerate(self.players):
            x, y = (5 if i % 2 == 0 else 182), (4 if i < 2 else 120)
            pose = state.poses[who]
            index = min(range(len(self.route)),
                        key=lambda j: (pose.x - self.route[j][0]) ** 2 + (pose.y - self.route[j][1]) ** 2)
            landing = 'red' if self.spaces[index] == 'red' else 'blue'
            tile = resized(f'board-panel-{PLAYER_COLORS[i]}-{landing}', 54, 62).copy()
            tile.putalpha(tile.getchannel('A').point(lambda value: round(value * .60)))
            paste(image, tile, x, y)
            paste(image, stamp('board-counter'), x + 19, y + 23)
            centered(image, self.sprite(f'{who}-face', 24), x + 13, y + 24)
            paste(image, stamp(f'board-rank-{places[who]}'), x + 28, y + 5)
            ds_text(image, str(state.stars[who]), x + 44, y + 23, height=8, middle=True)
            ds_text(image, str(state.coins[who]), x + 44, y + 35, height=8, middle=True)
            if who == state.active:
                draw.polygon(((x + 24, y + 52), (x + 33, y + 52), (x + 29, y + 57)),
                             fill='#fdf8a4', outline='#2a213b')
        return image

    def lower(self, state, t, focus=None):
        active = state.poses[state.active]
        center = active.x if focus is None else focus
        camera = round(max(0, min(self.plate.width - SIZE[0], center - 112)))
        image = self.plate.crop((camera, 0, camera + SIZE[0], SIZE[1]))
        draw = ImageDraw.Draw(image)
        for index, asset in state.markers:
            x, y = self.route[index]
            centered(image, resized(asset, 15, 15), x - camera, y - 8)
        for who, pose in sorted(state.poses.items(), key=lambda item: item[1].y):
            x, y = pose.x - camera, pose.y
            draw.ellipse((x - 8, y - 3, x + 8, y + 3), fill='#2a1520')
            actor = self.sprite(pose.sprite or f'{who}-{pose.facing}-{pose.stride}', self.heights[who])
            paste(image, actor, x - actor.width / 2, y - actor.height - pose.lift)
        if state.roll is not None:
            self._die(image, active.x - camera, active.y, state.roll, t)
        age = state.banner_age
        if age is not None and 0 <= age < 1.10:
            self._turn_banner(image, state.active, age)
        return image, camera

    @lru_cache(maxsize=16)
    def _turn_token(self, who):
        actor = self.sprite(f'{who}-down-0', 76).convert('RGBA')
        color = COLORS[self.players.index(who)]
        fill = Image.blend(Image.new('RGB', actor.size, color), actor.convert('RGB'), .34)
        fill.putalpha(actor.getchannel('A'))
        mask = Image.new('L', (actor.width + 4, actor.height + 4))
        mask.paste(actor.getchannel('A'), (2, 2))
        token = Image.new('RGBA', mask.size, 'white')
        token.putalpha(mask.filter(ImageFilter.MaxFilter(5)))
        token.alpha_composite(fill, (2, 2))
        return token

    def _turn_banner(self, image, who, age):
        slide = -192 * (1 - smooth(age / .19)) + 192 * smooth((age - .92) / .18)
        centered(image, stamp('turn-blue'), 120 + slide, 92)
        if age >= .08:
            drop = 17 * (1 - smooth((age - .08) / .19))
            centered(image, self._turn_token(who), 73 + slide, 94 - drop)
        if age >= .17:
            ds_text(image, who.upper(), 152 + slide, 70, height=18, middle=True, outline='#140b20')
            ds_text(image, 'GO!', 152 + slide, 91, height=20, middle=True, outline='#140b20')

    @staticmethod
    def _die(image, x, y, roll, t):
        if roll.remaining is not None:
            number(image, roll.remaining, x, max(3, y - 65), height=23)
            return
        age = roll.hit_age
        x += 15
        y = max(9, y - 76)
        if age < 0:
            y += round(4 * sin(t * 18))
            d = ImageDraw.Draw(image)
            d.polygon(((x - 18, y), (x - 9, y - 7), (x + 21, y - 7), (x + 16, y)),
                      fill='#ffebac', outline='#4f432a')
            d.polygon(((x + 16, y), (x + 21, y - 7), (x + 21, y + 24), (x + 16, y + 31)),
                      fill='#426c96', outline='#4f432a')
            d.rectangle((x - 18, y, x + 16, y + 31), fill='#76bbdc', outline='#f4d77b', width=2)
            paste(image, stamp('hit-button'), 170, 149)
            paste(image, resized('board-map-button', 27, 29), 213, 77)
            paste(image, resized('button-y', 11, 11), 211, 74)
        number(image, roll.face, x, y + 3, height=34 if age >= 0 else 24)
        if 0 <= age < .19:
            for side in (-1, 1):
                centered(image, resized('star', 8, 8), x + side * (17 + 40 * age), y + 10 - age * 22)
        if -.37 <= age < .26:
            approach = smooth((age + .37) / .37) - smooth(age / .26)
            stylus(image, x + 38 * (1 - approach), y + 14 + 29 * (1 - approach),
                   press=max(0, 1 - abs(age) / .14))

    def results(self, state, winner, award=0):
        image = Image.new('RGB', SIZE, '#05bfc4')
        paste(image, resized('results-paper', 240, 174), 0, 6)
        centered(image, resized('results', 152, 26), 120, 17)
        for i, (who, place) in enumerate(self.standings(state)):
            color = PLAYER_COLORS[self.players.index(who)]
            y = 34 + i * 32
            paste(image, resized(f'results-panel-{color}', 193, 27), 24, y)
            centered(image, resized(f'board-rank-{place}', 21, 14), 41, y + 13)
            centered(image, self.sprite(f'{who}-face', 19), 85, y + 13)
            centered(image, resized('star', 12, 12), 108, y + 8)
            ds_text(image, str(state.stars[who]), 126, y - 3, height=11, middle=True, outline='#271a33')
            centered(image, resized('coin', 11, 12), 169, y + 8)
            ds_text(image, str(state.coins[who]), 191, y - 3, height=11, middle=True, outline='#271a33')
            ds_text(image, who.capitalize(), 138, y + 11, height=9, middle=True)
            if who == winner and award:
                centered(image, resized('board-plus', 8, 10), 177, y + 21)
                ds_text(image, str(award), 195, y + 11, height=8, middle=True, outline='#51352c')
        centered(image, stamp('results-continue'), 120, 167)
        return image
