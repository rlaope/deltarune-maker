"""A Flower Castle cold open and four-player Soap Surfers match."""

import argparse
from functools import lru_cache
from math import floor, pi, sin
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw

from board_event import COIN_DROP, COIN_RECEIVE, EVENT_DIALOGUE, EVENT_END, action_events, draw_action, event_poses
from mpds_ui import ds_text, number, resized
from party_board import BoardState, CASTLE_LOOP, CASTLE_SPACES, PartyBoard, Pose, Roll
from party_reel import PartyReel
from reel_art import CHAPTER5, NEAR, ROOT, centered, mix, smooth, sprite, stylus
from study_cast import PLAYERS


TITLE = 'Soap Surfers Got Out of Hand in Mario Party DS'
GAME_TITLE = 'Soap Surfers'
FPS = 60
DIALOGUE_RATE = 31
DRAW = round(EVENT_END + .65, 2)
LOCK, RULES, MATCH = (round(DRAW + gap, 2) for gap in (1.75, 4.25, 8.50))
RACE_WINDOW = 34
DIE_START, DIE_HIT, FACE = 1.87, 2.72, 3
STEPS = ((3.43, 4.08), (4.08, 4.73), (4.73, 5.40))
LAND = STEPS[-1][1]
COIN_FLIGHT, COIN_STAGGER, EVENT_COINS = .42, .07, 10
BONUS = 10
HEIGHTS = dict(queen=38, gerson=34, flowery=36, ralsei=36, seth=38, aqua=30)
STARTING_NODES = dict(queen=7, gerson=10, flowery=9, ralsei=1)
START_COINS = dict(queen=14, gerson=16, flowery=27, ralsei=19)
EVENT_NODE = (STARTING_NODES['ralsei'] + FACE) % len(CASTLE_LOOP)
SOAP_ART = ROOT / 'assets/mpds/soap'


def build(fps=FPS):
    """Use one absolute timeline for the film and its audio mix."""
    from soap_surfers import simulate

    frames, relative_events = simulate(fps, RACE_WINDOW)
    victory = next(event for event in relative_events if event['type'] == 'win')
    win = MATCH + victory['t']
    payout = round(win + .64, 6)
    return_time = round((win + 3.70) * fps) / fps
    duration = return_time + 4.75
    if abs(COIN_DROP + COIN_FLIGHT + (EVENT_COINS - 1) * COIN_STAGGER - COIN_RECEIVE) > .001:
        raise ValueError('Final coin contact must align with the board reward')
    events = [
        dict(t=0, type='phase', phase='castle'),
        dict(t=DIE_START, type='die', action='start', id='ralsei'),
        dict(t=DIE_HIT, type='die', action='hit', id='ralsei', face=FACE),
        dict(t=LAND, type='board_event', action='land', id='ralsei', space=EVENT_NODE),
        dict(t=COIN_DROP, type='board_event', action='coins_drop', id='ralsei'),
        dict(t=COIN_RECEIVE, type='board_reward', id='ralsei', coins=EVENT_COINS),
        dict(t=DRAW, type='phase', phase='selection'),
        dict(t=DRAW + .30, type='roulette', action='start'),
        dict(t=LOCK, type='roulette', action='lock', title=GAME_TITLE),
        dict(t=RULES, type='phase', phase='rules'),
        dict(t=RULES, type='rules', title=GAME_TITLE),
        dict(t=MATCH, type='phase', phase='soap'),
        dict(t=MATCH, type='input', action='start_minigame', id='ralsei'),
        dict(t=return_time, type='phase', phase='return'),
        dict(t=payout, type='party_reward', id=victory['id'], coins=BONUS),
    ]
    events.extend(action_events())
    for index in range(EVENT_COINS):
        contact = round(COIN_DROP + index * COIN_STAGGER + COIN_FLIGHT, 2)
        events.append(dict(t=contact, type='coin_contact', id='ralsei'))
    for step, (_, time) in enumerate(STEPS, 1):
        events.append(dict(t=time, type='step', id='ralsei',
                           space=(STARTING_NODES['ralsei'] + step) % len(CASTLE_LOOP)))
    for event in relative_events:
        events.append({**event, 't': round(MATCH + event['t'], 6), 'phase': 'soap'})
    game_frames = []
    match_frame = round(MATCH * fps)
    for i in range(round(duration * fps)):
        t = i / fps
        if t < DRAW:
            phase = 'castle'
        elif t < RULES:
            phase = 'selection'
        elif i < match_frame:
            phase = 'rules'
        elif t < return_time:
            phase = 'soap'
        else:
            phase = 'return'
        local = i - match_frame
        game_frames.append(dict(t=t, u=local / fps, phase=phase,
                                soap=frames[max(0, min(local, len(frames) - 1))]))
    return game_frames, sorted(events, key=lambda event: event['t'])


