"""Second Diner board round with movement read from the chapter 5 game replay."""

from functools import lru_cache
import json
from math import pi, sin
from pathlib import Path

from PIL import Image, ImageDraw

from fast_diner_event import FOOD_CLOSE, FOOD_FOCUS, FOOD_LOCK, FOOD_OPEN, FOOD_REVEAL, draw_food_event
from mpds_ui import checkered, ds_text, number, resized, stamp
from party_board import BoardState, PartyBoard, Pose, Roll
from party_turns import BoardTurn, next_turn_start, turn_events, visible_banner_age
from reel_art import NEAR, ROOT, SIZE, centered, mix, paste, point, smooth


REPLAY = json.loads(Path(__file__).with_name('fast-board-replay.json').read_text())
GRAPH = REPLAY['board']
NODES = {node['id']: node for node in GRAPH['spaces']}
DINER = next(region for region in GRAPH['regions'] if region['id'] == 'second-diner')
PLAYERS = tuple(REPLAY['setup']['players'])
STARTS = {player['id']: player['space'] for player in REPLAY['initial']['players']}
SPECIAL = REPLAY['event']
TEAM_COLORS = REPLAY['grouping']['teams']
OPENING_CAMERA = (175, 62, 440)
CAST = ROOT / 'assets/cast'
HEIGHTS = dict(lancer=34, susie=43, noelle=43, flowery=49)
SPACE_COLORS = dict(blue='#6babdf', red='#f47780', event='#80bc83', item='#ba94d9')
ROLLING = (7, 3, 5, 9, 2, 6, 4, 8)
EVENT_PAYOUT = 6.13
TURN_OFFSETS = ((1.80, 2.33, 2.81, .40), (1.75, 2.29, 2.79, .43),
                (1.76, 2.30, 2.80, .41), (1.76, 2.30, 2.81, .42))
REACTION_LEAD = .46
COIN_REACTIONS = {
    'lancer': ("* Three coins! I'm rich!", 1.52),
    'susie': ('* Sweet. Snack money.', 1.44),
}
ROLLS = [record['events'] for record in REPLAY['trace'] if record['action']['type'] == 'roll']
PATHS = {who: (STARTS[who], *(event['to'] for event in events if event['type'] == 'move'))
         for who, events in zip(PLAYERS, ROLLS, strict=True)}
COIN_DELTAS = {event['player']: event['amount'] for record in REPLAY['trace']
               for event in record['events'] if event['type'] == 'coins'}


def schedule_turns():
    """Keep each completed move on screen until its reward and reaction settle."""
    turns, reactions = [], {}
    begin = 4.34
    for who, events, offsets in zip(PLAYERS, ROLLS, TURN_OFFSETS, strict=True):
        spin, hit, move = (round(begin + value, 2) for value in offsets[:3])
        first = who == PLAYERS[0]
        turn = BoardTurn(who, begin, (spin,), (hit,), tuple(events[0]['values']), move, offsets[3],
                         0, len(PATHS[who]), banner_hold=0 if first else .10,
                         camera_duration=.65 if first else .53,
                         coin_delay=EVENT_PAYOUT if who == SPECIAL['player'] else .27)
        turns.append(turn)
        dialogue_end = None
        if who in COIN_REACTIONS and COIN_DELTAS[who] == 3:
            text, duration = COIN_REACTIONS[who]
            start = turn.after_award(REACTION_LEAD)
            dialogue_end = round(start + duration, 2)
            reactions[who] = dict(speaker=who, start=start, end=dialogue_end, text=text,
                                  portrait=f'{who}-laugh-face')
        begin = next_turn_start(turn, dialogue_end=dialogue_end)
    return tuple(turns), reactions


TURNS, AWARD_LINES = schedule_turns()
EVENT_TURN = next(turn for turn in TURNS if turn.who == SPECIAL['player'])
ROUND_COMPLETE = next_turn_start(TURNS[-1])
TEAM_ASSIGNMENT = round(ROUND_COMPLETE + .32, 2)
DRAW_READY = round(ROUND_COMPLETE + 1.21, 2)
BOARD_LINES = (
    dict(speaker='lancer', start=.65, end=2.25, text="* I'll have the whole menu!", portrait='lancer-laugh-face'),
    dict(speaker='flowery', start=2.43, end=4.22, text='* All of it? Coming right up!', portrait='flowery-face-open'),
    *AWARD_LINES.values(),
    dict(speaker='flowery', start=EVENT_TURN.land + .48, end=EVENT_TURN.land + 2.18,
         text=f"* {SPECIAL['prompt']}", portrait='flowery-face-open'),
    dict(speaker='noelle', start=EVENT_TURN.land + 2.29, end=EVENT_TURN.land + 3.61,
         text='* The middle one, please.', portrait='noelle-face'),
)


