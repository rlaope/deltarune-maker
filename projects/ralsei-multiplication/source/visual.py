"""Original DELTARUNE art, staged on the multiplication episode's shared clock."""

from functools import lru_cache
import json
from math import cos, pi, sin
from pathlib import Path

from PIL import Image, ImageDraw

from crowd import Crowd
import numpy as np
from cosmic import cosmic_frame


ROOT = Path(__file__).resolve().parent
NEAR = Image.Resampling.NEAREST


def ease(value):
    value = min(1, max(0, value))
    return value * value * (3 - 2 * value)


def blend(a, b, amount):
    return a + (b - a) * amount


def ramp(t, start, end):
    return ease((t - start) / (end - start))


class NativeFont:
    def __init__(self, spec):
        self.atlas = Image.open(ROOT / spec['path']).convert('RGBA')
        self.glyphs = spec['glyphs']

    def width(self, text, scale=1):
        return sum(self.glyphs[str(ord(char))]['shift'] + 1 for char in text) * scale

    def wrap(self, text, width, scale=1):
        lines = ['']
        for word in text.split():
            candidate = (lines[-1] + ' ' + word).strip()
            if self.width(candidate, scale) > width and lines[-1]:
                lines.append(word)
            else:
                lines[-1] = candidate
        if any(self.width(line, scale) > width for line in lines):
            raise ValueError(f'Text exceeds its dialogue box: {text}')
        return lines

    @lru_cache(maxsize=512)
    def render(self, text, scale=1):
        image = Image.new('RGBA', (max(1, round(self.width(text))), 20))
        x = 0
        for char in text:
            glyph = self.glyphs[str(ord(char))]
            ink = self.atlas.crop((glyph['x'], glyph['y'], glyph['x'] + glyph['w'],
                                   glyph['y'] + glyph['h']))
            image.alpha_composite(ink, (x + glyph['offset'], 0))
            x += glyph['shift'] + 1
        return image.resize((max(1, round(image.width * scale)), round(20 * scale)), NEAR)

    def draw(self, image, text, x, y, scale=1, center=False):
        ink = self.render(text, scale)
        image.paste(ink, (round(x - ink.width / 2) if center else round(x), round(y)), ink)


