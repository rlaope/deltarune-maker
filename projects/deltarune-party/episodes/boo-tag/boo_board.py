"""The four-player courtyard round and its treasure chest encounter."""

from dataclasses import replace
from functools import lru_cache
from math import pi, sin

from PIL import Image, ImageDraw

from mpds_ui import ds_text, number, resized, stamp
from party_board import BoardState, PartyBoard, Pose, Roll
from party_items import DoubleDiceSet
from party_turns import (BANNER_DURATION, TURN_CAMERA_DURATION, BoardTurn, handoff_focus,
                         turn_events, visible_banner_age)
from reel_art import NEAR, ROOT, centered, mix, paste, smooth


PLAYERS = ('kris', 'susie', 'ralsei', 'gerson')
ROUTE = ((37, 145), (75, 145), (114, 144), (154, 144), (196, 147), (238, 147),
         (280, 133), (269, 103), (224, 101), (179, 101), (132, 100), (85, 104), (43, 111))
SPACES = ('blue', 'blue', 'blue', 'blue', 'event', 'red', 'blue',
          'blue', 'blue', 'red', 'blue', 'blue', 'blue')
HEIGHTS = dict(kris=37, susie=43, ralsei=40, gerson=38)
NODES = dict(kris=10, susie=6, ralsei=1, gerson=8)
COINS = dict(kris=22, susie=16, ralsei=19, gerson=25)
BANNER, DIE_START, DIE_HIT, MOVE = .05, 1.23, 1.99, 2.70
STEP_TIME, ROLL = .53, 3
LAND = MOVE + ROLL * STEP_TIME
CHEST_OPEN = 5.42
BOO_APPEAR = CHEST_OPEN + .09
BOO_HIT = 6.02
COIN_LOSS = 5
COIN_LOSS_TIME = 6.10
COIN_HITS = (6.42, 6.47, 6.52, 6.57, 6.62)
BOO_CLEAR = 6.86
EVENT_NODE = NODES['ralsei'] + ROLL
BLUE_REWARD = 3
REWARD = 10
CAST = ROOT / 'assets/cast'
NATIVE = ROOT / 'assets/boo-native'
ROLLING_FACES = (4, 8, 2, 6, 9, 7, 5)
RALSEI_LINE = dict(speaker='ralsei', start=6.89, end=7.81, text="* ...I'm okay!",
                   portrait='ralsei-worried-face')
SUSIE_START = round(RALSEI_LINE['end'] + .50, 2)
ITEM_OPEN = round(SUSIE_START + 2.60, 2)
ITEM_FOCUS = round(ITEM_OPEN + .51, 2)
DOUBLE_ITEM = round(ITEM_FOCUS + .60, 2)
DOUBLE_TOTAL = round(DOUBLE_ITEM + 1.77, 2)
BOARD_LINES = (
    RALSEI_LINE,
    dict(speaker='susie', start=round(ITEM_OPEN - 1.23, 2), end=round(ITEM_OPEN - .05, 2),
         text="* Heh. I'll take two.", portrait='susie-laugh-face'),
    dict(speaker='gerson', start=round(DOUBLE_TOTAL - .25, 2), end=round(DOUBLE_TOTAL + .76, 2),
         text="* Add 'em up, kid.", portrait='gerson-laugh-face'),
)


SUSIE_TURN = BoardTurn('susie', SUSIE_START,
                       tuple(round(DOUBLE_ITEM + delay, 2) for delay in (.23, 1.07)),
                       tuple(round(DOUBLE_ITEM + delay, 2) for delay in (.75, 1.40)),
                       (2, 3), round(DOUBLE_TOTAL + .27, 2), .31, NODES['susie'], len(ROUTE))
KRIS_START = SUSIE_TURN.after_award(1.12)
KRIS_BANNER_HOLD = .25
KRIS_SPIN = round(KRIS_START + TURN_CAMERA_DURATION + BANNER_DURATION + KRIS_BANNER_HOLD + .17, 2)
KRIS_TURN = BoardTurn('kris', KRIS_START, (KRIS_SPIN,), (round(KRIS_SPIN + .52, 2),),
                      (2,), round(KRIS_SPIN + .90, 2), .33, NODES['kris'], len(ROUTE), KRIS_BANNER_HOLD)
