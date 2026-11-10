"""Native Mario Party DS Double Dice Set selection and roll drawing."""

from dataclasses import dataclass

from mpds_ui import number, resized
from party_board import Roll
from party_turns import BoardTurn
from reel_art import centered, mix, paste, smooth, stylus


@dataclass(frozen=True)
class DoubleDiceSet:
    turn: BoardTurn
    menu_open: float
    focus: float
    confirm: float
    total: float

    def __post_init__(self):
        if len(self.turn.faces) != 2:
            raise ValueError('A Double Dice Set needs two die faces')

    def events(self):
        who = self.turn.who
        yield dict(t=self.menu_open, type='item_menu_open', id=who)
        yield dict(t=self.focus, type='item_menu_focus', id=who)
        yield dict(t=self.confirm, type='double_dice_item', id=who)
        yield dict(t=self.total, type='double_dice_total', id=who,
                   faces=self.turn.faces, total=self.turn.spaces)

    def draw_menu(self, lower, t, actor_x):
        paste(lower, resized('item-map-y', 30, 36), 210, 38)
        if t >= self.confirm + .12:
            return
        selected = t >= self.focus
        shift = min(57, max(-57, actor_x - 120))
        paste(lower, resized('item-double-dice-native', 33, 31), 104 + shift, 22)
        paste(lower, resized('item-normal-die', 23, 27), 110 + shift, 58)
        paste(lower, resized('item-select-hand', 30, 26), 97 + shift, 6 if selected else 51)
        card = 'item-double-card' if selected else 'item-dice-card'
        paste(lower, resized(card, 233, 36), 4, 121)
        confirm_offset = 2 if t >= self.confirm else 0
        paste(lower, resized('item-select-ok', 61, 23), 179 + confirm_offset, 157)

    def draw_rolls(self, lower, t, pose, camera, draw_hit):
        turn = self.turn
        x = min(172, max(66, pose.x - camera))
        y = max(9, pose.y - 76)
        first_spin, second_spin = turn.spins
        first_hit, second_hit = turn.hits
        first_face, second_face = turn.faces
        if t < second_spin:
            slide = 37 * smooth((t - first_hit - .11) / .19)
            self._draw_roll(lower, t, x - slide, pose.y, first_spin, first_hit, first_face, draw_hit)
        elif t < second_hit + .16:
            number(lower, first_face, x - 37, y + 4, height=24)
            self._draw_roll(lower, t, x, pose.y, second_spin, second_hit, second_face, draw_hit)
        elif t < self.total:
            age = smooth((t - second_hit - .16) / (self.total - second_hit - .16))
            number(lower, first_face, x - mix(37, 15, age), y + 4, height=24)
            centered(lower, resized('board-plus', 13, 15), x - 18 * (1 - age), y + 16)
            number(lower, second_face, x + 15 * age, y + 4, height=24)
        else:
            number(lower, turn.spaces, x, y, height=34)

    @staticmethod
    def _draw_roll(lower, t, x, actor_y, spin, hit, face, draw_hit):
        if t >= hit:
            draw_hit(lower, x - 15, actor_y, Roll(face, t - hit), t)
            return
        visible = face if hit - t < .052 else 1 + int((t - spin) * 18 + face) % 10
        paste(lower, resized(f'double-dice-roll/{visible:02}', 53, 67), x - 26.5, 25)
        paste(lower, resized('item-map-y', 30, 36), 210, 38)
        if hit - t < .37:
            approach = smooth((t - hit + .37) / .37)
            stylus(lower, x + 38 * (1 - approach), 70 + 29 * (1 - approach),
                   press=max(0, 1 - (hit - t) / .14))
        paste(lower, resized('item-dice-card', 233, 36), 4, 121)
