"""A Flower Castle cold open and four-player Soap Surfers match."""

import argparse
from functools import lru_cache
from math import floor, pi, sin
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw

from mpds_ui import ds_text, number, resized
from party_board import BoardState, CASTLE_LOOP, CASTLE_SPACES, PartyBoard, Pose, Roll
from party_reel import PartyReel
from reel_art import CHAPTER5, NEAR, ROOT, centered, mix, point, smooth, sprite, stylus
from study_cast import PLAYERS


TITLE = 'Ralsei Found a Lucky Space in Mario Party DS'
GAME_TITLE = 'Soap Surfers'
FPS = 60
DIALOGUE_RATE = 31
DRAW, LOCK, RULES, MATCH, RETURN, DURATION = 11.2, 12.95, 15.25, 19, 40.75, 45
DIE_START, DIE_HIT, FACE = 1.87, 2.72, 3
STEPS = ((3.43, 4.08), (4.08, 4.73), (4.73, 5.40))
LAND = STEPS[-1][1]
GUEST_ENTER, GUEST_LEAVE = 5.58, 10.18
COIN_DROP, COIN_FLIGHT, COIN_STAGGER, EVENT_COINS = 8.43, .42, .07, 10
COIN_RECEIVE = round(COIN_DROP + COIN_FLIGHT + (EVENT_COINS - 1) * COIN_STAGGER, 2)
DIALOGUE = (
    {'speaker': 'seth', 'start': 6.10, 'end': 7.25, 'text': 'The toll is ten coins.'},
    {'speaker': 'aqua', 'start': 7.37, 'end': 8.42, 'text': 'No, we pay HIM!'},
    {'speaker': 'flowery', 'start': MATCH + 2.74, 'end': MATCH + 3.67, 'text': 'Hee hee!'},
    {'speaker': 'ralsei', 'start': MATCH + 5.10, 'end': MATCH + 6.40,
     'text': "Whoa, I'm still going!", 'portrait': 'ralsei-surprised-face'},
    {'speaker': 'gerson', 'start': MATCH + 11.28, 'end': MATCH + 12.60, 'text': 'Easy does it, kids.'},
    {'speaker': 'flowery', 'start': RETURN + 1.38, 'end': RETURN + 2.70, 'text': 'Best two outta three?'},
)
HEIGHTS = dict(queen=38, gerson=34, flowery=36, ralsei=36, seth=38, aqua=30)
STARTING_NODES = dict(queen=7, gerson=10, flowery=9, ralsei=1)
START_COINS = dict(queen=14, gerson=16, flowery=27, ralsei=19)
EVENT_NODE = (STARTING_NODES['ralsei'] + FACE) % len(CASTLE_LOOP)
WIN_SCREEN, PAYOUT, BONUS = MATCH + 18.2, MATCH + 18.78, 10
SOAP_ART = ROOT / 'assets/mpds/soap'


def build(fps=FPS):
    """Use one absolute timeline for the film and its audio mix."""
    from soap_surfers import simulate

    frames, relative_events = simulate(fps, RETURN - MATCH)
    events = [
        dict(t=0, type='phase', phase='castle'),
        dict(t=DIE_START, type='die', action='start', id='ralsei'),
        dict(t=DIE_HIT, type='die', action='hit', id='ralsei', face=FACE),
        dict(t=LAND, type='board_event', action='land', id='ralsei', space=EVENT_NODE),
        dict(t=GUEST_ENTER, type='board_event', action='guests_enter', guests=['seth', 'aqua']),
        dict(t=COIN_DROP, type='board_event', action='coins_drop', id='ralsei'),
        dict(t=COIN_RECEIVE, type='board_reward', id='ralsei', coins=EVENT_COINS),
        dict(t=GUEST_LEAVE + .62, type='board_event', action='guests_leave', guests=['seth', 'aqua']),
        dict(t=DRAW, type='phase', phase='selection'),
        dict(t=DRAW + .30, type='roulette', action='start'),
        dict(t=LOCK, type='roulette', action='lock', title=GAME_TITLE),
        dict(t=RULES, type='phase', phase='rules'),
        dict(t=RULES, type='rules', title=GAME_TITLE),
        dict(t=MATCH, type='phase', phase='soap'),
        dict(t=MATCH, type='input', action='start_minigame', id='ralsei'),
        dict(t=RETURN, type='phase', phase='return'),
    ]
    for index in range(EVENT_COINS):
        contact = round(COIN_DROP + index * COIN_STAGGER + COIN_FLIGHT, 2)
        events.append(dict(t=contact, type='coin_contact', id='ralsei'))
    for step, (_, time) in enumerate(STEPS, 1):
        events.append(dict(t=time, type='step', id='ralsei',
                           space=(STARTING_NODES['ralsei'] + step) % len(CASTLE_LOOP)))
    winner = next(event['id'] for event in relative_events if event['type'] == 'win')
    events.append(dict(t=PAYOUT, type='party_reward', id=winner, coins=BONUS))
    for event in relative_events:
        events.append({**event, 't': round(MATCH + event['t'], 6), 'phase': 'soap'})
    game_frames = []
    for i in range(round(DURATION * fps)):
        t = i / fps
        if t < DRAW:
            phase = 'castle'
        elif t < RULES:
            phase = 'selection'
        elif t < MATCH:
            phase = 'rules'
        elif t < RETURN:
            phase = 'soap'
        else:
            phase = 'return'
        local = i - round(MATCH * fps)
        game_frames.append(dict(t=t, u=t - MATCH, phase=phase,
                                soap=frames[max(0, min(local, len(frames) - 1))]))
    return game_frames, sorted(events, key=lambda event: event['t'])