class Visual:
    def __init__(self, story):
        self.story = story
        native = json.loads((ROOT / 'assets/native.json').read_text())
        town = json.loads((ROOT / 'assets/town/town.json').read_text())
        extra = json.loads((ROOT / 'assets/extras.json').read_text())
        observers = json.loads((ROOT / 'assets/observers.json').read_text())
        staging = json.loads((ROOT / 'assets/staging-v3.json').read_text())
        self.specs = {**staging['sprites'], **native['sprites'], **town['sprites'], **extra['sprites'], **observers['sprites']}
        self.crowd = Crowd(story)
        final_bounds = [self.crowd.bounds(time) for time in (90.5, 91, 91.9)]
        left = min(bounds[0] for bounds in final_bounds) - 14
        top = min(bounds[1] for bounds in final_bounds) - 48
        right = max(bounds[2] for bounds in final_bounds) + 14
        bottom = max(bounds[3] for bounds in final_bounds)
        self.final_focus = (left + right) / 2
        self.final_zoom = min(320 / (right - left), 270 / (bottom - top))
        self.font = NativeFont(native['fonts']['main'])
        self.small = NativeFont(native['fonts']['small'])
        self.rooms = {name: Image.open(ROOT / spec['path']).convert('RGB')
                      for name, spec in town['rooms'].items()}
        self.images = {}
        for cue in story.DIALOGUE:
            for edition in ('short', 'gameplay'):
                width, scale = (225, 1.5) if edition == 'short' else (470, 1.5)
                if len(self.font.wrap(cue['text'], width, scale)) > 3:
                    raise ValueError(f'Dialogue needs more space: {cue["text"]}')

    def source(self, key, frame):
        frames = self.specs[key]['frames']
        frame %= len(frames)
        identity = key, frame
        if identity not in self.images:
            self.images[identity] = Image.open(ROOT / frames[frame]['path']).convert('RGBA')
        spec = frames[frame]
        anchor = spec.get('footAnchor', self.specs[key].get('footAnchor'))
        return self.images[identity], anchor

    @lru_cache(maxsize=2048)
    def body(self, key, frame, scale, flipped=False):
        source, anchor = self.source(key, frame)
        image = source.resize((max(1, round(source.width * scale)),
                               max(1, round(source.height * scale))), NEAR)
        x, y = anchor or (source.width / 2, source.height)
        if flipped:
            image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            x = source.width - x
        return image, (round(x * scale), round(y * scale))

    def legacy(self, t):
        return float(np.interp(t, [0,22.8,29.65,38.92,41.5,46.9,50,54.55,58.2,62.1,62.8,67.8,72.2,79.2,92],
                              [0,22.8,22.8,31.92,34.3,39.85,42.5,44.55,46.6,50.5,51.2,54.5,59.8,66.7,69.9]))

    def camera(self, t):
        raw_t = t
        t = self.legacy(t)
        shots = (
            (0, 0, 2.25), (12.25, 44, 1.70), (22.6, -20, 1.40), (28.75, -5, 1.12),
            (31.0, -20, 1.75), (33.9, 34, 1.75), (39.6, 0, .68),
            (41.65, -18, 1.80), (46.25, 0, 1.45),
            (50.65, 150, 1.65), (61.1, 135, 1.40),
            (66.7, self.final_focus, self.final_zoom),
        )
        x, zoom = shots[0][1:]
        for index, (start, next_x, next_zoom) in enumerate(shots[1:], 1):
            if t < start:
                break
            amount = ramp(t, start, start + (1.1 if start == 66.7 else .85))
            previous_x, previous_zoom = shots[index - 1][1:]
            if start == 50.65:
                previous_x = 150
            x, zoom = blend(previous_x, next_x, amount), blend(previous_zoom, next_zoom, amount)
        if 46.6 <= t < 50.65:
            x += 150 * ramp(t, 46.6, 50.5)
        if raw_t >= 73:
            bounds = self.crowd.bounds(raw_t)
            left, top, right, bottom = bounds
            target_x = (left + right) / 2
            target_zoom = min(zoom, 318 / (right - left + 90), 230 / (bottom - top + 85))
            transition = ramp(raw_t,73,74.1)
            x,zoom=blend(x,target_x,transition),blend(zoom,target_zoom,transition)
        return x, zoom

    def observers(self, t):
        raw_t=t
        t = self.legacy(t)
        kris_x, kris_y = -44.0, 32.0
        susie_x, susie_y = 4.0, 34.0
        kris_key, susie_key = 'krisUp', 'susieUp'
        kris_frame = susie_frame = 0
        # Each exchange starts with both observers watching the same action.
        if 6.25 <= t < 8 or 10.98 <= t < 12.85 or 20.82 <= t < 22.9:
            susie_key = 'susieLeft'
        if 6.85 <= t < 7.95:
            kris_key = 'krisRight'
            nod = ramp(t, 6.95, 7.1) * (1 - ramp(t, 7.23, 7.38))
            kris_y += 2 * nod
        if 11.45 <= t < 12.2:
            kris_key = 'krisRight'
            kris_x -= 4 * ramp(t, 11.45, 11.8)
        elif 12.2 <= t < 13:
            kris_x -= 4 * (1 - ramp(t, 12.2, 13))
        if 11.75 <= t < 13.25:
            susie_key, susie_frame = 'susieLaughLeft', int((t - 11.75) * 7) % 2
        reaching = ramp(t, 20.95, 21.45) * (1 - ramp(t, 22.05, 22.6))
        kris_x += 18 * reaching
        kris_y -= 19 * reaching
        if 20.95 <= t < 22.6:
            kris_key = 'krisHug' if 21.2 <= t < 22.05 else 'krisRight'
            kris_frame = 1 if kris_key == 'krisHug' else int(t * 8) % 4
        # Kris inches closer to Tenna; Susie steps beside them and backs them away.
        if 30.2 <= t < 33.7:
            creep = ramp(t, 30.2, 31.4) * (1 - ramp(t, 31.85, 32.55))
            pull = ramp(t, 31.85, 32.55) * (1 - ramp(t, 33.15, 33.7))
            kris_y += -8 * creep + 4 * pull
            approach = ramp(t, 31.25, 31.85) * (1 - ramp(t, 33.15, 33.7))
            susie_x -= 23 * approach
            susie_y += 4 * pull
            susie_key, susie_frame = 'susieLeft', int(t * 8) % 4
            kris_key = 'krisRight' if t >= 31.85 else 'krisUp'
            kris_frame = int(t * 8) % 4 if t < 31.4 else 0
        if 44.55 <= t < 46.6:
            realization = ramp(t, 44.55, 45.1)
            kris_y += 8 * realization
            susie_x -= 12 * ramp(t, 44.55, 45.3)
            kris_key, susie_key = 'krisRight', 'susieLeft'
            kris_frame = int(t * 8) % 4 if t < 45.1 else 0
            susie_frame = int(t * 8) % 4 if t < 45.3 else 0
        if t >= 46.6:
            run = ramp(t, 46.6, 50.5)
            kris_x, kris_y = blend(-44, 184, run), blend(40, 34, run)
            susie_x, susie_y = blend(-8, 137, ramp(t, 46.6, 51)), 38
            kris_key, susie_key = 'krisRight', 'susieRight'
            kris_frame, susie_frame = int(t * 12) % 4, int(t * 10) % 4
            if 47.2 <= t < 49.2:
                susie_y -= 52 * sin(pi * (t - 47.2) / 2)
                susie_key, susie_frame = 'susieJump', int((t - 47.2) * 8) % 4
            elif 49.2 <= t < 49.55:
                susie_key, susie_frame = 'susieLand', min(2, int((t - 49.2) * 9))
            if t >= 51.2:
                kris_key, kris_frame = 'krisHug', min(3, int((t - 51.2) * 8))
                susie_frame = 0
                susie_key = 'susieRight' if t < 59.8 else 'susieUp'
                if 54.5 <= t < 56:
                    susie_key, susie_frame = 'susieLaughRight', int((t - 54.5) * 7) % 2
            if t >= 59.8:
                release = ramp(t, 59.8, 60.3)
                kris_x += 13 * release
                kris_key, kris_frame = 'krisUp', int(t * 8) % 4 if t < 60.3 else 0
                if 60.65 <= t < 61.35:
                    kris_key, susie_key = 'krisLeft', 'susieRight'
        if 23.2 <= raw_t < 29.6:
            recoil=ramp(raw_t,23.2,23.55)*(1-ramp(raw_t,24.1,24.7))
            kris_y+=8*recoil
            kris_key='krisRight' if 24.2<=raw_t<25.1 or raw_t>=27.8 else 'krisUp'
            kris_frame=int(raw_t*8)%4 if recoil>.05 else 0
            susie_key='susieLaughLeft' if 24.1<=raw_t<26.5 else 'susieLeft' if raw_t>=27.4 else 'susieUp'
            susie_frame=int(raw_t*7)%2 if 24.1<=raw_t<26.5 else 0
        return [dict(id='kris' , key=kris_key, frame=kris_frame, x=kris_x, y=kris_y, scale=1),
                dict(id='susie', key=susie_key, frame=susie_frame, x=susie_x, y=susie_y,
                     depth=38 if 47.2 <= t < 49.55 else susie_y, scale=1)]

    def state(self, t):
        generation = None
        for change in self.story.GROWTH:
            if t < change['t']:
                break
            generation = change
        crowd = self.crowd.sample(t)
        count = crowd['count']
        cue = next((cue for cue in self.story.DIALOGUE if cue['start'] <= t < cue['end']), None)
        observers = self.observers(t)
        raw_t = t
        t = self.legacy(t)
        kris_x = observers[0]['x']
        actors = []
        for identity, ((x, y), (vx, vy), contact) in enumerate(zip(
                crowd['positions'], crowd['velocities'], crowd['contacts'], strict=True)):
            moving = abs(vx) + abs(vy) > 4
            key, frame = 'ralseiPleased', 0
            if moving:
                key = 'ralseiLeft' if vx < 0 else 'ralseiRight'
                frame = int(t * 9 + identity) % 4
            elif identity % 3 == 0:
                key, frame = 'ralseiIdle', (int(t * 2 + identity) % 2) * 2
            if contact > .7 and identity % 5 == 3:
                key, frame = 'ralseiSurprised', 0
            if 42.5 + (identity % 8) * .035 <= t < 46.6:
                key = 'ralseiIdle' if y < -35 else 'ralseiLeft' if x > kris_x else 'ralseiRight'
                frame = int(t * 9 + identity) % 4 if moving or contact > .35 else 0
            fall = crowd['falls'][identity]
            fall_elapsed = raw_t - fall if fall >= 0 else -1
            if 0 <= fall_elapsed < 3.6:
                key, frame = 'ralseiThrown', 0
            if 2.8 <= fall_elapsed < 3.6:
                key,frame='ralseiIdle',0
            if identity == 0:
                if generation and generation['t'] <= raw_t < generation['t'] + .5:
                    key, frame = 'ralseiMagic', int((raw_t - generation['t']) * 18)
                elif 51.2 <= t < 59.8:
                    key, frame = 'ralseiHug', min(3, int((t - 51.2) * 8))
                elif 59.8 <= t < 60.3:
                    key, frame = 'ralseiHugStop', min(3, int((t - 59.8) * 8))
                elif (cue and cue['speaker'] == 'ralsei') or t >= 60.3:
                    key, frame = 'ralseiPleased', 0
            carrying = identity in (1, 2, 3) and 16.15 <= t < 22.8
            if carrying and not moving:
                key, frame = 'ralseiMagicReady', 3
            actors.append(dict(id=f'ralsei-{identity}', key=key, frame=frame,
                               x=float(x), y=float(y), scale=1, contact=float(contact),
                               rotation=(min(1,fall_elapsed/.45)*35 if 0<=fall_elapsed<2.8 else 0),
                               rise=(.35+.65*ramp(fall_elapsed,2.8,3.6) if 2.8<=fall_elapsed<3.6 else 1)))
            if carrying:
                actors.append(dict(id=f'cake-{identity}', key='cake', frame=0, x=x + 9, y=y - 15,
                                   depth=y + .1, scale=.55))
        actors.extend(observers)
        if t >= 12.5:
            arrival = ramp(t, 12.5, 13.28)
            x = blend(238, 114, arrival) + 115 * ramp(t, 46.6, 51)
            walking = arrival < 1 or 46.6 <= t < 51
            actors.append(dict(id='queen', key='queenWalk' if walking else 'queenIdle',
                               frame=int(t * 9) % 4 if walking else 0, x=x, y=17, scale=1))
        if raw_t >= self.story.TIMES['tenna_enters']:
            arrival = ramp(t, 22.8, 23.6)
            x = blend(-235, -105, arrival) + 145 * ramp(t, 46.6, 51)
            key = 'tennaFreakout' if 29.25 <= t < 31.7 else 'tennaPoint' if (
                23.6 <= t < 26.55 or 47 <= t < 49.4 or 61.6 <= t < 64) else 'tennaIdle'
            actors.append(dict(id='tenna', key=key, frame=int(t * 12), x=x, y=42, scale=.34))
        if 34.3 <= t < 39.85:
            entering = ramp(t, 34.3, 34.9)
            leaving = ramp(t, 39.3, 39.85)
            x = blend(184, 75, entering) + 180 * leaving
            actors.append(dict(id='starwalker', key='starwalkerIdle', frame=0, x=x, y=20,
                               scale=1, flip=False))
        camera_x, zoom = self.camera(raw_t)
        return dict(t=raw_t, count=count, generation=generation, actors=actors, dialogue=cue,
                    camera_x=camera_x, zoom=zoom)

    def backdrop(self, size, state, ground):
        width,height=size
        source=self.rooms['castleFront']
        native=np.asarray(source)
        scale=state['zoom']*.5
        xs=(np.arange(width)-width/2+state['camera_x']*state['zoom'])/scale+500
        ys=(np.arange(height)-ground)/scale+550
        # Native courtyard bricks repeat over an unlimited black floor.
        tile=native[340:540,240:440]
        plate=tile[np.mod(ys.astype(int),200)[:,None],np.mod(xs.astype(int),200)[None,:]].copy()
        detail=ease((state['zoom']-.15)/.20)
        plate=(plate*detail).astype(np.uint8)
        result=Image.fromarray(plate)
        # The castle is behind the furthest foot, never underneath walking clones.
        rear=min(-115,self.crowd.bounds(state['t'])[1]-30)
        castle=source.crop((190,0,850,322))
        castle=castle.resize((max(1,round(castle.width*scale)),max(1,round(castle.height*scale))),NEAR)
        x=width/2+(-155-state['camera_x'])*state['zoom']
        y=ground+rear*state['zoom']-castle.height
        result.paste(castle,(round(x),round(y)))
        return result

    def draw_actor(self, image, actor, state, ground):
        zoom = state['zoom']
        scale = round(actor['scale'] * zoom, 3)
        if state.get('edition') == 'gameplay' and actor['id'].startswith('ralsei-'):
            # Keep a native nearest-neighbour hat/robe sampling footprint.
            scale = max(.16, scale)
        body, anchor = self.body(actor['key'], actor['frame'], scale, actor.get('flip', False))
        if actor.get('rise',1)<1:
            body=body.resize((body.width,max(1,round(body.height*actor['rise']))),NEAR)
            anchor=(body.width//2,body.height)
        if actor.get('rotation'):
            body = body.rotate(actor['rotation'], resample=NEAR, expand=True)
            anchor = (body.width//2, body.height)
        x = round(image.width / 2 + (actor['x'] - state['camera_x']) * zoom)
        y = round(ground + actor['y'] * zoom)
        box = (x - anchor[0], y - anchor[1], x - anchor[0] + body.width, y - anchor[1] + body.height)
        if box[2] < 0 or box[0] > image.width or box[3] < 0 or box[1] > image.height:
            return False
        image.paste(body, (box[0], box[1]), body)
        return True

    def portrait(self, speaker, t, speaking):
        key = {'ralsei': 'ralseiFace', 'susie': 'susieFace', 'queen': 'queenFace',
               'tenna': 'tennaFace', 'starwalker': 'starwalkerFace'}[speaker]
        frame = int(t * 9) % 2 if speaker == 'queen' and speaking else 8 if speaker == 'ralsei' else 0
        source, _ = self.source(key, frame)
        source = source.crop(source.getbbox())
        factor = min(46 / source.width, 53 / source.height)
        return source.resize((max(1, round(source.width * factor)),
                              max(1, round(source.height * factor))), NEAR)

    def dialogue(self, image, cue, t, edition):
        scale = 1.5
        if edition == 'short':
            left, top, width, height, text_width = 10, 440, 318, 112, 225
        else:
            left, top, width, height, text_width = 36, 266, 568, 88, 470
        draw = ImageDraw.Draw(image)
        draw.rectangle((left, top, left + width, top + height), fill='black', outline='white', width=2)
        rows = self.font.wrap(cue['text'], text_width, scale)
        visible = 1 + int((t - cue['start']) * self.story.TEXT_RATE)
        face = self.portrait(cue['speaker'], t, visible < len(cue['text']))
        image.paste(face, (left + 35 - face.width // 2, top + height // 2 - face.height // 2), face)
        y = top + (height - len(rows) * 24) // 2 - 2
        for row in rows:
            self.font.draw(image, row[:max(0, visible)], left + 77, y, scale)
            visible -= len(row) + 1
            y += 24

    def frame(self, t, edition='short'):
        if edition not in ('short', 'gameplay'):
            raise ValueError(f'Unknown edition: {edition}')
        if t >= self.story.TIMES['explosion']:
            return cosmic_frame(self, t, edition)
        state = self.state(t)
        size = (360, 640) if edition == 'short' else (640, 360)
        if edition == 'gameplay':
            state = dict(state, zoom=state['zoom'] * .68, edition='gameplay')
        old_t = self.legacy(t)
        wide_reveal = max(ramp(old_t, 39.6, 40.45) * (1 - ramp(old_t, 41.65, 42.5)), ramp(t, 73, 74))
        ground = blend(348, 395, wide_reveal) if edition == 'short' else blend(175, 228, wide_reveal)
        image = self.backdrop(size, state, ground)
        world = image.copy()
        ordered = sorted(state['actors'], key=lambda actor: (actor.get('depth', actor['y']),
                                                             actor['id'] != 'ralsei-0'))
        for actor in ordered:
            self.draw_actor(world, actor, state, ground)
        image = world
        cue = state['dialogue']
        if cue and cue.get('actor'):
            target = next((a for a in state['actors'] if a['id'] == cue['actor']),None)
            if target:
                px=size[0]/2+(target['x']-state['camera_x'])*state['zoom']
                py=ground+target['y']*state['zoom']-40*state['zoom']
                if 10<px<size[0]-10 and 115<py<420:
                    ImageDraw.Draw(image).polygon([(px-4,py-8),(px+4,py-8),(px,py-2)],fill='white')
        if t < self.story.INTRO['end']:
            left, top, width, height = (10, 132, 340, 100) if edition == 'short' else (130, 34, 380, 92)
            ImageDraw.Draw(image).rectangle((left, top, left + width, top + height),
                                            fill='black', outline='white', width=2)
            visible = max(0, 1 + int((t - self.story.INTRO['start']) * self.story.INTRO['rate']))
            for index, row in enumerate(self.story.INTRO['text'].splitlines()):
                text_x = size[0] / 2 - self.font.width(row, 1.7) / 2
                self.font.draw(image, row[:visible], text_x, top + 18 + index * 30, 1.7)
                visible = max(0, visible - len(row) - 1)
        else:
            label = f"RALSEIS  {state['count']:,}"
            y = 410 if edition == 'short' else 235
            ink = self.small.render(label, 2)
            x = (size[0] - ink.width) // 2
            ImageDraw.Draw(image).rectangle((x - 10, y - 5, x + ink.width + 9, y + 23), fill='black')
            image.paste(ink, (x, y), ink)
            if state['dialogue']:
                self.dialogue(image, state['dialogue'], t, edition)
        return image