TURNS = (SUSIE_TURN, KRIS_TURN)
DOUBLE_DICE = DoubleDiceSet(SUSIE_TURN, ITEM_OPEN, ITEM_FOCUS, DOUBLE_ITEM, DOUBLE_TOTAL)
DRAW_READY = KRIS_TURN.after_award(1.50)


def board_round_events():
    events = list(DOUBLE_DICE.events())
    for turn in TURNS:
        events.extend(turn_events(turn, BLUE_REWARD))
    events.append(dict(t=DRAW_READY - .25, type='round_complete'))
    return sorted(events, key=lambda event: event['t'])


@lru_cache(maxsize=160)
def sprite(name, height):
    with Image.open(CAST / f'{name}.png') as source:
        art = source.convert('RGBA')
    art = art.crop(art.getbbox())
    return art.resize((max(1, round(art.width * height / art.height)), height), NEAR)


@lru_cache(maxsize=8)
def boo_art(height):
    with Image.open(NATIVE / 'boo.png') as source:
        art = source.convert('RGBA')
    art = art.crop(art.getbbox())
    return art.resize((max(1, round(art.width * height / art.height)), height), NEAR)


@lru_cache(maxsize=1)
def loss_sign():
    art = stamp('board-minus')
    return art.crop(art.getbbox()).resize((12, 5), NEAR)


