"""A Flower Castle cold open and four-player Soap Surfers match."""

import argparse
from functools import lru_cache
from math import floor, pi, sin
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw

from mpds_ui import resized
from party_board import BoardState, CASTLE_LOOP, CASTLE_SPACES, PartyBoard, Pose, Roll
from party_reel import PartyReel
from reel_art import CHAPTER5, NEAR, ROOT, centered, mix, point, smooth, sprite, stylus
from study_cast import PLAYERS


TITLE = 'Flowery Waxed the Floor in Mario Party DS'
FPS = 60
DIALOGUE_RATE = 31
RULES, MATCH, RETURN, DURATION = 9.2, 12, 31.5, 36.5
DIE_START, DIE_HIT = 1.78, 2.56
SLIDE, CATCH = 3.65, 5.82
DIALOGUE = (
    {'speaker': 'flowery', 'start': .32, 'end': 1.73, 'text': 'I waxed the whole hall!'},
    {'speaker': 'ralsei', 'start': 1.85, 'end': 3.27, 'text': "It's very shiny, Flowery.", 'portrait': 'ralsei-smile-face'},
    {'speaker': 'queen', 'start': 4.16, 'end': 5.30, 'text': 'My Throne Is Slipping', 'portrait': 'queen-shocked-face'},
    {'speaker': 'gerson', 'start': 5.44, 'end': 6.68, 'text': "That's soap, Your Majesty.", 'portrait': 'gerson-laugh-face'},
    {'speaker': 'ralsei', 'start': 6.80, 'end': 7.72, 'text': "Let's all try it!", 'portrait': 'ralsei-smile-face'},
    {'speaker': 'flowery', 'start': 7.85, 'end': 9.08, 'text': 'Last one floating wins!'},
    {'speaker': 'flowery', 'start': 14.74, 'end': 15.67, 'text': 'Hee hee!'},
    {'speaker': 'ralsei', 'start': 17.1, 'end': 18.40, 'text': "Whoa, I'm still going!", 'portrait': 'ralsei-surprised-face'},
    {'speaker': 'gerson', 'start': 23.28, 'end': 24.60, 'text': 'Easy does it, kids.'},
    {'speaker': 'flowery', 'start': 32.08, 'end': 33.60, 'text': 'Next round, the stairs!'},
    {'speaker': 'ralsei', 'start': 34.12, 'end': 36.26, 'text': "Let's start with a towel."},
)
HEIGHTS = dict(queen=38, gerson=34, flowery=36, ralsei=36)
STARTING_NODES = dict(queen=7, gerson=10, flowery=9, ralsei=1)
START_COINS = dict(queen=14, gerson=16, flowery=27, ralsei=19)
WIN_SCREEN, PAYOUT, BONUS = 30.2, 30.52, 10
STEPS = ((3.12, 3.70), (3.70, 4.24), (4.24, 4.80))
SOAP_ART = ROOT / 'assets/mpds/soap'


def build(fps=FPS):
    """Use one absolute timeline for the film and its audio mix."""
    from soap_surfers import simulate

    frames, relative_events = simulate(fps, RETURN - MATCH)
    events = [
        dict(t=0, type='phase', phase='castle'),
        dict(t=DIE_START, type='die', action='start', id='ralsei'),
        dict(t=DIE_HIT, type='die', action='hit', id='ralsei', face=3),
        dict(t=SLIDE, type='soap_slide', id='flowery'),
        dict(t=CATCH, type='soap_catch', id='ralsei'),
        dict(t=RULES, type='phase', phase='rules'),
        dict(t=RULES, type='rules', title='Soap Surfers'),
        dict(t=MATCH, type='phase', phase='soap'),
        dict(t=MATCH, type='input', action='start_minigame', id='ralsei'),
        dict(t=RETURN, type='phase', phase='return'),
        dict(t=32.25, type='soap_drop', id='ralsei'),
    ]
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
        if t < RULES:
            phase = 'castle'
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


def walking(t, duration, start, end):
    u = smooth(t / duration)
    x, y = point(start, end, u)
    if 0 < u < 1:
        facing = 'right' if end[0] > start[0] else 'left'
        return Pose(x, y, facing, int(t * 15) % 4, abs(sin(t * 13)) * 5)
    return Pose(x, y)


