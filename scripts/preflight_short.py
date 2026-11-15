#!/usr/bin/env python3
"""Pre-render gate for a Shorts production workspace (story.py + visual.py + audio.py).

Usage: python3 scripts/preflight_short.py <workspace> [--allow-box-top]

Reads the workspace's story.py (and visual.py / audio.py / assets manifests without importing them)
and checks the review notes that most often sent a cut back: a requested line missing or out of
order, a reaction before its cause, music inside a requested silence, a missing sound file, and a
dialogue box under the platform caption area. Writes qa/preflight.md and exits 1 on any FAIL.
Run it before every preview and every final render and record its RESULT line with the export.

story.py may define, besides CUES / EVENTS / MUSIC / T / DURATION:
  SPEC  = ["Hello? Who is it?", "Kris?", ...]   # the requested lines, verbatim, in the requested order (required)
  ORDER = [("reveal", "shock"), ...]           # T[a] must come before T[b] (cause before reaction, etc.)
  SILENT = [("poof", "laugh"), ...]            # no MUSIC entry may play between T[a] and T[b]
  PUNCH = {"Hey, Raly!"}                       # cue texts allowed to appear all at once (no pacing check)
"""

import json
import re
import sys
from pathlib import Path

RATE_MAX = 22.0          # glyphs/s; 30 was "too fast"
GAP_MIN = 0.12           # s between lines
BOX_TOP_MIN, BOX_BOTTOM_MAX = 760, 1060   # shorts layout: clear of the Reels/Shorts caption area


def norm(s):
    return re.sub(r"[^a-z0-9\[\]]+", " ", s.lower()).strip()


def load_story(ws):
    # Execute the source directly: a cached .pyc from the same second can hide an edit to story.py.
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ws))
    import types
    mod = types.ModuleType("story")
    mod.__file__ = str(ws / "story.py")
    sys.modules["story"] = mod
    exec(compile((ws / "story.py").read_text(), str(ws / "story.py"), "exec"), mod.__dict__)
    return mod


def sound_keys(ws):
    keys = set()
    for nj in [ws / "assets" / "native.json", *sorted((ws / "assets").glob("*/sounds.json"))]:
        if nj.exists():
            keys |= set((json.loads(nj.read_text()).get("sounds") or {}).keys())
    au = ws / "audio.py"
    if au.exists():
        keys |= set(re.findall(r"""['"]([A-Za-z0-9_]+)['"]\s*:\s*['"](?:assets/|[^'"]+\.(?:wav|ogg|mp3))""", au.read_text()))
    return keys