def event_coins(turn):
    count = min(8, COIN_DELTAS[turn.who])
    start = turn.land + FOOD_CLOSE + .06
    return tuple(start + index * .05 for index in range(count))


def board_events():
    events = [dict(t=0, type='board', starts=STARTS, rounds=REPLAY['initial']['rounds'])]
    for turn in TURNS:
        events.append(dict(t=turn.start, type='turn_camera', id=turn.who))
        path = PATHS[turn.who]
        delta = COIN_DELTAS[turn.who]
        for event in turn_events(turn, delta):
            if event['type'] == 'board_step':
                step = event['step']
                event.update(source=path[step - 1], node=path[step])
            elif event['type'] == 'board_land':
                event.update(node=path[-1], space=NODES[path[-1]]['type'])
            elif event['type'] == 'blue_coin':
                if turn.who == SPECIAL['player']:
                    event['type'] = 'food_reward'
                elif delta < 0:
                    event['type'] = 'red_coin'
            events.append(event)
    for offset, kind in ((FOOD_OPEN, 'food_event_open'), (FOOD_LOCK, 'food_select'),
                         (FOOD_REVEAL, 'food_reveal')):
        events.append(dict(t=round(EVENT_TURN.land + offset, 2), type=kind, id=SPECIAL['player'],
                           selected=SPECIAL['selected'], options=SPECIAL['options']))
    for offset in FOOD_FOCUS:
        events.append(dict(t=round(EVENT_TURN.land + offset, 2), type='food_focus', id=SPECIAL['player']))
    for t in event_coins(EVENT_TURN):
        events.append(dict(t=round(t + .22, 2), type='food_coin_contact', id=SPECIAL['player']))
    teams = tuple(tuple(who for who in PLAYERS if TEAM_COLORS[who] == color) for color in ('blue', 'red'))
    events.append(dict(t=ROUND_COMPLETE, type='round_complete', sides=teams))
    events.append(dict(t=TEAM_ASSIGNMENT, type='green_team_assign', id=SPECIAL['player'],
                       color=TEAM_COLORS[SPECIAL['player']], seed=REPLAY['grouping']['teamSeed']))
    return events


@lru_cache(maxsize=256)
def sprite(name, height):
    with Image.open(CAST / f'{name}.png') as source:
        art = source.convert('RGBA')
    art = art.crop(art.getbbox())
    return art.resize((max(1, round(art.width * height / art.height)), height), NEAR)


def project(x, y):
    # Translate the graph's half-scale local coordinates onto the native room floor.
    return (round((x - DINER['x']) / 2) + 180, round((y - DINER['y']) / 2) + 154)


def links(nodes):
    ids = {node['id'] for node in nodes}
    for source in nodes:
        for link in source['next']:
            target = link['to'] if isinstance(link, dict) else link
            if target in ids:
                yield source, NODES[target]


@lru_cache(maxsize=2)
def coin_sign(negative):
    image = stamp('board-minus' if negative else 'board-plus')
    return image.crop(image.getbbox()).resize((10, 5 if negative else 10), NEAR)


def draw_question(screen, x, y, height):
    ds_text(screen, '?', x + 1, y + 1, height=height, color='#245643', middle=True)
    ds_text(screen, '?', x, y, height=height, color='#fff9dd', middle=True)