class Castle:
    def __init__(self):
        with Image.open(CHAPTER5 / 'board.png') as plate:
            self.board = PartyBoard(plate, CASTLE_LOOP, CASTLE_SPACES, PLAYERS, sprite, HEIGHTS)

    def state(self, t, winner):
        spots = {who: self.board.route_position(node) for who, node in STARTING_NODES.items()}
        poses = {who: Pose(*xy) for who, xy in spots.items()}
        coins = START_COINS.copy()
        if t >= PAYOUT:
            coins[winner] += BONUS
        if t >= RETURN:
            poses.update(queen=Pose(249, 82, 'left'), gerson=Pose(161, 94, 'right'),
                         ralsei=walking(t - 33.88, .77, (203, 111), (228, 104)),
                         flowery=walking(t - 32.24, 1.25, (199, 89), (280, 106)))
            return BoardState(poses, coins, dict.fromkeys(PLAYERS, 0), 'ralsei', 5, 10)

        roll = None
        for i, (start, end) in enumerate(STEPS):
            if start <= t < end:
                node = STARTING_NODES['ralsei'] + i
                u = (t - start) / (end - start)
                x, y = self.board.route_position(node, smooth(u))
                poses['ralsei'] = Pose(x, y, 'right', int(t * 15) % 4, 12 * sin(pi * u))
                roll = Roll(3, t - DIE_HIT, 3 - i)
        if DIE_START <= t < STEPS[0][0]:
            face = (4, 8, 2, 6, 9, 7, 5)[floor((t - DIE_START) * 13) % 7] if t < DIE_HIT else 3
            roll = Roll(face, t - DIE_HIT)
            jump = 15 * max(0, 1 - abs(t - DIE_HIT) / .23)
            poses['ralsei'] = Pose(*spots['ralsei'], lift=jump)
        if t >= STEPS[-1][1]:
            last = self.board.route_position(STARTING_NODES['ralsei'] + 3)
            poses['ralsei'] = walking(t - STEPS[-1][1], CATCH - STEPS[-1][1], last, (230, 111))

        if t >= SLIDE:
            poses['queen'] = walking(t - SLIDE, .77, spots['queen'], (247, 73))
            poses['gerson'] = walking(t - 4.22, 1.4, spots['gerson'], (168, 89))
        if 3.11 <= t < 5.3:
            poses['flowery'] = walking(t - 3.11, SLIDE - 3.11, spots['flowery'], (154, 100))
        elif t >= 5.3:
            poses['flowery'] = walking(t - 5.3, 1.55, (154, 100), (245, 83))
        if .32 <= t < 1.73 or 7.85 <= t < 9.08:
            p = poses['flowery']
            poses['flowery'] = Pose(p.x, p.y, lift=abs(sin(t * 17)) * 2,
                                    sprite=f'flowery-clap-{int(t * 12) % 4}')
        return BoardState(poses, coins, dict.fromkeys(PLAYERS, 0), 'ralsei', 4, 10, roll, t - .08)

    @staticmethod
    def bar(image, x, y, color, t):
        bar = soap_art(f'soap-{color}')
        bar = bar.resize((21, max(5, round(bar.height * 21 / bar.width))), NEAR)
        centered(image, bar.rotate(round(15 * sin(t * 13)), NEAR, expand=True), x, y)

    def screens(self, t, winner):
        state = self.state(t, winner)
        focus = state.poses['ralsei'].x
        if t >= RETURN:
            focus = mix(focus, state.poses['flowery'].x, .56)
        panel, camera = self.board.lower(state, t, focus=focus)
        if SLIDE <= t < CATCH:
            slide = (t - SLIDE) / (CATCH - SLIDE)
            x, y = point((154, 104), (230, 107), 1 - (1 - slide) ** 1.28)
            draw = ImageDraw.Draw(panel)
            for shift in (0, 6, 12):
                draw.line((x - camera - 15 - shift, y + 4 + shift / 5,
                           x - camera - 5 - shift, y + 4 + shift / 5), fill='#edb1a7')
            self.bar(panel, x - camera, y, 'yellow', t)
        elif CATCH <= t < RULES:
            self.bar(panel, 236 - camera, 85, 'yellow', 0)
            if t - CATCH < .23:
                for dx in (-12, 12):
                    centered(panel, resized('star', 8, 8), 236 + dx - camera, 78 - 20 * (t - CATCH))
        if 32.25 <= t < 33.57:
            u = (t - 32.25) / 1.32
            self.bar(panel, mix(212, 291, u) - camera,
                     101 - 17 * abs(sin(u * 2 * pi)) * (1 - u), 'yellow', t)
        return panel, self.board.upper(state)


class Film:
    def __init__(self):
        from soap_surfers import SoapSurfers

        self.frames, self.events = build()
        self.castle = Castle()
        self.game = SoapSurfers(sprite)
        self.layout = PartyReel(sprite, DIALOGUE_RATE)
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
