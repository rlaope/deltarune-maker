"""Render the Flower Kingdom diner round and Fast Food Frenzy as one Short."""

import argparse
import json
from math import pi, sin
from random import Random

from PIL import Image

from fast_board import BOARD_LINES, DRAW_READY, PLAYERS, SPECIAL, DinerBoard, board_events, sprite
from fast_game import FastGame
from fast_ui import DinerLayout, banner, native, result_badge, winner_name
from reel_art import NEAR, ROOT, SIZE, paste, smooth
from shorts_export import start_encoder


TITLE = 'Flowery’s Diner Went Full Mario Party DS'
VERSION = 'v7'
FPS = 60
TEXT_RATE = 27
NAME = 'Fast Food Frenzy'
POOL = ('Track Star', NAME, 'Power Washer', 'Plush Crush')
DRAW_SEED = 1
JARONA_VOICES = ((1, .94), (4, .97), (2, .86), (3, .82), (1, .94))


class Film:
    def __init__(self):
        self.board = DinerBoard()
        self.game = FastGame(sprite)
        self.layout = DinerLayout(sprite, TEXT_RATE)
        self.draw = DRAW_READY
        self.lock = round(self.draw + 2.78, 6)
        self.rules = round(self.lock + 1.62, 6)
        self.arena = round(self.rules + 4.85, 6)
        self.go = round(self.arena + self.game.ready, 6)
        self.finish = round(self.arena + self.game.finish, 6)
        self.result = round(self.finish + 1.78, 6)
        self.reveal = round(self.result + 1.10, 6)
        self.duration = round((self.result + 5.42) * FPS) / FPS
        self.cuts = (self.rules, self.arena)
        self.team = self.game.team

        draw = Random(DRAW_SEED)
        title = draw.choice(POOL)
        self.row = draw.randrange(4)
        if title != NAME:
            raise ValueError('The recorded one-versus-three draw must select Fast Food Frenzy')
        self.events = self.timeline()
        self.dialogue = tuple(BOARD_LINES) + self.conveyor_dialogue() + ({
            'speaker': 'lancer', 'start': self.result + 2.26, 'end': self.result + 5.16,
            'text': '* Can I get that to go?', 'portrait': 'lancer-laugh-face',
        },)
        _, self.preview = self.game.screens(self.game.ready + 8.2)
        self.result_plate = native('result-plate').resize(SIZE, NEAR).convert('RGB')
        self.result_control = native('result-control').resize(SIZE, NEAR).convert('RGB')

    def conveyor_dialogue(self):
        cues = []
        deliveries = [event for event in self.events if event['type'] == 'flowery_delivery']
        for event, (voice, length) in zip(deliveries, JARONA_VOICES, strict=True):
            start = event['t']
            cues.append(dict(speaker='flowery', start=start, end=start + length,
                             text='* JARONA!', portrait='flowery-face-open',
                             voice=f'../deltarune/flowery-jarona-voice-{voice}.wav'))
        reactions = (
            ('susie', 'out', .23, 1.24, '* Stupid burger!'),
            ('lancer', 'out', .71, 1.35, '* My pancakes betrayed me!'),
            ('noelle', 'clear', .16, 1.34, '* I can make it!'),
        )
        for speaker, kind, delay, length, text in reactions:
            event = next(e for e in self.events if e['type'] == kind and e.get('player') == speaker)
            start = event['t'] + delay
            cues.append(dict(speaker=speaker, start=start, end=start + length, text=text))
        drops = [event for event in self.events if event['type'] == 'drop']
        syrup = next(event for event in self.events if event['type'] == 'sticky')
        for event, pause, length, text in (
            (drops[0], .12, 1.20, '* Order up!'),
            (syrup, .18, 1.38, "* That's extra syrup!"),
            (drops[-1], .11, 1.32, '* Last call, Noelle!'),
        ):
            start = event['t'] + pause
            cues.append(dict(speaker='flowery', start=start, end=start + length,
                             text=text, portrait='flowery-face-open'))
        cues.sort(key=lambda cue: cue['start'])
        if any(before['end'] > after['start'] for before, after in zip(cues, cues[1:])):
            raise ValueError('Conveyor dialogue overlaps another speaker')
        return tuple(cues)

    def timeline(self):
        events = list(board_events())
        turns = [event for event in events if event['type'] == 'turn_banner']
        if len(turns) != 4 or {event['id'] for event in turns} != set(PLAYERS):
            raise ValueError('All four players must take a turn before the draw')
        complete = next(event for event in events if event['type'] == 'round_complete')
        landings = {event['id']: event['space'] for event in events if event['type'] == 'board_land'}
        if complete['t'] >= self.draw:
            raise ValueError('The roulette must follow completion of the full round')
        if set(self.team) != set(complete['sides'][0]) or complete['sides'][1] != ('flowery',):
            raise ValueError('The minigame cast must match the completed round')
        assigned = next(event for event in events if event['type'] == 'green_team_assign')
        if (landings[SPECIAL['player']] != 'event' or not complete['t'] < assigned['t'] < self.draw
                or assigned['color'] != 'blue' or landings['flowery'] != 'red'
                or any(landings[who] != 'blue' for who in self.team if who != SPECIAL['player'])):
            raise ValueError('The green-space player must join the two blue players before the draw')
        events += [
            {'t': self.draw, 'type': 'draw', 'mode': '1-vs-3', 'solo': 'flowery', 'team': self.team},
            {'t': round(self.draw + .70, 6), 'type': 'roulette_spin'},
            {'t': self.lock, 'type': 'roulette_lock', 'mode': '1-vs-3',
             'title': NAME, 'row': self.row, 'pool': POOL, 'seed': DRAW_SEED},
            {'t': self.rules, 'type': 'rules'},
            {'t': self.arena - .10, 'type': 'confirm'},
            {'t': self.arena, 'type': 'arena_open'},
            {'t': self.go, 'type': 'game_go'},
            {'t': self.finish, 'type': 'game_finish'},
            {'t': self.result, 'type': 'results'},
            {'t': self.reveal, 'type': 'winner_reveal', 'winner': self.game.winner,
             'survivors': self.game.survivors},
        ]
        events.extend(dict(event, t=round(self.arena + event['t'], 6), scene='conveyor')
                      for event in self.game.events)
        return sorted(events, key=lambda event: event['t'])

    def render_pair(self, t):
        if t < self.rules:
            lower, upper = self.board.screens(t)
            if t >= self.draw:
                self.layout.draw_roulette(lower, NAME, t - self.draw, self.lock - self.draw, self.row)
            return lower, upper
        if t < self.arena:
            return self.layout.game_rules(self.preview, self.team, 'flowery', self.arena - t)

        lower, upper = self.game.screens(t - self.arena)
        if self.go <= t < self.go + .86:
            banner(upper, 'start', t - self.go, .86)
        if self.finish <= t < self.finish + 1.34:
            banner(upper, 'finish', t - self.finish, 1.34)
        if t >= self.result:
            age = t - self.result
            stage = self.result_scene(age)
            upper = Image.blend(upper, stage, smooth(age / .37)) if age < .37 else stage
            lower = self.result_control
        return lower, upper

    def result_scene(self, age):
        screen = self.result_plate.copy()
        winner_age = age - (self.reveal - self.result)
        order = ('susie', 'lancer', 'noelle')
        for index, (who, x, y, height) in enumerate(zip(order, (73, 121, 170), (114, 115, 114), (37, 34, 38))):
            settle = smooth(age / .65)
            x += (-13, 0, 13)[index] * (1 - settle)
            bounce_age = winner_age - index * .08
            lift = 9 * sin(pi * bounce_age / .63) if 0 <= bounce_age <= .63 else 0
            moving = age < .65
            face = ('right', 'down', 'left')[index] if moving else 'down'
            stride = int(age * 12) % 4 if moving else 0
            if who == 'lancer' and 2.26 < age < 5.16:
                name = f'lancer-laugh-{int(age * 7) % 2}'
            else:
                name = f'{who}-{face}-{stride}'
            body = sprite(name, height)
            paste(screen, body, x - body.width / 2, y - body.height - lift)
        if winner_age >= 0:
            for who, x, y in (('Susie', 66, 39), ('Lancer', 120, 10), ('Noelle', 181, 39)):
                winner_name(screen, who, x, y)
            result_badge(screen, winner_age)
        return screen

    def render(self, t):
        lower, upper = self.render_pair(t)
        return self.layout.compose(lower, upper, t, self.cuts, self.dialogue)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stills', type=float, nargs='+')
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    film = Film()
    qa = ROOT / 'qa'
    qa.mkdir(exist_ok=True)
    (qa / 'timeline.json').write_text(json.dumps({
        'title': TITLE, 'duration': film.duration, 'events': film.events, 'dialogue': film.dialogue,
    }, indent=2, ensure_ascii=False) + '\n')
    if args.stills:
        for t in args.stills:
            film.render(t).resize((540, 960), NEAR).save(qa / f'fast-{t:05.2f}.png')
        return

    from fast_mix import render_audio

    audio = render_audio(film, TEXT_RATE)
    output = ROOT / 'out' / ('preview' if args.preview else 'final')
    output.mkdir(parents=True, exist_ok=True)
    path = output / f'fast-food-frenzy-short-{VERSION}.mp4'
    with start_encoder(path, audio, fps=FPS, scale=2 if args.preview else 8) as encoder:
        for frame in range(round(film.duration * FPS)):
            encoder.stdin.write(film.render(frame / FPS).tobytes())
            if frame % (FPS * 6) == 0:
                print(f'{frame / FPS:.0f}/{film.duration:.2f}s', flush=True)
        encoder.stdin.close()
        if encoder.wait():
            raise RuntimeError('Fast Food Frenzy encoding failed')


if __name__ == '__main__':
    main()
