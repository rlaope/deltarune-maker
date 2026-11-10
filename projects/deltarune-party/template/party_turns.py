"""Shared timing and native DS sound cues for board turns."""

from dataclasses import dataclass

from reel_art import SIZE, mix, smooth


BANNER_DURATION = 1.10
BANNER_OUT = .92
CAMERA_CENTER = 112
TURN_CAMERA_DURATION = .55
PARTY_SOUND_CUES = {
    'turn_banner': ('mpds-turn-banner.wav', .54),
    'die_hit': ('mpds-die-hit.wav', .63),
    'board_step': ('mpds-board-step.wav', .33),
    'board_land': ('mpds-menu.wav', .28),
    'item_menu_focus': ('mpds-item-focus.wav', .52),
    'double_dice_item': ('mpds-item-confirm.wav', .54),
    'double_dice_total': ('mpds-menu.wav', .35),
    'blue_coin': ('mpds-coin-blue.wav', .46),
    'roulette_lock': ('mpds-menu.wav', .46),
    'rules': ('mpds-menu.wav', .35),
    'confirm': ('mpds-menu.wav', .45),
    'return': ('mpds-menu.wav', .38),
    'coin_award': ('mpds-coin.wav', .49),
}


@dataclass(frozen=True)
class BoardTurn:
    who: str
    start: float
    spins: tuple[float, ...]
    hits: tuple[float, ...]
    faces: tuple[int, ...]
    move: float
    step: float
    origin: int
    board_spaces: int
    banner_hold: float = 0
    camera_duration: float = TURN_CAMERA_DURATION
    coin_delay: float = .27

    @property
    def banner(self):
        return round(self.start + self.camera_duration, 2)

    @property
    def spaces(self):
        return sum(self.faces)

    @property
    def land(self):
        return round(self.move + self.spaces * self.step, 2)

    @property
    def award(self):
        return round(self.land + self.coin_delay, 2)

    def after_award(self, settle):
        return round(self.award + settle, 2)

    @property
    def destination(self):
        return (self.origin + self.spaces) % self.board_spaces


def next_turn_start(turn, *, dialogue_end=None, reward_hold=1.60, dialogue_hold=.82):
    """Allow both the landing reward and any reaction dialogue to settle before the handoff."""
    reward_ready = turn.after_award(reward_hold)
    if dialogue_end is None:
        return reward_ready
    return max(reward_ready, round(dialogue_end + dialogue_hold, 2))


def turn_events(turn, coins):
    """Share the rendered turn's schedule with the sound mix."""
    yield dict(t=turn.banner, type='turn_banner', id=turn.who)
    for index, (spin, hit, face) in enumerate(zip(turn.spins, turn.hits, turn.faces, strict=True), 1):
        yield dict(t=spin, type='die_spin', id=turn.who, die=index, duration=round(hit - spin, 2))
        yield dict(t=hit, type='die_hit', id=turn.who, die=index, face=face)
    for index in range(turn.spaces):
        yield dict(t=round(turn.move + index * turn.step, 2), type='board_step',
                   id=turn.who, step=index + 1)
    yield dict(t=turn.land, type='board_land', id=turn.who, node=turn.destination)
    yield dict(t=turn.award, type='blue_coin', id=turn.who, coins=coins)


def handoff_focus(plate_width, previous, current, t, turn):
    """Ease between valid camera endpoints before showing the banner."""
    if t >= turn.banner:
        return current
    left, right = CAMERA_CENTER, CAMERA_CENTER + plate_width - SIZE[0]
    start = min(right, max(left, previous))
    end = min(right, max(left, current))
    return mix(start, end, smooth((t - turn.start) / turn.camera_duration))


def visible_banner_age(age, hold=0):
    """Add dwell without changing the native banner entry and exit."""
    if 0 <= age < BANNER_DURATION + hold:
        return max(BANNER_OUT, age - hold) if age > BANNER_OUT else age
    return None
