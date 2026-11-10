"""Render the Boo Tag episode as a title-free dual-screen short."""

import argparse
from functools import lru_cache
import json
from math import pi, sin
from random import Random

from PIL import Image, ImageDraw

from boo_board import (BANNER, BOARD_LINES, BOO_APPEAR, BOO_HIT, CHEST_OPEN, COIN_HITS, COIN_LOSS,
                       COIN_LOSS_TIME, DIE_HIT, DIE_START, DRAW_READY, LAND, MOVE,
                       PLAYERS, REWARD, ROLL, STEP_TIME, Courtyard, board_round_events, sprite)
from boo_game import BooGame, LIMIT, READY
from mpds_ui import ds_text, number, resized
from party_reel import ShortsReel
from reel_art import NEAR, ROOT, SIZE, centered, mix, smooth
from shorts_export import start_encoder


FPS = 60
TEXT_RATE = 27
DRAW = DRAW_READY
LOCK, RULES, MATCH = (round(DRAW + offset, 2) for offset in (1.70, 3.36, 7.66))
GO = round(MATCH + READY, 6)
FINISH = round(GO + LIMIT, 6)
RESULT = round(FINISH + 1.65, 6)
WIN_REVEAL = round(RESULT + 1.94, 6)
RETURN = round(WIN_REVEAL + 3.68, 6)
PAYOUT = round(RETURN + 1.13, 6)
DURATION = round((RETURN + 3.15) * FPS) / FPS
CUTS = (RULES, MATCH, RETURN)
VERSION = 'v5'
SHORT_SIZE = ShortsReel.size
EXPORT_SCALE = 8
NATIVE = ROOT / 'assets/boo-native'
DRAW_POOL = ('Camera Shy', 'Boo Tag', 'Rail Riders', 'Shortcut Circuit', 'Soap Surfers', 'Trash Landing')
# Recorded four-player draw used for this episode.
DRAW_SEED = 813


def line(speaker, start, end, text, face):
    return dict(speaker=speaker, start=start, end=end, text=f'* {text}',
                portrait=f'{speaker}-{face}')


def lines(adoption, shortcut):
    cues = list(BOARD_LINES)
    if shortcut is not None and shortcut < adoption + 1.70:
        cues.append(line('susie', shortcut - .72, shortcut + .32, 'Shortcut!', 'face'))
    cues.extend((
        line('ralsei', adoption + .16, adoption + 2.27, 'You can stay with me.', 'smile-face'),
        line('ralsei', WIN_REVEAL + 1.23, WIN_REVEAL + 3.50,
             'Can we play again?', 'smile-face'),
    ))
    return tuple(cues)

def board_events():
    base = [
        (0, 'board'), (BANNER + .05, 'turn_banner'), (DIE_START, 'die_spin'),
        (DIE_HIT, 'die_hit'), (LAND, 'board_land'), (CHEST_OPEN, 'chest_open'),
        (BOO_APPEAR, 'board_boo'), (BOO_HIT, 'board_hit'),
        (DRAW, 'draw'), (DRAW + .30, 'roulette_spin'), (LOCK, 'roulette_lock'),
        (RULES, 'rules'), (MATCH - .17, 'confirm'), (MATCH, 'arena_open'),
        (RESULT, 'results'), (WIN_REVEAL, 'winner_reveal'), (RETURN, 'return'),
        (PAYOUT, 'coin_award'),
    ]
    base.extend((MOVE + index * STEP_TIME, 'board_step') for index in range(ROLL))
    events = [dict(t=t, type=kind) for t, kind in base]
    next(event for event in events if event['type'] == 'die_spin')['duration'] = DIE_HIT - DIE_START
    events.extend(board_round_events())
    events.append(dict(t=COIN_LOSS_TIME, type='coin_loss', id='ralsei', coins=-COIN_LOSS))
    events.extend(dict(t=t, type='lost_coin_contact', id='ralsei') for t in COIN_HITS)
    return events


@lru_cache(maxsize=8)
def native_art(name):
    with Image.open(NATIVE / f'{name}.png') as source:
        return source.convert('RGBA')


def game_title():
    art = native_art('boo-title')
    return art.resize((min(132, art.width), min(21, art.height)), NEAR)


def rules_panel():
    return native_art('boo-rules').resize(SIZE, NEAR).convert('RGB')


