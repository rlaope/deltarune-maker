"""Build the film mix from the same events consumed by the browser build."""
import json
import math
import os
from pathlib import Path
import subprocess
import wave

import numpy as np

RATE = 48000
HERE = Path(__file__).resolve().parent
ASSETS = Path(os.environ.get('QUEEN_ASSET_DIR', HERE / 'assets')).expanduser().resolve()
PLAN = json.loads((HERE / 'out/events.json').read_text())
DURATION = PLAN['duration']
N = int(DURATION * RATE)
CACHE = {}


def decode(path):
    if path not in CACHE:
        data = subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(ASSETS / path),
                                        '-vn', '-f', 'f32le', '-ar', str(RATE), '-ac', '2', '-'])
        CACHE[path] = np.frombuffer(data, dtype='<f4').reshape(-1, 2)
    return CACHE[path]


def envelope(size, fade_in, fade_out):
    a = np.ones((size, 1), dtype=np.float32)
    i = min(size, round(fade_in * RATE))
    o = min(size, round(fade_out * RATE))
    if i:
        a[:i, 0] *= np.linspace(0, 1, i)
    if o:
        a[-o:, 0] *= np.linspace(1, 0, o)
    return a


def resample_pitch(source, playback_rate):
    if playback_rate == 1 or not len(source):
        return source
    positions = np.arange(math.ceil(len(source) / playback_rate)) * playback_rate
    earlier = positions.astype(np.int64)
    later = np.minimum(earlier + 1, len(source) - 1)
    blend = (positions - earlier).astype(np.float32)[:, None]
    return source[earlier] * (1 - blend) + source[later] * blend


def add(out, path, t, gain, pan=0, limit=None, ramp=(.002, .02), start=0, playback_rate=1):
    i = round(t * RATE)
    if i >= len(out):
        return
    source = decode(path)[round(start * RATE):]
    source = resample_pitch(source, playback_rate)
    n = min(len(source), len(out) - i, round(limit * RATE) if limit is not None else len(source))
    if n <= 0:
        return
    left, right = math.sqrt(1 - pan), math.sqrt(1 + pan)
    out[i:i + n] += source[:n] * gain * np.array([left, right], dtype=np.float32) * envelope(n, *ramp)


def main():
    out = np.zeros((N, 2), dtype=np.float32)
    bgm = np.zeros_like(out)
    effects = np.zeros_like(out)
    times = PLAN['times']
    sections = [
        (0, times['transition'] + .34, (.10, .67)),
        (times['battle'] - .025, times['win'] + .08, (.012, .37)),
        (times['bossBurst'] + .15, DURATION, (.09, .40)),
    ]
    for q, (start, end, ramp) in zip(PLAN['music'], sections, strict=True):
        add(bgm, q['path'], start, q['gain'], limit=end-start, ramp=ramp)
    duck = np.ones(N, dtype=np.float32)
    for cue in PLAN['cues']:
        limit = cue.get('limit')
        path = cue['path']
        queen_voice = path == 'dr/queen-text.wav'
        playback_rate = cue.get('playbackRate', 1)
        if path.endswith('-text.wav'):
            center = round(cue['t'] * RATE)
            start = max(0, center - round(.025 * RATE))
            natural_tail = len(decode(path)) / (RATE * playback_rate) if queen_voice else .085
            end = min(N, center + round(((limit or natural_tail) + .105) * RATE))
            depth = .49 if queen_voice else .22
            curve = 1 - depth * envelope(end-start, .025, .105)[:, 0]
            np.minimum(duck[start:end], curve, out=duck[start:end])
        add(effects, path, cue['t'], cue['gain'], cue.get('pan', 0), limit,
            ramp=(0, 0) if queen_voice else (.002, .02), start=cue.get('start', 0),
            playback_rate=playback_rate)
    bgm *= duck[:, None]
    out[:] = bgm + effects
    raw_peak = float(np.abs(out).max())
    factor = min(.86 / max(raw_peak, 1e-10), 1.6)
    out *= factor
    with wave.open(str(HERE / 'out/mix.wav'), 'wb') as w:
        w.setnchannels(2)
        w.setframerate(RATE)
        w.setsampwidth(2)
        w.writeframes((out * 32767).astype('<i2').tobytes())
    print(json.dumps({
        'duration_s': DURATION, 'sample_rate': RATE, 'channels': 2,
        'cues': len(PLAN['cues']), 'peak_dbfs': 20*math.log10(float(np.abs(out).max())),
        'rms_dbfs': 20*math.log10(float(np.sqrt(np.mean(out ** 2)))),
        'music_sections': sections, 'post_gain': factor,
    }, indent=2))


if __name__ == '__main__':
    main()
