from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'template'))

from party_turns import BoardTurn, next_turn_start


class NextTurnStartTest(unittest.TestCase):
    turn = BoardTurn('noelle', 1.25, (2,), (2.5,), (3,), 3.25, .41, 0, 12)

    def test_waits_after_reward_without_dialogue(self):
        self.assertEqual(next_turn_start(self.turn), 6.35)

    def test_later_dialogue_determines_handoff_on_board_clock(self):
        self.assertEqual(next_turn_start(self.turn, dialogue_end=6.128), 6.95)

    def test_early_dialogue_keeps_minimum_reward_hold(self):
        self.assertEqual(next_turn_start(self.turn, dialogue_end=5.08), 6.35)
