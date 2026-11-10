"""Fixed-tick combat for the Soap Surfers remix."""

from dataclasses import dataclass, field
from math import atan2, cos, hypot, sin


@dataclass(frozen=True)
class Skill:
    name: str
    windup: float
    speed: float
    reach: float
    hitbox: float
    push: float
    angles: tuple[float, ...]


SKILLS = {
    'queen': Skill('energy', .74, 1.96, 1.83, .105, .97, (0,)),
    'gerson': Skill('hammer', .69, 1.27, .47, .105, 1.55, (0,)),
    'flowery': Skill('jarona', .83, 1.90, .83, .248, 1.52, (0,)),
    'ralsei': Skill('fire', .73, 1.62, 1.65, .133, 1.39, (0,)),
}
CAST_TIMES = (
    (3.85, 'queen', 'ralsei'),
    (7.40, 'flowery', 'gerson'),
    (11.38, 'ralsei', 'queen'),
    (14.78, 'gerson', 'flowery'),
    (19.17, 'ralsei', 'flowery'),
    (22.60, 'flowery', 'ralsei'),
    (25.75, 'flowery', 'gerson'),
    (27.47, 'gerson', 'flowery'),
)


@dataclass
class Cast:
    id: str
    target: str
    at: float
    release_tick: int
    angle: float
    skill: Skill
    hits: set[str] = field(default_factory=set)
    near: float | None = None
    origin: tuple[float, float] | None = None

    def snapshot(self, x, y):
        return dict(id=self.id, target=self.target, at=self.at, angle=self.angle,
                    skill=self.skill.name, windup=self.skill.windup, x=x, y=y)


@dataclass
class Shot:
    cast: Cast
    x: float
    y: float
    angle: float
    traveled: float = 0

    def snapshot(self):
        return dict(skill=self.cast.skill.name, x=self.x, y=self.y, angle=self.angle,
                    radius=self.traveled)


class SkillRound:
    def __init__(self, ticks):
        self.dt = 1 / ticks
        self.schedule = {round(time * ticks): (caster, target) for time, caster, target in CAST_TIMES}
        self.casts = []
        self.shots = []
        self.pops = []

    @staticmethod
    def _emit(emit, t, kind, cast, x, y, target=None, **details):
        emit(t, kind, cast.id, skill=cast.skill.name, x=x, y=y,
             target=cast.target if target is None else target, **details)

    def _begin(self, t, tick, riders, caster, target, emit):
        first, second = riders[caster], riders[target]
        if not (first.alive and second.alive):
            return
        skill = SKILLS[caster]
        # The lane stays locked through windup, so an opponent can read it and turn.
        angle = atan2(second.y - first.y, second.x - first.x)
        cast = Cast(caster, target, t, tick + round(skill.windup / self.dt), angle, skill)
        self.casts.append(cast)
        self._emit(emit, t, 'skill_cast', cast, first.x, first.y, angle=angle)

    def _release(self, t, cast, rider, emit):
        if not rider.alive:
            return
        reach = .18 if cast.skill.name == 'hammer' else .07
        x = rider.x + reach * cos(cast.angle)
        y = rider.y + reach * sin(cast.angle)
        cast.origin = rider.x, rider.y
        if cast.skill.name == 'jarona':
            rider.vx, rider.vy = cast.skill.speed * cos(cast.angle), cast.skill.speed * sin(cast.angle)
            rider.recovery = max(rider.recovery, t + .42)
        for angle in cast.skill.angles:
            self.shots.append(Shot(cast, x, y, cast.angle + angle))
        self._emit(emit, t, 'skill_release', cast, x, y, angle=cast.angle)

    def _contact(self, t, shot, riders, emit):
        cast, skill = shot.cast, shot.cast.skill
        hammer = skill.name == 'hammer'
        for name, rider in riders.items():
            if name == cast.id or not rider.alive or name in cast.hits:
                continue
            dx, dy = rider.x - shot.x, rider.y - shot.y
            distance = hypot(dx, dy)
            gap = abs(distance - shot.traveled) if hammer else distance
            if name == cast.target and gap < skill.hitbox + .21:
                cast.near = min(cast.near if cast.near is not None else gap, gap)
            if gap > skill.hitbox:
                continue
            ox, oy = cast.origin
            angle = atan2(rider.y - oy, rider.x - ox) if hammer else shot.angle
            rider.vx += skill.push * cos(angle)
            rider.vy += skill.push * sin(angle)
            rider.recovery = max(rider.recovery, t + (.32 if hammer else .27))
            rider.hit_t, rider.hit_by = t, cast.id
            rider.skill_hit_t = t
            cast.hits.add(name)
            self.pops.append(dict(t=t, skill=skill.name, x=rider.x, y=rider.y))
            self._emit(emit, t, 'skill_hit', cast, rider.x, rider.y, name, push=skill.push)
            if skill.name == 'jarona':
                source = riders[cast.id]
                source.vx = -.48 * cos(shot.angle)
                source.vy = -.48 * sin(shot.angle)
            if not hammer:
                return True
        return False

    def step(self, t, tick, riders, emit):
        if tick in self.schedule:
            self._begin(t, tick, riders, *self.schedule[tick], emit)
        for cast in self.casts:
            if tick == cast.release_tick:
                self._release(t, cast, riders[cast.id], emit)
        active_shots = []
        for shot in self.shots:
            skill = shot.cast.skill
            step = skill.speed * self.dt
            shot.traveled += step
            if skill.name == 'jarona':
                rider = riders[shot.cast.id]
                if not rider.alive:
                    continue
                shot.x, shot.y = rider.x, rider.y
            elif skill.name != 'hammer':
                shot.x += step * cos(shot.angle)
                shot.y += step * sin(shot.angle)
            if shot.traveled < skill.reach and not self._contact(t, shot, riders, emit):
                active_shots.append(shot)
        self.shots = active_shots
        for cast in self.casts[:]:
            has_shot = any(shot.cast is cast for shot in self.shots)
            if tick <= cast.release_tick or has_shot:
                continue
            if cast.near is not None and cast.target not in cast.hits and riders[cast.target].alive:
                target = riders[cast.target]
                self._emit(emit, t, 'skill_dodge', cast, target.x, target.y, clearance=cast.near)
            self.casts.remove(cast)
        self.pops = [pop for pop in self.pops if t - pop['t'] < .30]

    def snapshot(self, t, riders):
        poses = {}
        for cast in self.casts:
            rider = riders[cast.id]
            recovery = .45 if cast.skill.name == 'jarona' else .28
            if rider.alive and t - cast.at < cast.skill.windup + recovery:
                poses[cast.id] = cast.snapshot(rider.x, rider.y)
        return dict(casts=poses, shots=[shot.snapshot() for shot in self.shots], impacts=self.pops.copy())