class Film:
    def __init__(self):
        self.game = BooGame(sprite)
        self.winner = self.game.winner
        self.events = sorted(
            board_events() + [dict(event, t=round(MATCH + event['t'], 6)) for event in self.game.events],
            key=lambda event: event['t'])
        adopt = next(event['t'] for event in self.events if event['type'] == 'adopt_boo')
        shortcut = next((event['t'] for event in self.events
                         if event['type'] == 'phase_wall' and event.get('id') == 'susie'), None)
        self.dialogue = lines(adopt, shortcut)
        draw = Random(DRAW_SEED)
        self.game_title = draw.choice(DRAW_POOL)
        self.draw_row = draw.randrange(4)
        if self.game_title != 'Boo Tag':
            raise ValueError('This episode uses the recorded Boo Tag draw')
        complete = next(event['t'] for event in self.events if event['type'] == 'round_complete')
        if complete > DRAW:
            raise ValueError('The roulette waits for all board turns to complete')
        lock = next(event for event in self.events if event['type'] == 'roulette_lock')
        lock.update(title=self.game_title, seed=DRAW_SEED, pool=DRAW_POOL, row=self.draw_row)
        self.board = Courtyard(self.winner, PAYOUT, RETURN)
        self.layout = ShortsReel(sprite, TEXT_RATE)
        self.title = game_title()
        self.rules = rules_panel()
        preview, _ = self.game.screens(READY + 1.23)
        self.preview = preview.crop((8, 20, 232, 163))
        self.ranking = sorted(PLAYERS, key=self.game.scores.get)
        self.score_lock = {who: .72 + .29 * index
                           for index, who in enumerate(reversed(self.ranking))}
        self.events.extend(dict(t=round(RESULT + t, 6), type='score_lock', id=who)
                           for who, t in self.score_lock.items())
        self.events.sort(key=lambda event: event['t'])
        self.result_plate = self.result_background()

    def result_background(self):
        path = NATIVE / 'result-clean.png'
        if path.is_file():
            return native_art('result-clean').resize(SIZE, NEAR).convert('RGB')
        return self.game.chest.crop((29, 10, 211, 132)).resize(SIZE, NEAR)

    def render_pair(self, t):
        if t < RULES:
            lower, upper = self.board.screens(t)
            if t >= DRAW:
                self.layout.roulette(lower, self.game_title, t - DRAW, LOCK - DRAW, selected_row=self.draw_row)
        elif t < MATCH:
            lower, upper = self.layout.rules(self.preview, self.title, self.rules, PLAYERS, 1)
            if t >= MATCH - .17:
                self.press_start(lower, MATCH - t)
        elif t < RETURN:
            lower, upper = self.game.screens(t - MATCH)
            if GO <= t < GO + .72:
                self.game_banner(lower, 'start', t - GO, .72)
            if FINISH <= t < FINISH + 1.25:
                self.game_banner(lower, 'finish', t - FINISH, 1.25)
            if t >= RESULT:
                age = t - RESULT
                stage = self.result_scene(age)
                lower = Image.blend(lower, stage, smooth(age / .34)) if age < .34 else stage
        else:
            lower, upper = self.board.screens(t)
            self.draw_payout(lower, t)
        return lower, upper

    @staticmethod
    def press_start(lower, until_start):
        button = lower.crop((179, 155, 239, 180))
        pressed = Image.blend(button, Image.new('RGB', button.size, '#221c37'), .19)
        lower.paste(pressed, (179, 155))
        if until_start > .09:
            ImageDraw.Draw(lower).rectangle((180, 155, 238, 178), outline='#fff199')

    @staticmethod
    def game_banner(lower, name, age, duration):
        enter = smooth(age / .15)
        leave = smooth((duration - age) / .22)
        target = 128 if name == 'start' else 143
        width = round(target * (.72 + .28 * enter))
        height = round(width / 4)
        mark = resized(name, width, height).copy()
        mark.putalpha(mark.getchannel('A').point(lambda alpha: round(alpha * leave)))
        centered(lower, mark, 120, 89 - (1 - enter) * 8)

    def result_scene(self, age):
        lower = self.result_plate.copy()
        reveal = max(0, age - (WIN_REVEAL - RESULT))
        for index, who in enumerate(PLAYERS):
            x = (41, 96, 146, 199)[index]
            y = (124, 133, 125, 120)[index]
            height = (39, 46, 39, 45)[index]
            settle = smooth(age / .53)
            x += (-11, -3, 3, 11)[index] * (1 - settle)
            y += 6 * (1 - settle)
            jump = 0
            face = 'down' if age > .51 else ('right' if index < 2 else 'left')
            stride = int(age * 11) % 4 if age < .53 else 0
            pose = f'{who}-{face}-{stride}'
            if reveal > .06 and who == self.winner:
                jump = 12 * sin(pi * smooth((reveal - .06) / .61))
                if who in ('gerson', 'susie'):
                    laugh_frames = 3 if who == 'gerson' else 2
                    pose = f'{who}-laugh-{int(reveal * 7) % laugh_frames}'
            elif reveal > .25:
                face = ('left', 'up', 'right', 'left')[index]
                pose = f'{who}-{face}-0'
            draw = ImageDraw.Draw(lower)
            draw.ellipse((x - 12, y - 4, x + 12, y + 3), fill='#6e4726')
            centered(lower, sprite(pose, height), x, y - height / 2 - jump)

            if age < .25:
                continue
            locked = age >= self.score_lock[who]
            value = self.game.scores[who] if locked else Random(int(age * 14) + 19 * index).uniform(0, 49)
            score_x = (20, 66, 113, 160)[index]
            score_y = 13 if index % 2 == 0 else 39
            self.game.draw_counter(lower, index, value, score_x, score_y)

        if reveal > 0:
            u = smooth(reveal / .24)
            y = 137 + 12 * (1 - u)
            name = self.winner.capitalize()
            for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ds_text(lower, name, 120 + ox, y + oy, height=17, color='#382208', middle=True)
            ds_text(lower, name, 120, y, height=17, color='#fff0b2', middle=True)
            centered(lower, resized('wins', 59, 19), 120, y + 28)
        return lower

    def draw_payout(self, lower, t):
        state = self.board.state(t)
        pose = state.poses[self.winner]
        active = state.poses[state.active]
        focus = mix(active.x, 192, smooth((t - RETURN) / .75))
        camera = round(max(0, min(self.board.board.plate.width - SIZE[0], focus - 112)))
        x, y = pose.x - camera, pose.y - 17
        for index in range(5):
            age = (t - (PAYOUT - .66 + index * .07)) / .38
            if 0 <= age < 1:
                centered(lower, resized('coin', max(3, round(8 * abs(1 - 2 * age))), 11),
                         x + (index - 2) * 6 * (1 - age), mix(y - 62, y, age * age))
        if PAYOUT <= t < PAYOUT + .85:
            age = t - PAYOUT
            centered(lower, resized('coin', 11, 13), x - 17, y - 35 - age * 9)
            centered(lower, resized('board-plus', 9, 10), x - 4, y - 35 - age * 9)
            number(lower, REWARD, x + 10, y - 42 - age * 9, height=14, kind='coins')

    def render(self, t, *, clean=True):
        # Keep the keyword accepted by earlier frame-check scripts.
        lower, upper = self.render_pair(t)
        return self.layout.compose(lower, upper, t, CUTS, self.dialogue)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stills', type=float, nargs='+')
    parser.add_argument('--scale', type=int, default=EXPORT_SCALE)
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    film = Film()
    qa = ROOT / 'qa'
    qa.mkdir(exist_ok=True)
    (qa / 'timeline.json').write_text(json.dumps(dict(events=film.events, dialogue=film.dialogue,
                                                     winner=film.winner, scores=film.game.scores,
                                                     duration=DURATION), indent=2) + '\n')
    if args.stills:
        for time in args.stills:
            still_size = tuple(length * 2 for length in SHORT_SIZE)
            film.render(time).resize(still_size, NEAR).save(qa / f'boo-{time:05.2f}.png')
        return

    from mix_boo import render_audio

    audio = render_audio(film)
    out = ROOT / 'out' / ('preview' if args.preview else 'final')
    out.mkdir(parents=True, exist_ok=True)
    process = start_encoder(out / f'boo-tag-short-{VERSION}.mp4', audio, fps=FPS, scale=args.scale)
    try:
        for frame in range(round(DURATION * FPS)):
            t = frame / FPS
            process.stdin.write(film.render(t).tobytes())
            if frame % (FPS * 6) == 0:
                print(f'{t:.0f}/{DURATION:.1f} s', flush=True)
    finally:
        process.stdin.close()
        if process.wait():
            raise RuntimeError('FFmpeg encoding failed')


if __name__ == '__main__':
    main()
