"""A runnable production check for the shared conversation and turn handoff."""

from dataclasses import replace
from functools import lru_cache
import hashlib
import json
from math import pi, sin
import subprocess

import numpy as np
from PIL import Image

from mix import Mixer, missing_sound_cues
from mpds_ui import number, resized
from party_board import BoardState, PartyBoard, Pose, Roll
from party_dialogue import PartyDialogue, Reply, Speaker
from party_reel import ShortsReel
from party_staging import ConversationShot
from party_turns import BoardTurn, PARTY_SOUND_CUES, handoff_focus, next_turn_start, turn_events
from reel_art import NEAR, ROOT, centered, paste, point, smooth
from shorts_export import start_encoder


TITLE = 'Three Coins, Four Coins Owed'
FPS = 60
PLAYERS = ('lancer', 'susie', 'noelle', 'flowery')
ROUTE = ((120, 129), (156, 119), (192, 109), (228, 99),
         (264, 86), (302, 73), (375, 130), (480, 140))
HEIGHTS = dict(lancer=34, susie=43, noelle=43, flowery=49)


@lru_cache(maxsize=128)
def sprite(name, height):
    with Image.open(ROOT / 'assets/cast' / f'{name}.png') as source:
        image = source.convert('RGBA')
    image = image.crop(image.getbbox())
    return image.resize((max(1, round(image.width * height / image.height)), height), NEAR)


