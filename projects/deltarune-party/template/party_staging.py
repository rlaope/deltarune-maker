"""Stage two stationary board players for an event-driven conversation."""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import replace
from math import ceil, floor, isfinite
from typing import TYPE_CHECKING

from reel_art import SIZE, mix, smooth

if TYPE_CHECKING:
    from party_board import BoardState, PartyBoard


class ConversationShot:
    def __init__(self, cues: Sequence[dict], participants: tuple[str, str], *,
                 reactions: Mapping[str, Sequence[str]] | None = None,
                 lead: float = .35, hold: float = .82):
        self.cues = tuple(dict(cue) for cue in cues)
        self.participants = tuple(participants)
        self.reactions = {who: tuple(frames) for who, frames in (reactions or {}).items()}
        if len(self.participants) != 2 or len(set(self.participants)) != 2 or not self.cues:
            raise ValueError('A conversation shot needs two distinct players and dialogue')
        if not all(isfinite(value) and value >= 0 for value in (lead, hold)):
            raise ValueError('Conversation lead and hold must be finite and nonnegative')
        if any(cue['speaker'] not in self.participants for cue in self.cues):
            raise ValueError('Every speaker must be a conversation participant')
        if any(who not in self.participants or not frames for who, frames in self.reactions.items()):
            raise ValueError('Reaction frames must belong to a conversation participant')
        self.lead = lead
        self.dialogue_start = min(cue['start'] for cue in self.cues)
        self.start = max(0, self.dialogue_start - lead)
        self.end = round(max(cue['end'] for cue in self.cues) + hold, 2)

    def apply(self, board: PartyBoard, state: BoardState, t: float, default_focus: float, *,
              moving: Collection[str] = ()) -> tuple[BoardState, float]:
        """Ease in, face the players, and hold the shot through the final reply.

        Supply moving from the scene's movement schedule, including stride-zero
        animation frames. Coordinates and HUD ownership remain in the board state.
        """
        if not self.start <= t < self.end or state.roll is not None or state.banner_age is not None:
            return state, default_focus
        poses = [state.poses[who] for who in self.participants]
        if any(who in moving or pose.stride != 0 or pose.lift != 0
               for who, pose in zip(self.participants, poses, strict=True)):
            return state, default_focus

        staged = state.poses.copy()
        left, right = board.plate.width, 0
        for who, pose, other in zip(self.participants, poses, reversed(poses), strict=True):
            dx, dy = other.x - pose.x, other.y - pose.y
            facing = pose.facing
            if dx or dy:
                if abs(dx) >= abs(dy):
                    facing = 'right' if dx > 0 else 'left'
                else:
                    facing = 'down' if dy > 0 else 'up'
            frames = self.reactions.get(who, ())
            body = pose.sprite
            cue = next((cue for cue in self.cues
                        if cue['speaker'] == who and cue['start'] <= t < cue['end']), None)
            if cue is not None and frames:
                body = frames[int((t - cue['start']) * 7) % len(frames)]
            staged[who] = replace(pose, facing=facing, sprite=body)
            names = (pose.sprite or f'{who}-{facing}-0', *frames)
            actors = [board.sprite(name, board.heights[who]) for name in names]
            width = max(actor.width for actor in actors)
            height = max(actor.height for actor in actors)
            if pose.y - height < 0 or pose.y > SIZE[1]:
                raise ValueError('Conversation players must fit vertically in the board view')
            left, right = min(left, pose.x - width / 2), max(right, pose.x + width / 2)

        first = ceil(max(0, right + 8 - SIZE[0]))
        last = floor(min(board.plate.width - SIZE[0], left - 8))
        if first > last:
            raise ValueError('Conversation players cannot fit together at native size')
        camera = max(first, min(last, round((left + right - SIZE[0]) / 2)))
        focus = camera + 112
        amount = 1
        if t < self.dialogue_start:
            amount = smooth((t - self.start) / (self.dialogue_start - self.start))
        return replace(state, poses=staged), mix(default_focus, focus, amount)
