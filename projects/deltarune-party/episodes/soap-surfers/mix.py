"""Shared timeline mixer for original DELTARUNE and Mario Party DS audio."""

import hashlib
import json
from pathlib import Path
import subprocess
import wave

import numpy as np


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets/audio"
RATE = 48000
VOICES = {"gerson": ("gerson-text.wav", .93), "queen": ("queen-text.wav", .95),
          "flowery": ("flowery-text-1.wav", .88), "ralsei": ("ralsei-text.wav", .91)}


class Mixer:
    def __init__(self, duration):
        self.stems = {name: np.zeros((round(duration * RATE), 2), dtype=np.float32)
                      for name in ("music", "sound", "voice")}
        self.decoded = {}
        self.cues = []

    def add(self, stem, time, filename, gain, duration=None, *, offset=0, fade=.016, pitch=1, pan=0):
        if filename not in self.decoded:
            raw = subprocess.check_output([
                "ffmpeg", "-v", "error", "-i", str(ASSETS / filename),
                "-ac", "2", "-ar", str(RATE), "-f", "f32le", "-",
            ])
            self.decoded[filename] = np.frombuffer(raw, "<f4").reshape(-1, 2)

        source = self.decoded[filename]
        start = round(time * RATE)
        source_start = round(offset * RATE)
        length = min(len(self.stems[stem]) - start, int((len(source) - source_start) / pitch))
        if duration is not None:
            length = min(length, round(duration * RATE))
        if length <= 0:
            raise ValueError(f"Empty cue {filename} at {time}")

        if pitch == 1:
            segment = source[source_start:source_start + length].copy()
        else:
            indices = source_start + np.arange(length) * pitch
            source_indices = np.arange(len(source))
            segment = np.column_stack([
                np.interp(indices, source_indices, source[:, channel]) for channel in range(2)
            ]).astype(np.float32)

        fade_samples = min(length // 3, round(fade * RATE))
        if fade_samples:
            ramp = np.linspace(0, 1, fade_samples, dtype=np.float32)[:, None]
            segment[:fade_samples] *= ramp
            segment[-fade_samples:] *= ramp[::-1]
        balance = (1 - max(pan, 0), 1 + min(pan, 0))
        self.stems[stem][start:start + length] += np.asarray(balance, dtype=np.float32) * gain * segment
        self.cues.append({
            "t": round(time, 6), "stem": stem, "source": filename, "gain": gain,
            "source_offset": offset, "duration": length / RATE, "pitch": pitch, "pan": pan,
        })

    def duck(self, start, end, factor):
        music = self.stems["music"]
        first, hold, release, last = [round(time * RATE) for time in
                                      (max(0, start - .08), start, end, end + .14)]
        last = min(len(music), last)
        envelope = np.interp(np.arange(first, last), [first, hold, release, last], [1, factor, factor, 1])
        music[first:last] *= envelope[:, None]

    def write(self, destination, receipt):
        mixed = sum(self.stems.values())
        gain = min(1.32, .88 / float(np.max(np.abs(mixed))))
        mixed *= gain
        destination.parent.mkdir(exist_ok=True)
        with wave.open(str(destination), "wb") as stream:
            stream.setparams((2, 2, RATE, 0, "NONE", "not compressed"))
            stream.writeframes(np.rint(mixed * 32767).astype("<i2").tobytes())

        report = {
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            "sample_rate": RATE, "channels": 2, "samples": len(mixed),
            "duration": len(mixed) / RATE, "master_gain": gain,
            "peak_dbfs": float(20 * np.log10(np.max(np.abs(mixed)))),
            "stems_rms_dbfs": {
                name: float(20 * np.log10(rms)) if (rms := np.sqrt(np.mean(data ** 2))) else None
                for name, data in self.stems.items()
            },
            "sources": {name: hashlib.sha256((ASSETS / name).read_bytes()).hexdigest()
                        for name in sorted(self.decoded)},
            "cues": sorted(self.cues, key=lambda cue: cue["t"]),
        }
        receipt.write_text(json.dumps(report, indent=2) + "\n")