class Rehearsal:
    def __init__(self):
        with Image.open(ROOT / 'assets/boards/chapter-5/second-diner.png') as source:
            plate = source.crop((0, 210, source.width, 390))
        self.board = PartyBoard(plate, ROUTE, ('blue',) * len(ROUTE), PLAYERS, sprite, HEIGHTS)
        self.dialogue = PartyDialogue({
            'lancer': Speaker('lancer-laugh-face', '../cast/lancer-text.wav', -.12),
            'susie': Speaker('susie-confused-face', '../cast/susie-text.wav', .12),
        })
        first = BoardTurn('lancer', 0, (1.85,), (2.55,), (2,), 3.05, .40, 0, len(ROUTE))
        award = next(event for event in turn_events(first, 3) if event['type'] == 'blue_coin')
        reply_end = self.dialogue.exchange(
            award, Reply('lancer', "* Three coins! I'm rich!"),
            Reply('susie', '* You still owe me four.'))
        self.shot = ConversationShot(
            self.dialogue.cues, ('lancer', 'susie'),
            reactions={'lancer': ('lancer-laugh-0', 'lancer-laugh-1')})
        next_start = next_turn_start(first, dialogue_end=reply_end)
        second = BoardTurn('susie', next_start, (next_start + 1.85,), (next_start + 2.55,),
                           (1,), next_start + 3.05, .40, 4, len(ROUTE))
        self.turns = (first, second)
        self.duration = round(next_turn_start(second) * FPS) / FPS
        self.events = sorted((event for turn in self.turns for event in turn_events(turn, 3)),
                             key=lambda event: event['t'])
        self.reel = ShortsReel(sprite, self.dialogue.text_rate)
        self.dialogue.validate_fit(self.reel.font)

    def state(self, t):
        poses = {who: Pose(*ROUTE[index]) for who, index in
                 zip(PLAYERS, (0, 4, 6, 7), strict=True)}
        state = BoardState(poses, dict.fromkeys(PLAYERS, 10), dict.fromkeys(PLAYERS, 0),
                           PLAYERS[0], 1, 1)
        for turn in self.turns:
            if t < turn.start:
                break
            roll = None
            if turn.spins[0] <= t < turn.move:
                age = t - turn.hits[0]
                face = 1 + int(t * 14) % 10 if age < 0 else turn.faces[0]
                roll = Roll(face, age)
            if turn.move <= t < turn.land:
                progress = (t - turn.move) / turn.step
                step = min(turn.spaces - 1, int(progress))
                a = ROUTE[(turn.origin + step) % len(ROUTE)]
                b = ROUTE[(turn.origin + step + 1) % len(ROUTE)]
                x, y = point(a, b, smooth(progress - step))
                poses[turn.who] = Pose(x, y, 'right', int(t * 12) % 4,
                                       5 * sin(pi * (progress - step)))
                roll = Roll(turn.faces[0], t - turn.hits[0], turn.spaces - step)
            elif t >= turn.land:
                poses[turn.who] = Pose(*ROUTE[turn.destination])
            if t >= turn.award:
                state.coins[turn.who] += 3
            age = t - turn.banner
            state = replace(state, active=turn.who, roll=roll,
                            banner_age=age if 0 <= age < 1.10 else None)
        return state

    def frame(self, t):
        state = self.state(t)
        focus = state.poses[state.active].x
        second = self.turns[1]
        if t >= second.start:
            previous_state = self.state(second.start - .01)
            _, previous_focus = self.shot.apply(
                self.board, previous_state, second.start - .01,
                previous_state.poses[previous_state.active].x)
            focus = handoff_focus(self.board.plate.width, previous_focus, focus, t, second)
        state, focus = self.shot.apply(self.board, state, t, focus)
        lower, camera = self.board.lower(state, t, focus)
        for turn in self.turns:
            x, y = ROUTE[turn.destination]
            for index in range(3):
                progress = (t - turn.land - index * .045) / .17
                if 0 <= progress < 1:
                    centered(lower, resized('coin', 9, 11), x - camera + (index - 1) * 9,
                             y - 65 + 45 * progress ** 2)
            if turn.award <= t < turn.award + .58:
                centered(lower, resized('coin', 12, 14), x - camera - 14, y - 58)
                paste(lower, resized('board-plus', 8, 10), x - camera - 2, y - 63)
                number(lower, 3, x - camera + 12, y - 65, height=14, kind='coins')
        return self.reel.compose(lower, self.board.upper(state), t, dialogue=self.dialogue.cues)

    def render_check(self, output):
        mixer = Mixer(self.duration)
        mixer.add('music', 0, 'mpds-wiggler.flac', .41, self.duration, fade=.09)
        expected = {}
        for event in self.events:
            if event['type'] == 'die_spin':
                mixer.add('sound', event['t'], 'mpds-dice-spin.wav', .36, event['duration'])
                expected[event['type']] = 'mpds-dice-spin.wav'
            elif event['type'] in PARTY_SOUND_CUES:
                path, gain = PARTY_SOUND_CUES[event['type']]
                mixer.add('sound', event['t'], path, gain)
                expected[event['type']] = path
        before_dialogue = mixer.stems['sound'].copy()
        self.dialogue.mix(mixer)
        if not np.array_equal(before_dialogue, mixer.stems['sound']):
            raise ValueError('Dialogue changed the action sound stem')
        missing = missing_sound_cues(self.events, mixer.cues, expected)
        if missing:
            raise ValueError(f'Missing native action cues: {missing}')
        mixer.write(output / 'mix.wav', output / 'mix.json')
        (output / 'timeline.json').write_text(json.dumps({
            'title': TITLE, 'duration': self.duration, 'events': self.events,
            'dialogue': self.dialogue.cues, 'next_turn': self.turns[1].start,
        }, indent=2) + '\n')
        for index, cue in enumerate(self.dialogue.cues):
            self.frame(cue['end'] - .1).resize((540, 960), NEAR).save(output / f'reply-{index}.png')
        path = output / 'conversation-check.mp4'
        with start_encoder(path, output / 'mix.wav') as encoder:
            for frame in range(round(self.duration * FPS)):
                encoder.stdin.write(self.frame(frame / FPS).tobytes())
            encoder.stdin.close()
            if encoder.wait():
                raise RuntimeError('Conversation check encoding failed')
        probe = json.loads(subprocess.check_output([
            'ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path),
        ]))
        video = next(stream for stream in probe['streams'] if stream['codec_type'] == 'video')
        audio = next(stream for stream in probe['streams'] if stream['codec_type'] == 'audio')
        if (video['width'], video['height'], video['r_frame_rate'], int(video['nb_frames'])) != (
                2160, 3840, '60/1', round(self.duration * FPS)):
            raise ValueError('Conversation check has unexpected video dimensions, rate, or frame count')
        if (int(audio['sample_rate']), audio['channels']) != (48000, 2):
            raise ValueError('Conversation check needs 48 kHz stereo audio')
        (output / 'export.json').write_text(json.dumps({
            'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'width': video['width'], 'height': video['height'], 'frame_rate': video['r_frame_rate'],
            'duration': float(video['duration']), 'frames': int(video['nb_frames']),
            'sample_rate': int(audio['sample_rate']), 'channels': audio['channels'],
        }, indent=2) + '\n')
        print(path)
