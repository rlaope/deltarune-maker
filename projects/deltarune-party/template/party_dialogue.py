"""Schedule cast exchanges once for the dialogue box and original voice blips."""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class Speaker:
    portrait: str
    voice: str
    pan: float = 0


@dataclass(frozen=True)
class Reply:
    speaker: str
    text: str
    portrait: str | None = None


class PartyDialogue:
    def __init__(self, speakers, *, text_rate=27):
        if not isfinite(text_rate) or text_rate <= 0:
            raise ValueError('Dialogue text rate must be positive')
        self._speakers = dict(speakers)
        self.text_rate = text_rate
        self.cues = ()

    def exchange(self, event, *replies, delay=.18, until=None):
        """Schedule an action's replies and return when the last box closes.

        Set until to the next protected action or cue. The whole exchange
        must fit, so a reply never gets cut off to make the deadline.
        """
        start = event['t'] + delay
        if not replies or not isfinite(start) or start < 0 or delay < 0:
            raise ValueError('An exchange needs replies and a valid start time')

        cues = []
        for reply in replies:
            text = ' '.join(reply.text.split())
            if not text:
                raise ValueError('A reply needs text')
            speaker = self._speakers[reply.speaker]
            end = round(start + (len(text) - 1) / self.text_rate + .58, 6)
            cues.append(dict(speaker=reply.speaker, text=text, portrait=reply.portrait or speaker.portrait,
                             start=round(start, 6), end=end))
            start = end + .12

        if until is not None and (not isfinite(until) or end > until):
            raise ValueError(f'Exchange ends at {end:.3f}s, past the {until:.3f}s deadline')
        ordered = sorted((*self.cues, *cues), key=lambda cue: cue['start'])
        if any(before['end'] > after['start'] for before, after in zip(ordered, ordered[1:])):
            raise ValueError('Exchange overlaps existing dialogue')
        self.cues = tuple(ordered)
        return end

    def validate_fit(self, font):
        """Check the original font against the Shorts reel's two-row gap."""
        width = 185
        for cue in self.cues:
            try:
                rows = font.wrap(cue['text'], width)
            except KeyError as error:
                raise ValueError(f"{cue['speaker']} dialogue uses unsupported glyph {error.args[0]!r}") from error
            if len(rows) > 2 or any(font.width(row) > width for row in rows):
                raise ValueError(f"{cue['speaker']} dialogue exceeds the two-row Shorts box: {cue['text']!r}")

    def mix(self, mixer):
        """Use the same text clock as the reel and leave gameplay sounds intact."""
        for cue in self.cues:
            speaker = self._speakers[cue['speaker']]
            blips = [cue['start'] + index / self.text_rate for index, char in enumerate(cue['text'])
                     if char.isalnum()]
            for time, next_time in zip(blips, blips[1:] + [cue['end']]):
                duration = min(.085, next_time - time)
                mixer.add('voice', time, speaker.voice, .87, duration, fade=.004, pan=speaker.pan)
            if blips:
                mixer.duck(blips[0], min(blips[-1] + .15, cue['end']), .57)
