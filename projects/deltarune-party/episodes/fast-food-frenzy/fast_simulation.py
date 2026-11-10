"""Fixed-step replay of the three Fast Food Frenzy runner controls."""

from dataclasses import dataclass, field
from math import copysign, sin, pi

FPS = 60
READY = 2.10
DURATION = 30
FINISH = READY + DURATION
END = 153
FEED = -30
TEAM = ('susie', 'lancer', 'noelle')
LANES = (-.99, 0., .99)
JUMP_TIME = .66
RUSH_TIME = .25

# World-width radius in lanes, longitudinal radius in belt units, top height.
FOODS = {
    'burger': (.46, 11, 36),
    'shake': (.37, 10, 35),
    'hot-dog': (.67, 8, 8),
    'pancakes': (.68, 8, 6),
    'ice-cream': (.36, 8, 7),
    'fries': (.40, 9, 13),
}


@dataclass(frozen=True)
class Drop:
    t: float
    kind: str
    x: float
    cue: str = ''
    quick: bool = False

    @property
    def pickup(self):
        return self.t - .57

    @property
    def rush_start(self):
        return self.pickup + .14


# These are the solo player's inputs. The match derives the routes and
# outcome by applying them to the same belt seen on the runner's screen.
DROPS = (
    Drop(1.23, 'fries', .99, 'lancer'),
    Drop(3.06, 'hot-dog', -.495),
    Drop(5.01, 'shake', .99, quick=True),
    Drop(7.18, 'burger', -.99, 'susie'),
    Drop(9.48, 'burger', -.99, quick=True),
    Drop(11.38, 'ice-cream', .99, 'lancer-feint'),
    Drop(13.14, 'pancakes', -.495, 'lancer', quick=True),
    Drop(15.19, 'hot-dog', -.495),
    Drop(17.05, 'shake', -.99),
    Drop(18.81, 'pancakes', .495),
    Drop(20.49, 'burger', 0., quick=True),
    Drop(22.26, 'fries', .99, 'noelle'),
    Drop(24.01, 'ice-cream', -.99, quick=True),
    Drop(25.78, 'burger', .99),
    Drop(27.31, 'hot-dog', .495),
)


@dataclass
class Runner:
    id: str
    x: float
    z: float
    lane: float
    depth: float
    stride: float = 0
    facing: str = 'down'
    status: str = ''
    status_until: float = 0
    jump: float = -4
    pushed: float = 0
    side_push: float = 0
    out: float | None = None
    last_dodge: float = -2
    last_hop: float = -2
    dash_until: float = 0
    syrup_x: float = 0
    syrup_since: float = 0
    cue_seen: set = field(default_factory=set)


@dataclass
class Food:
    id: int
    plan: Drop
    z: float
    contacted: set
    entered: bool = False


@dataclass(frozen=True)
class Pose:
    id: str
    x: float
    z: float
    height: float
    stride: float
    facing: str
    status: str
    out: float | None


@dataclass(frozen=True)
class World:
    runners: tuple
    food: tuple
    travel: float
    speed: float


def clamp(value, low, high):
    return max(low, min(high, value))


def belt_speed(t):
    return 21 + 18 * (clamp(t / DURATION, 0, 1) ** 1.20)


def height(runner, t):
    elapsed = t - runner.jump
    return 23 * sin(pi * elapsed / JUMP_TIME) if 0 < elapsed < JUMP_TIME else 0


def move_toward(current, target, maximum):
    difference = target - current
    return current + copysign(min(abs(difference), maximum), difference)


def obstacles(runner, foods):
    return [
        food for food in foods
        if runner.id not in food.contacted and -8 <= runner.z - food.z < 69
    ]


def approaching(runner, food, speed):
    return (runner.z - food.z - FOODS[food.plan.kind][1]) / speed


def flee_lane(runner, threats, speed, actors):
    def lane_score(x):
        lane_preference = .30 if runner.id == 'lancer' else .13
        cost = .24 * abs(x - runner.x) + lane_preference * abs(x - runner.lane)
        for food in threats:
            rx, _, _ = FOODS[food.plan.kind]
            hit = max(0, rx + .20 - abs(x - food.plan.x))
            if hit:
                time = max(.05, approaching(runner, food, speed))
                cost += 4.5 * hit / (time + .28)
        for other in actors:
            if other is not runner and other.out is None and abs(runner.z - other.z) < 21:
                cost += max(0, .52 - abs(x - other.x)) * .20
        return cost
    return min(LANES, key=lane_score)