@lru_cache(maxsize=16)
def soap_art(name):
    return Image.open(SOAP_ART / f'{name}.png').convert('RGBA')


@lru_cache(maxsize=32)
def episode_sprite(name, height):
    if not name.startswith(('seth-', 'aqua-')):
        return sprite(name, height)
    with Image.open(CHAPTER5 / 'guests' / f'{name}.png') as source:
        image = source.convert('RGBA')
    image = image.crop(image.getbbox())
    return image.resize((round(image.width * height / image.height), height), NEAR)


class Castle:
    def __init__(self):
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
        if t >= PAYOUT:
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
        if GUEST_ENTER <= t < GUEST_LEAVE + .62:
            enter = smooth((t - GUEST_ENTER) / .55)
            leave = smooth((t - GUEST_LEAVE) / .62)
            progress = enter - leave
            for who, origin, target, inbound, outbound in (
                ('seth', (119, 87), (158, 104), 'right', 'left'),
                ('aqua', (266, 85), (237, 107), 'left', 'right'),
            ):
                x, y = point(origin, target, progress)
                hop = sin(pi * progress) * (8 if who == 'aqua' else 3)
                direction = outbound if leave else inbound
                stride = int(t * 12) % 4 if progress < 1 else 0
                poses[who] = Pose(x, y, direction, stride, hop)
        if RETURN + 1.26 <= t < RETURN + 2.75:
            p = poses['flowery']
            poses['flowery'] = Pose(p.x, p.y, sprite=f'flowery-clap-{int(t * 12) % 4}')
        turn = 5 if t >= RETURN else 4
        return BoardState(poses, coins, dict.fromkeys(PLAYERS, 0), 'ralsei', turn, 10, roll, t - .08)

    def screens(self, t, winner):
        state = self.state(t, winner)
        focus = state.poses['ralsei'].x
        if t >= RETURN:
            focus = mix(focus, 166, smooth((t - RETURN - .20) / 1.08))
        panel, camera = self.board.lower(state, t, focus=focus)
        x, y = self.board.route_position(EVENT_NODE)
        x -= camera
        if LAND <= t < GUEST_ENTER + .31:
            age = t - LAND
            radius = 12 + 20 * age
            draw = ImageDraw.Draw(panel)
            draw.arc((x - radius, y - radius / 3 - 1, x + radius, y + radius / 3 + 1),
                     9, 172, fill='#c9f4a4', width=2)
            ds_text(panel, '?', x, y - 58 - 12 * age, height=15, middle=True, outline='#315434')
            for side in (-1, 1):
                centered(panel, resized('star', 7, 7), x + side * (14 + 18 * age), y - 9 - 23 * age)
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
            centered(panel, resized('coin', 12, 15), x - 16, y - offset)
            centered(panel, resized('board-plus', 10, 12), x - 2, y - offset)
            number(panel, EVENT_COINS, x + 15, y - offset - 8, height=16, kind='coins')


class Film:
    def __init__(self):
        from soap_surfers import SoapSurfers

        self.frames, self.events = build()
        self.castle = Castle()
        self.game = SoapSurfers(sprite)
        self.layout = PartyReel(episode_sprite, DIALOGUE_RATE)
        self.winner = next(event['id'] for event in self.events if event['type'] == 'win')
        self.preview, _ = self.game.screens(self.frames[round(MATCH * FPS)])

    def render(self, frame):
        t, phase = frame['t'], frame['phase']
        if phase == 'soap':
            lower, upper = self.game.screens(frame)
            if t >= WIN_SCREEN:
                upper = lower
                state = self.castle.state(t, self.winner)
                lower = self.castle.board.results(state, self.winner, BONUS if t >= PAYOUT else 0)
                if t > RETURN - .25:
                    u = smooth((t - RETURN + .25) / .25)
                    stylus(lower, 120 + 28 * (1 - u), 168 + 17 * (1 - u), press=u)
        elif phase == 'rules':
            lower, upper = self.layout.rules(self.preview, soap_art('title'), soap_art('rules-bottom'),
                                             PLAYERS, MATCH - t)
        else:
            lower, upper = self.castle.screens(t, self.winner)
            if phase == 'selection':
                self.layout.roulette(lower, GAME_TITLE, t - DRAW, LOCK - DRAW)
        return self.layout.compose(lower, upper, t, (RULES, MATCH, RETURN), DIALOGUE)


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
