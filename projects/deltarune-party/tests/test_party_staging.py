from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'template'))

from party_staging import ConversationShot


@dataclass(frozen=True)
class Pose:
    x: float
    y: float
    facing: str = 'down'
    stride: int = 0
    lift: float = 0
    sprite: str | None = None


@dataclass(frozen=True)
class BoardState:
    poses: dict
    coins: dict
    stars: dict
    active: str
    turn: int
    total_turns: int
    roll: object = None
    banner_age: float | None = None


class ConversationShotTests(unittest.TestCase):
    def setUp(self):
        self.state = BoardState(
            poses={'lancer': Pose(170, 100), 'susie': Pose(260, 125), 'noelle': Pose(480, 120)},
            coins={'lancer': 13, 'susie': 10, 'noelle': 10},
            stars={'lancer': 0, 'susie': 0, 'noelle': 0}, active='lancer', turn=1, total_turns=5)
        self.loaded = []

        def sprite(name, height):
            self.loaded.append(name)
            return Image.new('RGBA', (24 if name.endswith('laugh-1') else 20, height))

        self.board = SimpleNamespace(plate=Image.new('RGB', (640, 180)), sprite=sprite,
                                     heights={'lancer': 34, 'susie': 43, 'noelle': 43})
        self.shot = ConversationShot(
            ({'speaker': 'lancer', 'start': 1, 'end': 2},
             {'speaker': 'susie', 'start': 2.12, 'end': 3.25}),
            ('lancer', 'susie'), reactions={'lancer': ('lancer-laugh-0', 'lancer-laugh-1')})

    def test_faces_and_frames_both_players_without_changing_game_state(self):
        staged, focus = self.shot.apply(self.board, self.state, 1.2, 170)
        self.assertEqual(staged.poses['lancer'].facing, 'right')
        self.assertEqual(staged.poses['susie'].facing, 'left')
        self.assertEqual(staged.poses['lancer'].sprite, 'lancer-laugh-1')
        self.assertIs(staged.poses['noelle'], self.state.poses['noelle'])
        self.assertEqual(replace(staged, poses=self.state.poses), self.state)
        self.assertEqual(self.state.poses['lancer'], Pose(170, 100))
        camera = round(focus - 112)
        self.assertLessEqual(camera + 8, 170 - 12)
        self.assertGreaterEqual(camera + 240 - 8, 260 + 10)

    def test_eases_before_text_and_holds_during_gap_and_after_reply(self):
        _, initial = self.shot.apply(self.board, self.state, self.shot.start, 170)
        _, middle = self.shot.apply(self.board, self.state, .825, 170)
        staged, full = self.shot.apply(self.board, self.state, 1, 170)
        self.assertEqual(initial, 170)
        self.assertTrue(min(initial, full) < middle < max(initial, full))
        for time in (2.06, 3.9, 4.069):
            with self.subTest(time=time):
                held, focus = self.shot.apply(self.board, self.state, time, 170)
                self.assertEqual(focus, full)
                self.assertEqual(held.poses['lancer'].facing, staged.poses['lancer'].facing)
        self.assertEqual(self.shot.end, 4.07)
        untouched, focus = self.shot.apply(self.board, self.state, self.shot.end, 170)
        self.assertIs(untouched, self.state)
        self.assertEqual(focus, 170)

    def test_keeps_roll_banner_and_moving_pose_in_control(self):
        for state, moving in (
                (replace(self.state, roll=object()), ()),
                (replace(self.state, banner_age=0), ()),
                (replace(self.state, poses={**self.state.poses, 'lancer': Pose(170, 100, stride=1)}), ()),
                (replace(self.state, poses={**self.state.poses, 'susie': Pose(260, 125, lift=2)}), ()),
                (self.state, ('lancer',))):
            with self.subTest(state=state, moving=moving):
                unchanged, focus = self.shot.apply(self.board, state, 1.2, 170, moving=moving)
                self.assertIs(unchanged, state)
                self.assertEqual(focus, 170)

    def test_camera_handles_plate_edges_and_rejects_impossible_composition(self):
        for positions, camera in (((20, 90), 0), ((550, 620), 400)):
            state = replace(self.state, poses={
                **self.state.poses, 'lancer': Pose(positions[0], 100), 'susie': Pose(positions[1], 125)})
            _, focus = self.shot.apply(self.board, state, 1.2, 170)
            self.assertEqual(round(focus - 112), camera)
        for pose in (Pose(410, 125), Pose(260, 20), Pose(632, 125)):
            state = replace(self.state, poses={**self.state.poses, 'susie': pose})
            with self.subTest(pose=pose), self.assertRaisesRegex(ValueError, 'fit'):
                self.shot.apply(self.board, state, 1.2, 170)
