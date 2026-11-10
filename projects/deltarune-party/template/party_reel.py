"""Shared DS minigame selection, rules, and vertical framing."""

from PIL import Image, ImageDraw

from mpds_ui import checkered, ds_text, resized, stamp
from party_board import PLAYER_COLORS
from reel_art import NEAR, SIZE, Text, centered, paste, smooth, stylus


class PartyReel:
    size = (270, 480)

    def __init__(self, sprite, text_rate):
        self.sprite = sprite
        self.text_rate = text_rate
        self.font = Text()
        self.background = Image.new('RGB', self.size, '#0e0a11')
        draw = ImageDraw.Draw(self.background)
        for y in (38, 257):
            draw.rectangle((13, y - 2, 256, y + 181), outline='#57424b')

    def roulette(self, lower, title, elapsed, lock_at, *, selected_row=0):
        """Slide in the native four-player draw and reveal the selected title."""
        y = 90 - 166 * (1 - smooth(elapsed / .34))
        centered(lower, resized('roulette-frame', *SIZE), 120, y)
        centered(lower, stamp('four-player'), 120, y - 59)
        centered(lower, resized('roulette-players', 112, 27), 120, y + 61)
        if elapsed < .30:
            return lower
        locked = elapsed >= lock_at
        if locked:
            active_row = selected_row
        else:
            turns = 10
            spin = (elapsed - .30) / (lock_at - .30)
            advances = int(turns * (1 - (1 - spin) ** 1.35))
            active_row = (selected_row + advances - turns) % 4
        centered(lower, resized('roulette-slots', 172, 72), 120, y)
        for index in range(4):
            row = y - 26 + 17 * index
            active = index == active_row
            if active:
                centered(lower, resized('roulette-selected', 168, 16), 120, row)
            reveal = locked and active
            label = title if reveal else '? ' * 12
            ds_text(lower, label, 120, row - (9 if reveal else 6), height=12 if reveal else 8,
                    color='#31220a' if active else '#e3cf97', middle=True)
        return lower

    def rules(self, preview, title, rules, players, time_until_start):
        lower = rules.resize(SIZE, NEAR).convert('RGB')
        if 0 <= time_until_start < .34:
            u = smooth((.34 - time_until_start) / .34)
            stylus(lower, 207 + 29 * (1 - u), 168 + 18 * (1 - u), press=u)
        upper = checkered(('#fffde5', '#f1eaa5'))
        paste(upper, resized('instruction-strip', 240, 24), 0, 0)
        centered(upper, title, 120, 12)
        centered(upper, preview.resize((160, 120), NEAR).convert('RGBA'), 120, 101)
        centered(upper, resized('preview-border', 160, 130), 120, 101)
        centered(upper, resized('four-player', 52, 16), 30, 38)
        for i, who in enumerate(players):
            y = 46 + 34 * i
            centered(upper, resized(f'board-panel-{PLAYER_COLORS[i]}', 28, 31), 215, y)
            centered(upper, self.sprite(f'{who}-face', 20), 215, y)
        return lower, upper

    def compose(self, lower, upper, t, cuts=(), dialogue=()):
        fade = min((smooth(abs(t - cut) / .17) for cut in cuts), default=1)
        if fade < 1:
            blank = Image.new('RGB', SIZE, '#170d17')
            lower = Image.blend(blank, lower, fade)
            upper = Image.blend(blank, upper, fade)
        image = self.background.copy()
        image.paste(upper, (15, 38))
        image.paste(lower, (15, 257))
        for cue in dialogue:
            if cue['start'] <= t < cue['end']:
                self._dialogue(image, cue, t)
        return image

    def _dialogue(self, image, cue, t):
        rows = self.font.wrap(cue['text'], 188)
        height = max(26, 9 + 13 * len(rows))
        y = 221 + (34 - height) // 2
        ImageDraw.Draw(image).rectangle((19, y, 251, y + height), fill='#100b16', outline='#e8dce2')
        face = cue.get('portrait', f"{cue['speaker']}-face")
        centered(image, self.sprite(face, 21), 38, y + height / 2)
        visible = 1 + int((t - cue['start']) * self.text_rate)
        for i, row in enumerate(rows):
            self.font.draw(image, row[:max(0, visible)], 57, y + 5 + i * 13)
            visible -= len(row) + 1


class ShortsReel(PartyReel):
    """Frame the original Shorts grid with an empty upper margin."""

    upper_position = (15, 38)
    lower_position = (15, 254)

    def __init__(self, sprite, text_rate):
        super().__init__(sprite, text_rate)
        self.background = Image.new('RGB', self.size, '#0e0b16')
        frame = ImageDraw.Draw(self.background)
        for x, y in (self.upper_position, self.lower_position):
            frame.rectangle((x - 1, y - 1, x + SIZE[0], y + SIZE[1]), outline='#3a3554')

    def compose(self, lower, upper, t, cuts=(), dialogue=()):
        fade = min((smooth(abs(t - cut) / .18) for cut in cuts), default=1)
        if fade < 1:
            blank = Image.new('RGB', SIZE, '#110d19')
            lower = Image.blend(blank, lower, fade)
            upper = Image.blend(blank, upper, fade)
        image = self.background.copy()
        image.paste(upper, self.upper_position)
        image.paste(lower, self.lower_position)
        for cue in dialogue:
            if cue['start'] <= t < cue['end']:
                self._dialogue(image, cue, t)
        return image

    def _dialogue(self, image, cue, t):
        rows = self.font.wrap(cue['text'], 185)
        height = max(29, 10 + 12 * len(rows))
        x, y = self.upper_position
        left, top = x + 3, y + SIZE[1] + (36 - height) // 2
        ImageDraw.Draw(image).rectangle((left, top, left + 233, top + height),
                                        fill='black', outline='#f9f8f9', width=2)
        face = cue.get('portrait', f"{cue['speaker']}-face")
        centered(image, self.sprite(face, 23), left + 19, top + height / 2)
        visible = 1 + int((t - cue['start']) * self.text_rate)
        for i, row in enumerate(rows):
            self.font.draw(image, row[:max(0, visible)], left + 38, top + 6 + i * 12)
            visible -= len(row) + 1