class Courtyard:
    def __init__(self, winner, payout, return_time):
        self.winner = winner
        self.payout = payout
        self.return_time = return_time
        with Image.open(ROOT / 'assets/board/courtyard.png') as plate:
            self.board = PartyBoard(plate, ROUTE, SPACES, PLAYERS, sprite, HEIGHTS)
        if SPACES[EVENT_NODE] != 'event':
            raise ValueError('The chest belongs on the question-mark space')
        if any(SPACES[turn.destination] != 'blue' for turn in TURNS):
            raise ValueError('The shown regular turns must land on blue spaces')

    def advance(self, start, offset, step, count):
        distance = offset / step
        passed = min(count - 1, int(distance))
        progress = min(1, distance - passed)
        here = self.board.route_position(start + passed)
        there = self.board.route_position(start + passed + 1)
        x, y = self.board.route_position(start + passed, smooth(progress))
        dx, dy = there[0] - here[0], there[1] - here[1]
        if abs(dx) >= abs(dy):
            facing = 'left' if dx < 0 else 'right'
        else:
            facing = 'up' if dy < 0 else 'down'
        return Pose(x, y, facing, int(distance * 4) % 4, 7 * sin(pi * progress)), count - passed

    def state(self, t):
        positions = {who: self.board.route_position(node) for who, node in NODES.items()}
        poses = {who: Pose(*xy) for who, xy in positions.items()}
        coins = COINS.copy()
        if t >= COIN_LOSS_TIME:
            coins['ralsei'] -= COIN_LOSS
        if t >= self.payout:
            coins[self.winner] += REWARD

        active, banner_start, roll = 'ralsei', BANNER, None
        if DIE_START <= t < MOVE:
            face = ROLLING_FACES[int((t - DIE_START) * 14) % len(ROLLING_FACES)] if t < DIE_HIT else ROLL
            roll = Roll(face, t - DIE_HIT)
            jump = 15 * max(0, 1 - abs(t - DIE_HIT) / .23)
            poses['ralsei'] = Pose(*positions['ralsei'], lift=jump)
        if MOVE <= t < LAND:
            pose, remaining = self.advance(NODES['ralsei'], t - MOVE, STEP_TIME, ROLL)
            poses['ralsei'] = replace(pose, stride=int(t * 13) % 4)
            roll = Roll(ROLL, t - DIE_HIT, remaining)
        if t >= LAND:
            x, y = self.board.route_position(EVENT_NODE)
            anticipation = smooth((t - BOO_APPEAR - .12) / .17)
            recoil = smooth((t - BOO_HIT) / .13) * (1 - smooth((t - BOO_HIT - .20) / .41))
            facing = 'up' if not anticipation else 'right'
            if t >= BOO_CLEAR:
                facing = 'down'
            poses['ralsei'] = Pose(x - 19 * recoil, y + 7 * recoil, facing,
                                   stride=2 if recoil > .15 else 0, lift=8 * recoil)
        for turn in TURNS:
            if t < turn.start:
                break
            active, banner_start, roll = turn.who, turn.banner, None
            if turn.spins[0] <= t < turn.move:
                jump = 12 * max(max(0, 1 - abs(t - hit) / .15) for hit in turn.hits)
                poses[active] = Pose(*positions[active], lift=jump)
                if len(turn.faces) == 1:
                    roll = self.roll_face(t, turn.spins[0], turn.hits[0], turn.faces[0])
            if turn.move <= t < turn.land:
                poses[active], remaining = self.advance(NODES[active], t - turn.move, turn.step, turn.spaces)
                roll = Roll(turn.spaces, t - turn.hits[-1], remaining)
            if t >= turn.land:
                lift = 5 * max(0, 1 - abs(t - turn.award) / .17)
                poses[active] = Pose(*self.board.route_position(turn.destination), lift=lift)
            if t >= turn.award:
                coins[active] += BLUE_REWARD
        if t >= self.return_time:
            active, banner_start = 'ralsei', BANNER
            poses['ralsei'] = Pose(*self.board.route_position(EVENT_NODE), 'up')
            if self.winner != 'gerson':
                pose = poses[self.winner]
                jump = max(0, 1 - abs(t - self.payout) / .20) * 5
                poses[self.winner] = Pose(pose.x, pose.y, pose.facing, lift=jump)
        return BoardState(poses, coins, dict.fromkeys(PLAYERS, 0), active,
                          4 if t < self.return_time else 5, 10, roll, t - banner_start)

    @staticmethod
    def roll_face(t, spin, hit, face):
        if t < hit:
            face = ROLLING_FACES[int((t - spin) * 14) % len(ROLLING_FACES)]
        return Roll(face, t - hit)

    def screens(self, t, encounter=True):
        state = self.state(t)
        focus = state.poses[state.active].x
        prior_x = ROUTE[EVENT_NODE][0]
        for turn in TURNS:
            if state.active == turn.who:
                focus = handoff_focus(self.board.plate.width, prior_x, focus, t, turn)
                break
            prior_x = ROUTE[turn.destination][0]
        if t >= self.return_time:
            focus = mix(focus, 192, smooth((t - self.return_time) / .75))
        lower, camera = self.board.lower(replace(state, banner_age=None), t, focus=focus)
        x, y = self.board.route_position(EVENT_NODE)
        x -= camera
        chest_x, chest_y = x + 18, y - 26
        if encounter:
            chest = 'chest-open' if t >= CHEST_OPEN else 'chest-closed'
            art = sprite(chest, 23 if chest == 'chest-closed' else 24)
            paste(lower, art, chest_x - art.width / 2, chest_y - art.height)
            if 0 <= t - LAND < .52:
                age = t - LAND
                ds_text(lower, '?', x, y - 45 - 21 * age, height=16, middle=True, outline='#272e62')
            if BOO_APPEAR <= t < BOO_CLEAR:
                self.draw_boo_contact(lower, t, x, y)
            elif t >= self.return_time:
                age = t - self.return_time
                if age > 2.23:
                    reveal = smooth((age - 2.23) / .50)
                    ghost_y = chest_y - 11 - 14 * reveal + sin(age * 5) * 2
                    centered(lower, boo_art(20), chest_x + 4, ghost_y)
        if ITEM_OPEN <= t < TURNS[0].spins[0]:
            DOUBLE_DICE.draw_menu(lower, t, state.poses['susie'].x - camera)
        elif TURNS[0].spins[0] <= t < TURNS[0].move:
            DOUBLE_DICE.draw_rolls(lower, t, state.poses['susie'], camera, self.board._die)
        if state.active != 'ralsei' and t < DRAW_READY:
            turn = next(turn for turn in TURNS if turn.who == state.active)
            if turn.land <= t < turn.award + .49:
                self.draw_blue_reward(lower, t, turn, camera)
        hold = KRIS_TURN.banner_hold if state.active == 'kris' else 0
        age = visible_banner_age(state.banner_age, hold)
        if age is not None:
            self.board._turn_banner(lower, state.active, age)
        return lower, self.board.upper(state)

    def draw_blue_reward(self, lower, t, turn, camera):
        x, y = self.board.route_position(turn.destination)
        x -= camera
        for index in range(BLUE_REWARD):
            age = (t - turn.land - .045 - index * .04) / .145
            if 0 <= age < 1:
                centered(lower, resized('coin', 6 + round(3 * sin(pi * age)), 11),
                         x + (index - 1) * 11 * (1 - age), mix(y - 62, y - 18, age * age))
        if t >= turn.award:
            label_x = max(26, x)
            label_y = y - 56 - 7 * smooth((t - turn.award) / .22)
            centered(lower, resized('coin', 11, 13), label_x - 15, label_y)
            centered(lower, resized('board-plus', 10, 11), label_x - 3, label_y)
            number(lower, BLUE_REWARD, label_x + 9, label_y - 7, height=14, kind='coins')

    @staticmethod
    def draw_boo_contact(lower, t, x, y):
        body_y = y - HEIGHTS['ralsei'] / 2
        rise = smooth((t - BOO_APPEAR) / .28)
        dive = smooth((t - BOO_APPEAR - .28) / (BOO_HIT - BOO_APPEAR - .28))
        retreat = smooth((t - BOO_HIT) / .30)
        ghost_x = mix(x + 18 + 12 * rise, x, dive) + 38 * retreat
        ghost_y = mix(y - 30 - 27 * rise, body_y, dive) - 24 * retreat
        art = boo_art(round(9 + 16 * rise))
        fade = smooth((t - COIN_HITS[-1]) / (BOO_CLEAR - COIN_HITS[-1]))
        if fade:
            art = art.copy()
            art.putalpha(art.getchannel('A').point(lambda value: round(value * (1 - fade))))
        centered(lower, art, ghost_x, ghost_y)

        impact_age = t - BOO_HIT
        if 0 <= impact_age < .13:
            burst = 6 + round(90 * impact_age)
            draw = ImageDraw.Draw(lower)
            for dx, dy in ((-1, -1), (-1, 1), (1, -1)):
                draw.line((x + dx * burst, body_y + dy * burst,
                           x + dx * (burst + 5), body_y + dy * (burst + 4)),
                          fill='#fff3bb', width=2)

        for index, arrival in enumerate(COIN_HITS):
            flight = (t - arrival + .36) / .36
            if 0 <= flight < 1:
                arc = sin(pi * flight)
                coin_x = mix(x, ghost_x, flight) + (index - 2) * 6 * arc
                coin_y = mix(body_y, ghost_y, flight) - (14 + index * 3) * arc
                coin_w = 4 + round(6 * abs(sin(pi * 2 * flight)))
                centered(lower, resized('coin', coin_w, 12), coin_x, coin_y)
            elif 0 <= t - arrival < .09:
                centered(lower, resized('star', 7, 7), ghost_x + (index - 2) * 3, ghost_y - 11)

        if t >= COIN_LOSS_TIME:
            lift = 8 * smooth((t - COIN_LOSS_TIME) / .23)
            label_x, label_y = x - 12, y - 53 - lift
            centered(lower, resized('coin', 13, 15), label_x - 17, label_y)
            centered(lower, loss_sign(), label_x - 3, label_y)
            number(lower, COIN_LOSS, label_x + 10, label_y - 8, height=16, kind='coins')
