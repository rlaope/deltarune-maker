"""Live steering for the Boo Tag cast, in native screen-space coordinates."""

from functools import lru_cache
from heapq import heappop, heappush
from math import hypot

NAMES = ('kris', 'susie', 'ralsei', 'gerson')
START = ((79, 38), (106, 41), (84, 99), (69, 102))
INITIAL_ENTRY = ((65, 40), (120, 39), (95, 110), (63, 110))
RUN_SPEED = (40, 43, 37, 39)
CHASE_SPEED = (56, 59, 48, 54)


def gap(a, b):
    return hypot(a[0] - b[0], a[1] - b[1])


def segment_crosses(a, b, poly):
    """Clip a segment against the inward edges of a convex footprint."""
    near, far = 0., 1.
    dx, dy = b[0] - a[0], b[1] - a[1]
    for (x0, y0), (x1, y1) in zip(poly, (*poly[1:], poly[0])):
        ex, ey = x1 - x0, y1 - y0
        v = ex * (a[1] - y0) - ey * (a[0] - x0)
        rate = ex * dy - ey * dx
        if abs(rate) < .0001:
            if v < 0:
                return False
            continue
        hit = -v / rate
        if rate > 0:
            near = max(near, hit)
        else:
            far = min(far, hit)
        if near > far:
            return False
    return True


class Nav:
    def __init__(self, treasure, blocked):
        self.treasure = treasure
        self.bounds = tuple((min(x for x, _ in p), min(y for _, y in p),
                             max(x for x, _ in p), max(y for _, y in p)) for _, p in treasure)
        self.nodes = tuple((x, y) for y in range(31, 156, 12) for x in range(25, 229, 12)
                           if x >= 29 - (y - 29) * .108 and
                           all(not blocked((x + dx, y + dy)) for dx, dy in
                               ((0, 0), (2, 0), (-2, 0), (0, 2), (0, -2))))
        self.node_index = {p: i for i, p in enumerate(self.nodes)}
        self.links = []
        for x, y in self.nodes:
            links = []
            for dx, dy in ((12, 0), (-12, 0), (0, 12), (0, -12), (12, 12), (12, -12), (-12, 12), (-12, -12)):
                q = x + dx, y + dy
                if q in self.node_index and self.cover((x, y), q) is None:
                    links.append((self.node_index[q], hypot(dx, dy)))
            self.links.append(links)

    def cover(self, a, b):
        x0, x1 = sorted((a[0], b[0]))
        y0, y1 = sorted((a[1], b[1]))
        for index, ((_, poly), (l, t, r, d)) in enumerate(zip(self.treasure, self.bounds)):
            if x1 >= l and x0 <= r and y1 >= t and y0 <= d and segment_crosses(a, b, poly):
                return index
        return None

    @lru_cache(maxsize=8192)
    def astar(self, start, end):
        if start == end:
            return (start,)
        queue = [(0., 0., start)]
        visited = {start: (0., None)}
        while queue:
            _, cost, here = heappop(queue)
            if here == end:
                route = [here]
                while (here := visited[here][1]) is not None:
                    route.append(here)
                return tuple(reversed(route))
            if visited[here][0] < cost:
                continue
            for step, increment in self.links[here]:
                path_cost = cost + increment
                if step in visited and visited[step][0] <= path_cost:
                    continue
                visited[step] = path_cost, here
                heuristic = gap(self.nodes[step], self.nodes[end])
                heappush(queue, (path_cost + heuristic, path_cost, step))
        return ()

    def path(self, pos, goal):
        if self.cover(pos, goal) is None:
            return (goal,)
        links = sorted((gap(pos, p), i) for i, p in enumerate(self.nodes) if gap(pos, p) < 36)
        start = next((i for _, i in links if self.cover(pos, self.nodes[i]) is None), None)
        end = self.node_index.get(goal)
        if start is None or end is None:
            return ()
        route = self.astar(start, end)
        return tuple(self.nodes[i] for i in route)


