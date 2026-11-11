"""Deterministic crowded movement with births, local contacts, and shared intentions."""

from math import ceil, pi

import numpy as np


class Crowd:
    """Cache a 30 Hz physical crowd and interpolate it on the film's clock.

    IDs are array indices. Positions are world foot coordinates, velocities are
    world units per second, and contacts describe the most recent body contact.
    """

    rate = 30
    perspective = .70

    def __init__(self, story):
        self.duration = story.DURATION
        self.changes = tuple(story.DOUBLINGS)
        self.total_maximum = self.changes[-1]['to']
        self.maximum = min(1024, self.total_maximum)
        self.times = story.TIMES
        self.collision_events = []
        self.frames = ceil(self.duration * self.rate) + 1
        random = np.random.default_rng(731)
        self.radii = random.uniform(9.2, 11.5, self.maximum)
        angles = random.uniform(0, 2 * pi, self.maximum)
        distances = np.sqrt(random.uniform(.05, .98, self.maximum))
        self.homes = np.column_stack((np.cos(angles), np.sin(angles))) * distances[:, None]
        decisions = ceil(self.duration / 2.6) + 2
        self.decisions = random.uniform(-1, 1, (decisions, self.maximum, 2))
        self.turn_period = random.uniform(2.6, 4.6, self.maximum)
        self.birth_times = np.zeros(self.maximum)
        for change in self.changes:
            self.birth_times[change['from']:min(self.maximum, change['to'])] = change['t']
        self.positions = np.zeros((self.frames, self.maximum, 2), dtype=np.float32)
        self.velocities = np.zeros_like(self.positions)
        self.contacts = np.zeros((self.frames, self.maximum), dtype=np.float32)
        self.counts = np.ones(self.frames, dtype=np.int32)
        self.falls = np.full((self.frames, self.maximum), -1, dtype=np.float32)
        self._simulate()
        self._prepare_layers()

    @staticmethod
    def _ease(value):
        value = np.clip(value, 0, 1)
        return value * value * (3 - 2 * value)

    @staticmethod
    def _pairs(points):
        cells = {}
        for identity, cell in enumerate(np.floor(points / 23).astype(np.int32)):
            cells.setdefault((int(cell[0]), int(cell[1])), []).append(identity)
        pairs = []
        for (x, y), members in cells.items():
            pairs.extend((a, b) for index, a in enumerate(members) for b in members[index + 1:])
            for dx, dy in ((0, 1), (1, -1), (1, 0), (1, 1)):
                neighbours = cells.get((x + dx, y + dy), ())
                pairs.extend((a, b) for a in members for b in neighbours)
        return np.asarray(pairs, dtype=np.int32).reshape(-1, 2)

    def _goals(self, t, count):
        radius = max(18, 20.5 * np.sqrt(count))
        chase = 150 * self._ease((t - self.times['run']) / 3.9)
        goals = self.homes[:count] * radius
        goals[:, 1] -= radius * .95
        goals[:, 0] += chase
        decisions = np.floor(t / self.turn_period[:count]).astype(int)
        goals += self.decisions[decisions, np.arange(count)] * 35
        goals[:, 1] = np.minimum(goals[:, 1], -4)
        goals[0] = chase, 0
        if t >= self.times['run']:
            pursuit = self._ease((t - self.times['run']) / 3.9)
            goals[0] = max(0, -57 + 228 * pursuit), (8 + 23 * pursuit) / self.perspective
        if 16.15 <= t < 22.8:
            amount = self._ease((t - 16.15) / 1.5) * (1 - self._ease((t - 21.5) / 1.3))
            delivery = np.array(((85, -3), (-52, 8), (-12, -13)), dtype=float)
            if t < 17.7:
                delivery[1] = 35, 18
            elif t < 19.6:
                delivery[1] = -52, 18
            delivery[:, 1] /= self.perspective
            goals[1:4] += amount * (delivery - goals[1:4])
            if 19.1 <= t < 22.8:
                hold = 1 - self._ease((t - 22.1) / .7)
                goals[2] += hold * (delivery[1] - goals[2])
        if t >= self.times['stop']:
            ids = np.arange(1, min(9, count))
            angles = 1.1 + ids * .64
            waiting = np.column_stack((145 + 38 * np.cos(angles),
                                       (3 - 28 * np.abs(np.sin(angles))) / self.perspective))
            amount = self._ease((t - self.times['stop'] - ids * .10) / 1.5)
            goals[ids] += amount[:, None] * (waiting - goals[ids])
        # Two helpers walk into the open foreground then cross one another.
        if count > 6 and 20.5 <= t < 27.5:
            progress = self._ease((t - 22.2) / 1.10)
            goals[5] = -48 + 55 * progress, 7 / self.perspective
            goals[6] = 48 - 55 * progress, 7 / self.perspective
            for j in range(1,count):
                if j not in (5,6) and abs(goals[j,0])<65 and goals[j,1]>-25:
                    goals[j,1] -= 38
        for begin, a, b, center in ((32.,7,10,30.),(46.5,1,3,-20.)):
            if count > b and begin-1.8 <= t < begin+4.5:
                crossing=self._ease((t-begin)/1.1)
                goals[a]=(center-42+52*crossing),4/self.perspective
                goals[b]=(center+42-52*crossing),4/self.perspective
        return goals

    def _resolve(self, points, t, weights, pairs):
        contact = np.zeros(len(points))
        if len(pairs) == 0:
            return contact
        a, b = pairs.T
        maturity = self._ease((t - self.birth_times[:len(points)]) / .65)
        distance_needed = (self.radii[a] + self.radii[b]) * np.minimum(maturity[a], maturity[b])
        for _ in range(8):
            delta = points[b] - points[a]
            distance = np.linalg.norm(delta, axis=1)
            overlap = distance_needed - distance
            touching = overlap > 0
            if not np.any(touching):
                break
            left, right = a[touching], b[touching]
            direction = delta[touching] / np.maximum(distance[touching, None], 1e-8)
            coincident = distance[touching] < 1e-8
            angles = (left[coincident] * .731 + right[coincident] * 2.399) % (2 * pi)
            direction[coincident] = np.column_stack((np.cos(angles), np.sin(angles)))
            amount = np.minimum(overlap[touching] * .48, 2.5)
            mass = weights[left] + weights[right]
            correction = direction * amount[:, None]
            np.add.at(points, left, -correction * (weights[left] / mass)[:, None])
            np.add.at(points, right, correction * (weights[right] / mass)[:, None])
            strength = np.minimum(1, overlap[touching] / 5)
            np.maximum.at(contact, left, strength)
            np.maximum.at(contact, right, strength)
        return contact

    def _simulate(self):
        points = np.zeros((self.maximum, 2))
        velocity = np.zeros_like(points)
        count = 1
        births = {round(change['t'] * self.rate): change for change in self.changes if change['to'] <= self.maximum}
        fallen_since = np.full(self.maximum, -1.)
        cooldown = np.zeros(self.maximum)
        hug_origin = None
        for frame in range(1, self.frames):
            t = frame / self.rate
            previous = points[:count].copy()
            goals = self._goals(t, count)
            intended = (goals - points[:count]) * 2.1
            speed = np.linalg.norm(intended, axis=1)
            limit = 46 if self.times['run'] <= t < (self.times['stop'] + .3) else 29
            intended *= np.minimum(1, limit / np.maximum(speed, 1e-8))[:, None]
            pursuit = (goals[0] - points[0]) * 6
            leader_speed = 75 if self.times['run'] <= t < self.times['stop'] else 35
            intended[0] = pursuit * min(1, leader_speed / max(np.linalg.norm(pursuit), 1e-8))
            if 16.15 <= t < 22.8:
                intended[1:4] = np.clip((goals[1:4] - points[1:4]) * 3, -52, 52)
            if count > 6 and 20.5 <= t < 23.6:
                intended[5:7] = np.clip((goals[5:7] - points[5:7]) * 5, -65, 65)
            down = (fallen_since[:count] >= 0) & (t - fallen_since[:count] < 3.6)
            intended[down] *= .05
            velocity[:count] += (intended - velocity[:count]) * .22
            points[:count] += velocity[:count] / self.rate
            weights = np.ones(count)
            weights[0] = .08
            for begin,a,b,_ in ((32.,7,10,30.),(46.5,1,3,-20.)):
                if count>b and begin-1.8 <= t < begin+4.5:
                    weights[[a,b]]=.03
            if 16.15 <= t < 22.8:
                weights[2] = .25
            if count > 6 and 20.5 <= t < 27.5:
                weights[5:7] = .03
            if t >= self.times['stop']:
                if hug_origin is None:
                    hug_origin = previous[0].copy()
                target = np.array((171, 31 / self.perspective))
                points[0] = hug_origin + (target - hug_origin) * self._ease((t - self.times['stop']) / .7)
                weights[0] = 0
            pairs = self._pairs(points[:count])
            before_contact = points[:count].copy()
            contacts = self._resolve(points[:count], t, weights, pairs)
            displacement = points[:count] - before_contact
            # Falls are caused by measured contact correction, never independent pose jitter.
            for identity in range(1, min(count, 32)):
                impact = float(np.linalg.norm(displacement[identity]))
                expected = 6 if identity==5 and 22.65<=t<24 else 10 if identity==7 and 32<=t<34 else 3 if identity==1 and 46.5<=t<48.5 else None
                eligible = expected is not None and np.linalg.norm(points[identity]-points[expected]) < self.radii[identity]+self.radii[expected]+1
                secondary = identity % 7 == 3 and t > 29 and impact > 1.8
                if (eligible and contacts[identity] > .05 or secondary) and t > cooldown[identity]:
                    fallen_since[identity] = t
                    cooldown[identity] = t + 9
                    neighbours = np.linalg.norm(points[:count] - points[identity], axis=1)
                    neighbours[identity] = np.inf
                    partner = expected if eligible else int(np.argmin(neighbours))
                    self.collision_events.append({'id': identity, 'visible': bool(t < 50), 'partner': partner, 'time': t, 'fall_time': t, 'recovery_time': t + 3.6, 'x': float(points[identity,0]), 'y': float(points[identity,1]*self.perspective), 'contact': float(contacts[identity]), 'displacement': displacement[identity].tolist()})
            self.falls[frame, :count] = fallen_since[:count]
            # A curved front leaves room for the observers without forming a straight rank.
            radius = max(35, 20.5 * np.sqrt(count))
            center = 150 * self._ease((t - self.times['run']) / 3.9)
            side = np.minimum(1, np.abs(points[:count, 0] - center) / (radius * 1.15))
            foreground = (15 if t >= self.times['stop'] else 8) - radius * .22 * side ** 2
            foreground[0] = np.inf
            if 16.15 <= t < 22.8:
                foreground[2] = 18 if t < 19.6 else 8
            intrusion = np.maximum(0, points[:count, 1] * self.perspective - foreground)
            points[:count, 1] -= np.minimum(intrusion * .35, 1.4) / self.perspective
            if t < self.times['run']:
                points[0, 1] = min(points[0, 1], 8 / self.perspective)
            velocity[:count] = (points[:count] - previous) * self.rate
            # Brief contact impulses are damped so a bump causes a recoverable step.
            speed = np.linalg.norm(velocity[:count], axis=1)
            velocity[:count] *= np.minimum(1, 75 / np.maximum(speed, 1e-8))[:, None]
            if frame in births:
                change = births[frame]
                parents = change['from']
                points[parents:change['to']] = points[:parents]
                angle = (np.arange(parents) * 2.399 + frame * .13) % (2 * pi)
                impulse = np.column_stack((np.cos(angle), np.sin(angle))) * 32
                velocity[parents:change['to']] = velocity[:parents] + impulse
                velocity[:parents] -= impulse * .45
                count = change['to']
                contacts = np.pad(contacts, (0, count - len(contacts)))
            contacts = np.maximum(contacts, self.contacts[frame - 1, :count] * .82)
            self.positions[frame, :count] = points[:count] * (1, self.perspective)
            self.velocities[frame, :count] = velocity[:count] * (1, self.perspective)
            self.contacts[frame, :count] = contacts
            self.counts[frame] = count

    def _core_sample(self, t):
        clock = min(self.frames - 1, max(0, round(t * self.rate, 9)))
        frame = int(clock)
        after = min(frame + 1, self.frames - 1)
        fraction = clock - frame
        count = int(self.counts[frame])
        positions = self.positions[frame, :count] * (1 - fraction) + self.positions[after, :count] * fraction
        return {
            'count': count,
            'positions': positions,
            'velocities': self.velocities[frame, :count].copy(),
            'contacts': self.contacts[frame, :count].copy(),
            'falls': self.falls[frame, :count].copy(),
        }

    def bounds(self, t):
        positions = self.sample(t)['positions']
        return (*positions.min(axis=0), *positions.max(axis=0))

    def _prepare_layers(self):
        self.layers = []
        random = np.random.default_rng(8291)
        for change in self.changes:
            if change['from'] < self.maximum:
                continue
            parent = self.sample(change['t'])['positions']
            number = change['to']
            angle = random.uniform(0, 2 * pi, number)
            radius = np.sqrt(random.uniform(.02, 1, number)) * 20.5 * np.sqrt(number)
            # Lobed outline and variable density: no lattice or row template.
            radius *= 1 + .13 * np.cos(angle * 3) + .09 * np.sin(angle * 5)
            goal = np.column_stack((150 + radius * np.cos(angle),
                                    (radius * np.sin(angle) - 20.5 * np.sqrt(number)) * self.perspective))
            start = np.concatenate((parent, parent), axis=0)
            self.layers.append({'time': change['t'], 'start': start, 'goal': goal})

    def sample(self, t):
        base = self._core_sample(t)
        active = next((layer for layer in reversed(self.layers) if t >= layer['time']), None) if hasattr(self, 'layers') else None
        if active is None:
            base['ids'] = np.arange(base['count'])
            return base
        elapsed = t - active['time']
        amount = self._ease(elapsed / 3.5)
        positions = active['start'] + (active['goal'] - active['start']) * amount
        # Keep the observed foreground population on the same physical simulation.
        positions[:self.maximum] = base['positions']
        count = len(positions)
        velocities = (active['goal'] - active['start']) * (6 * np.clip(elapsed / 3.5,0,1) * (1 - np.clip(elapsed / 3.5,0,1)) / 3.5)
        velocities[:self.maximum] = base['velocities']
        return {'count': count, 'ids': np.arange(count), 'positions': positions,
                'velocities': velocities, 'contacts': np.pad(base['contacts'], (0,count-self.maximum)),
                'falls': np.pad(base['falls'], (0,count-self.maximum),constant_values=-1)}
