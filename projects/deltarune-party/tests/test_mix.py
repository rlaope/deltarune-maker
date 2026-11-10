import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'template'))

from mix import missing_sound_cues


class SoundCoverageTests(unittest.TestCase):
    def test_requires_sound_on_the_same_event(self):
        events = [
            {'t': 1.1234567, 'type': 'blue_coin'},
            {'t': 2, 'type': 'blue_coin'},
            {'t': 3, 'type': 'game_go'},
            {'t': 4, 'type': 'board_land'},
        ]
        cues = [
            {'t': 1.123457, 'stem': 'sound', 'source': 'mpds-coin-blue.wav', 'gain': .5},
            {'t': 2, 'stem': 'voice', 'source': 'mpds-coin-blue.wav', 'gain': .5},
            {'t': 2.02, 'stem': 'sound', 'source': 'mpds-coin-blue.wav', 'gain': .5},
            {'t': 3, 'stem': 'sound', 'source': 'mpds-menu.wav', 'gain': .5},
            {'t': 3, 'stem': 'sound', 'source': 'mpds-native-start.wav', 'gain': 0},
        ]
        sources = {'blue_coin': 'mpds-coin-blue.wav', 'game_go': 'mpds-native-start.wav'}

        self.assertEqual(missing_sound_cues(events, cues, sources), [
            (2, 'blue_coin', 'mpds-coin-blue.wav'),
            (3, 'game_go', 'mpds-native-start.wav'),
        ])