def begin_jump(runner, t, report, food, reason):
    if t - runner.jump < JUMP_TIME + .09:
        return False
    runner.jump = t
    report('jump', t, player=runner.id, food=food.plan.kind if food else None,
           obstacle=food.id if food else None, reason=reason)
    return True


def runner_input(runner, t, speed, foods, actors, report):
    threats = obstacles(runner, foods)
    if runner.status == 'sticky':
        if t - runner.last_hop > .79 and t - runner.jump > JUMP_TIME + .09:
            runner.last_hop = t
            begin_jump(runner, t, report, None, 'unstick')
            runner.status_until -= .21
        # Each pull runs into the same syrup patch and the belt keeps moving.
        age = t - runner.syrup_since
        return runner.syrup_x + .19 * sin(age * 2 * pi / .82)
    if runner.status in ('blocked', 'stunned', 'frozen'):
        return runner.x
    signature = next((food for food in threats if food.plan.cue == runner.id), None)
    if signature and approaching(runner, signature, speed) < 1.38:
        if signature.id not in runner.cue_seen:
            if approaching(runner, signature, speed) <= (.45 if runner.id != 'susie' else .60):
                reason = 'challenge' if runner.id == 'susie' else (
                    'vault' if signature.plan.kind == 'fries' else 'step')
                if begin_jump(runner, t, report, signature, reason):
                    runner.cue_seen.add(signature.id)
            return signature.plan.x
        if t - runner.jump < JUMP_TIME:
            return signature.plan.x
    if runner.id == 'lancer':
        feint = next((food for food in threats if food.plan.cue == 'lancer-feint'), None)
        if feint and .83 < approaching(runner, feint, speed) < 1.90:
            return feint.plan.x
    target = flee_lane(runner, threats, speed, actors)
    if threats and abs(runner.x - target) > .55 and t - runner.last_dodge > .52:
        food = min(threats, key=lambda hazard: abs(approaching(runner, hazard, speed)))
        rush = runner.id == 'lancer'
        if approaching(runner, food, speed) < (1.60 if rush else 1.15):
            runner.last_dodge = t
            report('dodge', t, player=runner.id, food=food.plan.kind, obstacle=food.id,
                   lane=target, gap=round(runner.z - food.z, 2))
            if rush:
                runner.dash_until = t + .37
                report('dash', t, player=runner.id, food=food.plan.kind, obstacle=food.id, lane=target)
    return target


def impact(runner, food, t, report):
    kind = food.plan.kind
    rx, rz, top = FOODS[kind]
    dx, dz = abs(runner.x - food.plan.x), abs(runner.z - food.z)
    if dx > rx + .13 or dz > rz + 2:
        return
    h = height(runner, t)
    descending = JUMP_TIME / 2 < t - runner.jump < JUMP_TIME
    if h > top:
        return
    if kind == 'fries' and t - runner.jump < JUMP_TIME and (h > 3 or descending):
        food.contacted.add(runner.id)
        report('clear', t, player=runner.id, food=kind, obstacle=food.id)
        return
    if kind in ('pancakes', 'ice-cream', 'hot-dog') and not descending and h > 1:
        return

    food.contacted.add(runner.id)
    if kind in ('burger', 'shake'):
        runner.status, hold, push = 'blocked', (1.53 if food.plan.cue == 'susie' else .64), 36
        runner.jump = -4
        direction = runner.x - food.plan.x
        if abs(direction) < .04:
            direction = -food.plan.x or 1
        runner.side_push = copysign(1.85 if food.plan.cue == 'susie' else .38, direction)
    elif kind == 'pancakes' and descending:
        runner.status, hold, push = 'sticky', 3.90, 2
        runner.syrup_x = runner.x
        runner.syrup_since = t
    elif kind == 'ice-cream' and descending:
        runner.status, hold, push = 'frozen', 1.14, 3
    elif kind == 'hot-dog' and descending:
        runner.status, hold, push = 'stunned', .65, 12
    else:
        runner.status, hold, push = 'blocked', .33, 26 if kind == 'fries' else 13
    runner.status_until = t + hold
    runner.pushed = push
    report('impact', t, player=runner.id, food=kind, obstacle=food.id, status=runner.status,
           x=round(runner.x, 3), depth=round(runner.z, 3), airborne=round(h, 2))
    if runner.status == 'sticky':
        report('sticky', t, player=runner.id, food=kind, obstacle=food.id)