def dialogue(events):
    return_time = next(event['t'] for event in events if event.get('phase') == 'return')
    lines = [
        {'speaker': 'ralsei', 'start': .49, 'end': 1.68, 'text': 'Alright, my turn!',
         'portrait': 'ralsei-smile-face'},
        *EVENT_DIALOGUE,
    ]
    calls = {
        'queen': ('Watch This', 'queen-smug-face'),
        'ralsei': ('A little fire!', 'ralsei-worried-face'),
        'gerson': ("My turn, kid.", 'gerson-laugh-face'),
        'flowery': ('JARONA!', 'flowery-face'),
    }
    last_hammer = next((event for event in reversed(events)
                        if event['type'] == 'skill_release' and event['skill'] == 'hammer'), None)
    spoken = set()
    for event in events:
        if event['type'] != 'skill_release':
            continue
        who = event['id']
        counter = event is last_hammer and who in spoken
        if who == 'flowery' and event['skill'] != 'jarona':
            continue
        if who != 'flowery' and who in spoken and not counter:
            continue
        text, portrait = calls[who]
        time = event['t']
        start = time - (.22 if who == 'flowery' else .62)
        end = time + (1.00 if who == 'flowery' else .53)
        if counter:
            text = 'Back at ya!'
            start = time - .43
        if lines[-1]['end'] > start:
            continue
        lines.append({'speaker': who, 'start': start, 'end': end, 'text': text,
                      'portrait': portrait, 'voice': who != 'flowery'})
        spoken.add(who)
    lines.extend((
        {'speaker': 'flowery', 'start': return_time + 1.02, 'end': return_time + 2.39,
         'text': 'Best two outta three?'},
        {'speaker': 'gerson', 'start': return_time + 2.54, 'end': return_time + 4.15,
         'text': 'Lemme dry off first.', 'portrait': 'gerson-laugh-face'},
    ))
    return tuple(lines)


@lru_cache(maxsize=16)
def soap_art(name):
    return Image.open(SOAP_ART / f'{name}.png').convert('RGBA')


@lru_cache(maxsize=48)
def episode_sprite(name, height):
    special = CHAPTER5 / 'action' / f'{name}.png'
    if special.is_file():
        path = special
    elif name.startswith(('seth-', 'aqua-')):
        path = CHAPTER5 / 'guests' / f'{name}.png'
    else:
        return sprite(name, height)
    with Image.open(path) as source:
        image = source.convert('RGBA')
    image = image.crop(image.getbbox())
    return image.resize((max(1, round(image.width * height / image.height)), height), NEAR)


@lru_cache(maxsize=1)
def soap_rules():
    panel = soap_art('rules-bottom').copy()
    centered(panel, resized('button-a', 10, 10), 28, 139)
    ds_text(panel, 'Use skill', 37, 132, height=11, color='#282030')
    return panel


class Castle:
    def __init__(self, return_time, payout):
        self.return_time = return_time
        self.payout = payout
        with Image.open(CHAPTER5 / 'board.png') as plate:
            self.board = PartyBoard(plate, CASTLE_LOOP, CASTLE_SPACES, PLAYERS, episode_sprite, HEIGHTS)
        if CASTLE_SPACES[EVENT_NODE] != 'event':
            raise ValueError('The toll only triggers on the question-mark space')

    def state(self, t, winner):
        spots = {who: self.board.route_position(node) for who, node in STARTING_NODES.items()}
        poses = {who: Pose(*xy) for who, xy in spots.items()}
        coins = START_COINS.copy()
        if t >= COIN_RECEIVE:
            coins['ralsei'] += EVENT_COINS
        if t >= self.payout:
            coins[winner] += BONUS

        roll = None
        for i, (start, end) in enumerate(STEPS):
            if start <= t < end:
                node = STARTING_NODES['ralsei'] + i
                u = (t - start) / (end - start)
                x, y = self.board.route_position(node, smooth(u))
                poses['ralsei'] = Pose(x, y, 'right', int(t * 15) % 4, 12 * sin(pi * u))
                roll = Roll(FACE, t - DIE_HIT, FACE - i)
        if DIE_START <= t < STEPS[0][0]:
            face = (4, 8, 2, 6, 9, 7, 5)[floor((t - DIE_START) * 13) % 7] if t < DIE_HIT else FACE
            roll = Roll(face, t - DIE_HIT)
            jump = 15 * max(0, 1 - abs(t - DIE_HIT) / .23)
            poses['ralsei'] = Pose(*spots['ralsei'], lift=jump)
        if t >= LAND:
            x, y = self.board.route_position(EVENT_NODE)
            lift = 7 * sin(pi * (t - COIN_RECEIVE) / .32) if COIN_RECEIVE <= t < COIN_RECEIVE + .32 else 0
            poses['ralsei'] = Pose(x, y, lift=lift)
        if LAND <= t < EVENT_END:
            event_poses(poses, t, self.board.route_position(EVENT_NODE))
        if self.return_time + .88 <= t < self.return_time + 2.45:
            p = poses['flowery']
            poses['flowery'] = Pose(p.x, p.y, sprite=f'flowery-clap-{int(t * 12) % 4}')
        turn = 5 if t >= self.return_time else 4
        return BoardState(poses, coins, dict.fromkeys(PLAYERS, 0), 'ralsei', turn, 10, roll, t - .08)

    def screens(self, t, winner):
        state = self.state(t, winner)
        focus = state.poses['ralsei'].x
        if t >= self.return_time:
            focus = mix(focus, 166, smooth((t - self.return_time - .20) / 1.08))
        panel, camera = self.board.lower(state, t, focus=focus)
        x, y = self.board.route_position(EVENT_NODE)
        x -= camera
        if LAND <= t < LAND + .49:
            age = t - LAND
            radius = 12 + 20 * age
            draw = ImageDraw.Draw(panel)
            draw.arc((x - radius, y - radius / 3 - 1, x + radius, y + radius / 3 + 1),
                     9, 172, fill='#c9f4a4', width=2)
            ds_text(panel, '?', x, y - 58 - 12 * age, height=15, middle=True, outline='#315434')
            for side in (-1, 1):
                centered(panel, resized('star', 7, 7), x + side * (14 + 18 * age), y - 9 - 23 * age)
        draw_action(panel, camera, t, (x + camera, y))
        if COIN_DROP <= t < COIN_RECEIVE + .85:
            self.coin_award(panel, x, y, t)
        return panel, self.board.upper(state)

    @staticmethod
    def coin_award(panel, x, y, t):
        for index in range(EVENT_COINS):
            age = (t - COIN_DROP - index * COIN_STAGGER) / COIN_FLIGHT
            if 0 <= age < 1:
                dx = (index % 5 - 2) * 11 * (1 - age)
                width = 3 + round(7 * abs(sin((age + index / 4) * 2 * pi)))
                centered(panel, resized('coin', width, 12), x + dx, mix(y - 93, y - 21, age * age))
        age = t - COIN_RECEIVE
        if 0 <= age < .85:
            offset = 47 + 12 * smooth(age / .26)
            x -= 25
            centered(panel, resized('coin', 12, 15), x - 16, y - offset)
            centered(panel, resized('board-plus', 10, 12), x - 2, y - offset)
            number(panel, EVENT_COINS, x + 15, y - offset - 8, height=16, kind='coins')