def box(ws):
    vp = ws / "visual.py"
    if not vp.exists():
        return None
    m = re.search(r"^BOX\s*=\s*\((\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)", vp.read_text(), re.M)
    return tuple(int(x) for x in m.groups()) if m else None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    ws = Path(sys.argv[1]).expanduser().resolve()
    allow_top = "--allow-box-top" in sys.argv
    s = load_story(ws)
    cues = list(getattr(s, "CUES", []))
    T = dict(getattr(s, "T", {}))
    fails, warns, oks = [], [], []

    # 1. the requested lines, verbatim and in order
    spec = getattr(s, "SPEC", None)
    if not spec:
        fails.append("SPEC missing: copy every requested line, verbatim and in order, into story.SPEC")
    else:
        texts = [norm(c["text"]) for c in cues]
        i = 0
        for line in spec:
            want = norm(line)
            j = next((k for k in range(i, len(texts)) if want and want in texts[k]), None)
            if j is None:
                where = next((k for k, t in enumerate(texts) if want in t), None)
                fails.append(f"SPEC line missing or out of order: {line!r}" + (f" (found earlier at cue {where})" if where is not None else ""))
            else:
                i = j + 1
        if not any(f.startswith("SPEC") for f in fails):
            oks.append(f"SPEC: all {len(spec)} lines present in order")

    # 2. cause before reaction and other ordering
    for a, b in getattr(s, "ORDER", []):
        if a not in T or b not in T:
            fails.append(f"ORDER refers to a missing time: {a!r} or {b!r}")
        elif not T[a] < T[b]:
            fails.append(f"ORDER broken: T[{a}]={T[a]:.2f} is not before T[{b}]={T[b]:.2f}")
        else:
            oks.append(f"ORDER {a} < {b} ({T[a]:.2f} < {T[b]:.2f})")

    # 3. silence windows
    for a, b in getattr(s, "SILENT", []):
        if a not in T or b not in T:
            fails.append(f"SILENT refers to a missing time: {a!r} or {b!r}")
            continue
        loud = [m["key"] for m in getattr(s, "MUSIC", []) if m["start"] < T[b] and (m.get("end") or 1e9) > T[a] + 0.06]
        (fails if loud else oks).append(f"SILENT {a}..{b}: " + (f"music still playing {loud}" if loud else "no music"))

    # 4. every sound key exists
    have = sound_keys(ws)
    missing = sorted({e["key"] for e in getattr(s, "EVENTS", [])} - have) if have else []
    if not have:
        warns.append("no assets/native.json or audio.py EXTRA found; sound keys not checked")
    elif missing:
        fails.append(f"sound keys not in native.json / audio.EXTRA: {missing}")
    else:
        oks.append(f"sound keys: {len(getattr(s, 'EVENTS', []))} events, all present")

    # 5. dialogue pacing and overlap
    punch = {norm(x) for x in getattr(s, "PUNCH", set())}
    prev = None
    for k, c in enumerate(cues):
        n = len(c["text"])
        if norm(c["text"]) not in punch and not c.get("cut"):
            if c.get("rate", 0) > RATE_MAX:
                warns.append(f"cue {k} types at {c['rate']}/s (> {RATE_MAX}): {c['text']!r}")
            hold = c["end"] - c["start"] - n / max(c.get("rate", RATE_MAX), 1)
            if hold < 0.85 + 0.025 * n - 0.05:
                warns.append(f"cue {k} holds {hold:.2f}s (< {0.85 + 0.025 * n:.2f}): {c['text']!r}")
        if prev is not None and c["start"] < prev["end"] - 1e-3 and c.get("where") == prev.get("where"):
            fails.append(f"cue {k} starts before cue {k - 1} ends: {c['text']!r}")
        elif prev is not None and c["start"] - prev["end"] < GAP_MIN and not c.get("cut") and norm(c["text"]) not in punch:
            warns.append(f"cue {k} follows with only {c['start'] - prev['end']:.2f}s gap")
        prev = c

    # 6. dialogue box clear of the platform caption area
    b = box(ws)
    if b is None:
        warns.append("BOX not found in visual.py")
    elif b[1] < BOX_TOP_MIN and allow_top:
        oks.append(f"BOX {b} at the top (allowed by --allow-box-top)")
    elif b[1] < BOX_TOP_MIN or b[3] > BOX_BOTTOM_MAX:
        fails.append(f"BOX {b} outside y {BOX_TOP_MIN}-{BOX_BOTTOM_MAX} (Reels caption area / layout rule)")
    else:
        oks.append(f"BOX {b}")

    dur = getattr(s, "DURATION", None)
    if not dur:
        fails.append("DURATION missing")

    lines = [f"# preflight: {getattr(s, 'TITLE', ws.name)} {getattr(s, 'VERSION', '')}", f"duration {dur}", ""]
    lines += ["## cues"] + [f"{c['start']:6.2f}-{c['end']:6.2f}  {c['speaker']:>8}: {c['text']}" for c in cues]
    lines += ["", "## FAIL"] + (fails or ["none"]) + ["", "## WARN"] + (warns or ["none"]) + ["", "## OK"] + oks
    (ws / "qa").mkdir(exist_ok=True)
    (ws / "qa" / "preflight.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nRESULT: {'FAIL' if fails else 'PASS'} ({len(fails)} fail, {len(warns)} warn) -> {ws / 'qa' / 'preflight.md'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