class DinerBoard(PartyBoard):
    def __init__(self, sprite=sprite):
        self.players = PLAYERS
        self.heights = HEIGHTS
        self.sprite = sprite
        self.points = {node['id']: project(node['x'], node['y']) for node in GRAPH['spaces']}
        with Image.open(ROOT / 'assets' / DINER['asset']) as source:
            self.plate = source.convert('RGB')
        self.local = tuple(node for node in GRAPH['spaces'] if node['id'].startswith('diner-') and
                           0 <= self.points[node['id']][0] < self.plate.width and
                           0 <= self.points[node['id']][1] < self.plate.height)
        self.route = tuple(self.points[node['id']] for node in self.local)
        self.spaces = tuple(node['type'] for node in self.local)
        self.map = self.make_map()
        self.draw_local_route()

    def map_point(self, x, y):
        return 52 + (x - 150) * 134 / 450, 58 + (y - 230) * 63 / 214

    def make_map(self):
        image = checkered(('#f4e5e1', '#e7c9cf'))
        draw = ImageDraw.Draw(image)
        draw.rectangle((40, 30, 200, 154), fill='#d6aebd', outline='#a87698', width=1)
        visible = tuple(node for node in self.local if 150 <= self.points[node['id']][0] <= 600)
        for source, target in links(visible):
            start = self.map_point(*self.points[source['id']])
            end = self.map_point(*self.points[target['id']])
            draw.line((start, end), fill='#faede5', width=4)
        for node in visible:
            x, y = self.map_point(*self.points[node['id']])
            draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=SPACE_COLORS[node['type']])
            if node['id'] == SPECIAL['space']:
                draw_question(image, x, y - 5, height=9)
        ds_text(image, 'Second Diner', 120, 9, height=12, middle=True, color='#562742')
        return image

    def draw_local_route(self):
        draw = ImageDraw.Draw(self.plate)
        edges = [(self.points[a['id']], self.points[b['id']]) for a, b in links(self.local)]
        for a, b in edges:
            draw.line((a, b), fill='#6c3c4a', width=8)
            draw.line((a, b), fill='#f8d0a1', width=4)
        for node in self.local:
            x, y = self.points[node['id']]
            color = SPACE_COLORS[node['type']]
            draw.ellipse((x - 15, y - 7, x + 15, y + 8), fill='#4e292b')
            draw.ellipse((x - 15, y - 9, x + 15, y + 5), fill='#d8a273', outline='#fbd9a4')
            draw.ellipse((x - 12, y - 7, x + 12, y + 2), fill=color)
            draw.line((x - 6, y - 6, x + 5, y - 6), fill='#fff1ce')
            if node['id'] == SPECIAL['space']:
                draw.ellipse((x - 10, y - 27, x + 10, y - 8), fill='#327953', outline='#c3efb7')
                draw_question(self.plate, x, y - 26, height=15)

    def state(self, t):
        initial = REPLAY['initial']
        poses = {who: Pose(*self.points[STARTS[who]]) for who in PLAYERS}
        coins = {player['id']: player['coins'] for player in initial['players']}
        active = PLAYERS[0]
        roll = banner_age = None
        for turn in TURNS:
            if t < turn.start:
                break
            who = active = turn.who
            path = PATHS[who]
            if turn.spins[0] <= t < turn.move:
                age = t - turn.hits[0]
                face = ROLLING[int((t - turn.spins[0]) * 14) % len(ROLLING)] if age < 0 else turn.faces[0]
                roll = Roll(face, age)
                poses[who] = Pose(*self.points[path[0]], lift=15 * max(0, 1 - abs(age) / .21))
            if turn.move <= t < turn.land:
                offset = (t - turn.move) / turn.step
                step = min(turn.spaces - 1, int(offset))
                progress = min(1, offset - step)
                a, b = self.points[path[step]], self.points[path[step + 1]]
                x, y = point(a, b, smooth(progress))
                facing = ('right' if b[0] > a[0] else 'left') if abs(b[0] - a[0]) > abs(b[1] - a[1]) else (
                    'down' if b[1] > a[1] else 'up')
                poses[who] = Pose(x, y, facing, int(t * 13) % 4, 6 * sin(pi * progress))
                roll = Roll(turn.faces[0], t - turn.hits[0], turn.spaces - step)
            if t >= turn.land:
                recoil = 4 * max(0, 1 - abs(t - turn.award) / .18)
                poses[who] = Pose(*self.points[path[-1]], lift=recoil)
            if t >= turn.award:
                coins[who] += COIN_DELTAS[who]
            banner_age = visible_banner_age(t - turn.banner, turn.banner_hold)
        return BoardState(poses, coins, dict.fromkeys(PLAYERS, 0), active,
                          initial['round'], initial['rounds'], roll, banner_age)

    def camera(self, t, state):
        previous = OPENING_CAMERA
        for turn in TURNS:
            if state.active == turn.who:
                actor = state.poses[turn.who]
                focus = self.close_camera(actor.x, actor.y)
                progress = smooth((t - turn.start) / turn.camera_duration)
                return tuple(round(value) for value in point(previous, focus, progress))
            previous = self.close_camera(*self.points[PATHS[turn.who][-1]])

    def close_camera(self, x, y):
        return (
            max(0, min(self.plate.width - SIZE[0], x - 111)),
            max(0, min(self.plate.height - SIZE[1], y - 138)),
            SIZE[0],
        )

    def screens(self, t):
        state = self.state(t)
        left, top, width = self.camera(t, state)
        scale = SIZE[0] / width
        lower = self.plate.crop((left, top, left + width, top + round(SIZE[1] / scale)))
        lower = lower.resize(SIZE, NEAR)
        draw = ImageDraw.Draw(lower)
        positions = {who: ((pose.x - left) * scale, (pose.y - top) * scale)
                     for who, pose in state.poses.items()}
        for who, (x, y) in sorted(positions.items(), key=lambda item: item[1][1]):
            pose = state.poses[who]
            actor_name = f'{who}-{pose.facing}-{pose.stride}'
            reward_line = AWARD_LINES.get(who)
            if reward_line and reward_line['start'] <= t < reward_line['end']:
                actor_name = f'{who}-laugh-{int((t - reward_line["start"]) * 7) % 2}'
            elif who == 'lancer' and .65 <= t < 2.25:
                actor_name = f'lancer-laugh-{int(t * 7) % 2}'
            elif who == 'flowery' and 2.43 <= t < 4.22:
                actor_name = f'flowery-clap-{int(t * 7) % 4}'
            elif who == 'flowery' and TURNS[-1].land <= t < TURNS[-1].award + .29:
                actor_name = f'flowery-panic-{int((t - TURNS[-1].land) * 7) % 2}'
            draw.ellipse((x - 8 * scale, y - 3 * scale, x + 8 * scale, y + 2 * scale), fill='#693834')
            actor = self.sprite(actor_name, round(HEIGHTS[who] * max(.65, scale)))
            paste(lower, actor, x - actor.width / 2, y - actor.height - pose.lift * scale)
        if state.roll is not None:
            self._die(lower, *positions[state.active], state.roll, t)
        if state.banner_age is not None:
            self._turn_banner(lower, state.active, state.banner_age)
        for turn in TURNS:
            if turn == EVENT_TURN and FOOD_CLOSE <= t - turn.land < EVENT_PAYOUT + .58:
                self.draw_reward(lower, t, turn, left, top, event_coins(turn))
            elif turn != EVENT_TURN and turn.land <= t < turn.award + .58:
                self.draw_reward(lower, t, turn, left, top)
        age = t - EVENT_TURN.land
        if FOOD_OPEN <= age < FOOD_CLOSE:
            draw_food_event(lower, age, SPECIAL['options'], SPECIAL['selected'])
        colors = {}
        if EVENT_TURN.land <= t < TEAM_ASSIGNMENT:
            colors[SPECIAL['player']] = 'green'
        elif t >= TEAM_ASSIGNMENT:
            colors[SPECIAL['player']] = TEAM_COLORS[SPECIAL['player']]
        upper = self.upper(state, landing_colors=colors)
        if TEAM_ASSIGNMENT <= t < TEAM_ASSIGNMENT + .3:
            shine = int(245 * (1 - (t - TEAM_ASSIGNMENT) / .3))
            ImageDraw.Draw(upper).rounded_rectangle((5, 120, 58, 179), radius=8,
                                                    outline=(245, 224, max(145, shine)))
        return lower, upper

    def draw_reward(self, lower, t, turn, left, top, coin_starts=None):
        x, y = self.points[PATHS[turn.who][-1]]
        x, y = x - left, y - top
        delta = COIN_DELTAS[turn.who]
        if coin_starts is None:
            coin_starts = tuple(turn.land + .025 + index * .045 for index in range(abs(delta)))
        flight = .22 if turn == EVENT_TURN else .17
        for index, start in enumerate(coin_starts):
            age = (t - start) / flight
            if 0 <= age < 1:
                progress = age * age
                if delta < 0:
                    progress = 1 - progress
                offset = (index - 1) * 11 if turn != EVENT_TURN else (index % 4 - 1.5) * 10 * (1 - progress)
                centered(lower, resized('coin', 6 + round(3 * sin(pi * age)), 11),
                         x + offset, mix(y - 66, y - 17, progress))
        if t >= turn.award:
            label_y = y - 64 - 8 * smooth((t - turn.award) / .22)
            centered(lower, resized('coin', 12, 14), x - 15, label_y)
            centered(lower, coin_sign(delta < 0), x - 2, label_y)
            number(lower, abs(delta), x + 10, label_y - 7, height=14, kind='coins')