class Film:
    def __init__(self):
        from soap_surfers import SoapSurfers

        self.frames, self.events = build()
        self.win = next(event for event in self.events if event['type'] == 'win')
        self.payout = next(event['t'] for event in self.events if event['type'] == 'party_reward')
        self.return_time = next(event['t'] for event in self.events if event.get('phase') == 'return')
        self.dialogue = dialogue(self.events)
        self.castle = Castle(self.return_time, self.payout)
        self.game = SoapSurfers(episode_sprite)
        self.layout = PartyReel(episode_sprite, DIALOGUE_RATE)
        self.winner = self.win['id']
        self.preview, _ = self.game.screens(self.frames[round(MATCH * FPS)])

    def render(self, frame):
        t, phase = frame['t'], frame['phase']
        if phase == 'soap':
            lower, upper = self.game.screens(frame)
            if t >= self.win['t']:
                upper = lower
                state = self.castle.state(t, self.winner)
                lower = self.castle.board.results(state, self.winner, BONUS if t >= self.payout else 0)
                if t > self.return_time - .25:
                    u = smooth((t - self.return_time + .25) / .25)
                    stylus(lower, 120 + 28 * (1 - u), 168 + 17 * (1 - u), press=u)
        elif phase == 'rules':
            lower, upper = self.layout.rules(self.preview, soap_art('title'), soap_rules(),
                                             PLAYERS, MATCH - t)
        else:
            lower, upper = self.castle.screens(t, self.winner)
            if phase == 'selection':
                self.layout.roulette(lower, GAME_TITLE, t - DRAW, LOCK - DRAW)
        return self.layout.compose(lower, upper, t, (RULES, MATCH, self.return_time), self.dialogue)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stills', type=float, nargs='+')
    parser.add_argument('--audio', type=Path, default=ROOT / 'out/mix.wav')
    parser.add_argument('--output', type=Path)
    options = parser.parse_args()
    film = Film()
    if options.stills:
        for time in options.stills:
            frame = film.frames[min(len(film.frames) - 1, max(0, round(time * FPS)))]
            film.render(frame).resize((540, 960), NEAR).save(ROOT / f'qa/soap-{time:05.2f}.png')
        return
    if not options.output:
        parser.error('--output is required')
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-n', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
               '-s', '270x480', '-r', str(FPS), '-i', '-', '-i', str(options.audio),
               '-vf', 'scale=2160:3840:flags=neighbor:in_range=full:out_range=tv:out_color_matrix=bt709,format=yuv420p',
               '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '15',
               '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
               '-bsf:v', 'h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0',
               '-c:a', 'aac', '-b:a', '320k', '-movflags', '+faststart', str(options.output)]
    with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
        for i, frame in enumerate(film.frames):
            encoder.stdin.write(film.render(frame).tobytes())
            if i % 360 == 0:
                print(f'{i}/{len(film.frames)}', flush=True)
        encoder.stdin.close()
        if encoder.wait():
            raise RuntimeError('Soap Surfers encoding failed')


if __name__ == '__main__':
    main()