class Chase:
    def __init__(self, treasure, blocked, fps):
        self.nav = Nav(treasure, blocked)
        self.period = max(1, round(.20 * fps))
        self.fps = fps
        self.goals = [None] * 4
        self.routes = [()] * 4
        self.modes = [None] * 4
        self.targets = [None] * 4
        self.threats = [None] * 4
        self.previous_owners = (None, None)

    def seek(self, who, pos, threat, p, velocities, friendly=False):
        other = p[threat]
        enemy_v = velocities[threat]
        projected = (other[0] + enemy_v[0] * .18, other[1] + enemy_v[1] * .18)
        current_gap = gap(pos, other)
        current_cover = self.nav.cover(other, pos)
        previous_goal = self.goals[who]
        if not friendly and current_cover is not None and current_gap > 47 and gap(pos, previous_goal or pos) < 10:
            if not any(gap(pos, xy) < 18 for j, xy in enumerate(p) if j not in (who, threat)):
                return pos, (), current_cover

        candidates = []
        for q in self.nav.nodes:
            trip = gap(pos, q)
            if trip < (12 if friendly else 17) or trip > (53 if friendly else 71):
                continue
            cover = self.nav.cover(projected, q)
            future_gap = gap(projected, q)
            squad_gap = min(gap(q, xy) for j, xy in enumerate(p) if j not in (who, threat))
            wall_bonus = (7 if friendly else 27) if cover is not None else 0
            inertia = 5 if previous_goal is not None and gap(previous_goal, q) < 11 else 0
            crowded = max(0, 27 - squad_gap) * (1.3 if friendly else .52)
            score = min(future_gap, 112) + wall_bonus + inertia - .48 * trip - crowded
            candidates.append((score, q, cover))
        for _, goal, cover in sorted(candidates, reverse=True):
            route = self.nav.path(pos, goal)
            if route:
                return goal, route, cover
        return pos, (), current_cover

    def _decide_runner(self, i, p, velocities, owners, friendly, report):
        hostile = [j for j in owners if j is not None and j != i]
        if friendly:
            hostile = [j for j in range(4) if j != i]
        if not hostile:
            return
        threat = min(hostile, key=lambda j: gap(p[i], p[j]))
        goal, path, cover = self.seek(i, p[i], threat, p, velocities, friendly)
        changed = self.modes[i] != ('stroll' if friendly else 'evade') or self.threats[i] != threat
        changed |= self.goals[i] != goal and (self.goals[i] is None or gap(self.goals[i], goal) >= 15)
        if changed and not friendly:
            report('evade_cover' if cover is not None else 'evade_turn', i, threat=threat,
                   goal=goal, route=path, cover=cover, gap=gap(p[i], p[threat]), speed=RUN_SPEED[i])
        self.goals[i], self.routes[i] = goal, path
        self.threats[i] = threat
        self.modes[i] = 'stroll' if friendly else 'evade'

    def _pick(self, i, p, owners, immune, stage, offer):
        valid = [j for j in range(4) if j not in owners and j != immune]
        if not valid:
            valid = [j for j in range(4) if j not in owners]
        if offer and 2 in valid and owners[1] is None:
            return 2
        if stage == 0 and i == 0 and 1 in valid:
            return 1
        if stage == 1 and i == 1 and 3 in valid:
            return 3
        nearest = min(valid, key=lambda j: gap(p[i], p[j]))
        previous = self.targets[i]
        if previous in valid and gap(p[i], p[previous]) <= gap(p[i], p[nearest]) + 11:
            return previous
        return nearest

    def steer(self, tick, p, velocities, owners, protected, stage, adopted, offer, report):
        changed = tuple(owners) != self.previous_owners
        self.previous_owners = tuple(owners)
        decision = changed or tick % self.period == 0
        result = []
        for i, pos in enumerate(p):
            if i in owners and not (i == 2 and adopted):
                ghost = owners.index(i)
                target = self._pick(i, p, owners, protected[ghost], stage, offer)
                if changed or self.targets[i] != target:
                    report('chase_target', i, target=target, gap=gap(pos, p[target]), speed=CHASE_SPEED[i])
                self.targets[i] = target
                self.modes[i] = 'chase'
                separation = gap(pos, p[target])
                anticipation = min(.18, separation / 220)
                vx, vy = velocities[target]
                goal = (p[target][0] + anticipation * vx, p[target][1] + anticipation * vy)
                result.append((goal, CHASE_SPEED[i]))
                continue
            if owners == [None, None]:
                result.append((pos, 0))
                continue
            if stage == 0 and owners == [0, None] and i == 1:
                # Susie sees a shortcut and lets Kris reach her.
                aim = (p[0][0] + 14, p[0][1] + 3)
                result.append((aim, 12))
                continue
            if stage == 0 and owners == [0, None] and i in (2, 3):
                result.append((pos, 0))
                continue
            if stage == 1 and owners == [1, None] and i == 2:
                # Ralsei drifts over to check on Gerson, across Susie's line.
                aim = (p[3][0] + 10, p[3][1] - 12)
                result.append((aim, 19))
                continue
            if offer and i == 2 and i not in owners and owners[0] is not None:
                holder = p[owners[0]]
                if gap(pos, holder) <= 27:
                    result.append((pos, 0))
                    continue
            friendly = i in owners and i == 2 and adopted
            if decision or self.modes[i] not in ('evade', 'stroll'):
                self._decide_runner(i, p, velocities, owners, friendly, report)
            route = self.routes[i]
            while route and gap(pos, route[0]) <= 2:
                route = route[1:]
            self.routes[i] = route
            goal = route[0] if route else pos
            result.append((goal, 17 if friendly else RUN_SPEED[i]))
        return tuple(result)