def simulate():
    actors = [
        Runner('susie', -.91, 115, -.99, 110),
        Runner('lancer', .02, 115, 0, 89),
        Runner('noelle', .88, 115, .99, 61),
    ]
    foods, frames, events = [], [], []
    travel = 0.
    remaining = tuple(TEAM)

    def report(kind, t, **extra):
        events.append(dict(type=kind, t=round(READY + t, 6), **extra))

    report('go', 0)
    for index, plan in enumerate(DROPS):
        report('food_pickup', plan.pickup, player='flowery', food=plan.kind, obstacle=index, lane=plan.x)
        if plan.quick:
            report('flowery_delivery', plan.rush_start, player='flowery', food=plan.kind,
                   obstacle=index, lane=plan.x, quip='* JARONA!')
        report('drop', plan.t, player='flowery', food=plan.kind, obstacle=index, lane=plan.x)
    for step in range(DURATION * FPS + 1):
        t = step / FPS
        speed = belt_speed(t)
        if step in (10 * FPS, 20 * FPS):
            report('belt_speed', t, speed=round(speed, 2))
        for index, plan in enumerate(DROPS):
            if step == round(plan.t * FPS):
                foods.append(Food(index, plan, FEED, set()))
        for food in foods:
            if step:
                food.z += speed / FPS
            if not food.entered and food.z >= 0:
                food.entered = True
                report('food_enter', t, food=food.plan.kind, obstacle=food.id, lane=food.plan.x)
        foods = [food for food in foods if food.z < END + 20]
        for runner in actors:
            if runner.out is not None:
                continue
            if runner.status and t >= runner.status_until:
                report('recover', t, player=runner.id, status=runner.status)
                runner.status = ''
            target = runner_input(runner, t, speed, foods, actors, report)
            old_x = runner.x
            lateral = 2.75 if runner.id == 'noelle' else 2.20
            dashing = runner.id == 'lancer' and t < runner.dash_until and not runner.status
            if dashing:
                lateral = 3.52
            if runner.status == 'sticky':
                lateral *= .41
            runner.x = clamp(move_toward(runner.x, target, lateral / FPS) + runner.side_push / FPS,
                             -1.22, 1.22)
            runner.side_push = move_toward(runner.side_push, 0, 3.25 / FPS)
            dx = runner.x - old_x
            if abs(dx) > .009:
                runner.facing = 'left' if dx < 0 else 'right'
            else:
                runner.facing = 'down'
            limit = 50 if runner.id == 'noelle' else 45
            effort = clamp(speed + (runner.z - runner.depth) * 1.85 + 8 * dashing, 0, limit)
            if runner.status == 'sticky':
                effort *= .23
            elif runner.status == 'blocked':
                effort *= .04
            elif runner.status in ('frozen', 'stunned'):
                effort = 0
            runner.z = max(11, runner.z + (speed - effort + runner.pushed) / FPS)
            runner.pushed = max(0, runner.pushed - 65 / FPS)
            scramble = 18 if runner.status == 'sticky' else 0
            runner.stride += (effort + abs(dx) * FPS * 8 + scramble) / FPS
            for food in foods:
                if runner.id not in food.contacted:
                    impact(runner, food, t, report)
            if runner.z >= END:
                runner.out = t
                report('out', t, player=runner.id, x=round(runner.x, 3), status=runner.status)
        travel += speed / FPS
        poses = tuple(Pose(runner.id, runner.x, runner.z, height(runner, t), runner.stride,
                           runner.facing, runner.status, runner.out) for runner in actors)
        frames.append(World(poses, tuple((food.id, food.plan.kind, food.plan.x, food.z) for food in foods),
                            travel, speed))
        remaining = tuple(runner.id for runner in actors if runner.out is None)
        if not remaining:
            break
    play_time = (len(frames) - 1) / FPS
    winner = 'team' if remaining else 'flowery'
    report('finish', play_time, winner=winner, survivors=remaining)
    return frames, sorted(events, key=lambda event: event['t']), winner, remaining
