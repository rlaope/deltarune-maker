"""Mix original DELTARUNE music, writer voices, and action cues on the story clock."""

import hashlib
import json
import random
from pathlib import Path
import subprocess
import wave

import numpy as np


ROOT = Path(__file__).resolve().parent
RATE = 48000
VOICE_SETTINGS = {
    'ralsei': ('ralseiVoice', 1, .59, 0),
    'susie': ('susieVoice', 2, .69, .12),
    'queen': ('queenVoice', 2, .72, .20),
    'tenna': ('tennaVoice', 3, .70, -.18),
    'starwalker': ('starwalkerVoice', 1, .95, .14),
}


def sources():
    native = json.loads((ROOT / 'assets/native.json').read_text())
    extras = json.loads((ROOT / 'assets/extras.json').read_text())
    voices = json.loads((ROOT / 'assets/voices-v3.json').read_text())
    return {**native['audio'], **extras['audio'], **voices['audio']}


def build_cues(story, *, available=None, contact_events=()):
    """Use the same character indices as the renderer's typewriter."""
    available = sources() if available is None else available
    cues = []
    rng = random.Random(31039)
    intro = story.INTRO
    for index, char in enumerate(intro['text']):
        time = intro['start'] + index / intro['rate']
        if char.isalnum() and time < intro['end']:
            cues.append(dict(t=time, key='narratorVoice', gain=.95, pitch=1,
                             speaker='narrator', char=char, pan=0))
    tenna_keys = ['tennaVoice'] + [
        f'tennaVoice{number}' for number in range(2, 10)
        if f'tennaVoice{number}' in available
    ]
    for line in story.DIALOGUE:
        who = line['speaker']
        key, spacing, gain, pan = VOICE_SETTINGS[who]
        last = -spacing
        for index, char in enumerate(line['text']):
            time = line['start'] + index / story.TEXT_RATE
            silent = char in ' &\n^!.?,:/\\|*' if who in ('queen', 'tenna') else not char.isalnum()
            if silent or index - last < spacing or time >= line['end']:
                continue
            last = index
            pitch = 1
            if who == 'queen':
                pitch = round(.90 + rng.random() * .15, 4)
            elif who == 'tenna':
                key = rng.choice(tenna_keys)
                pitch = round(.86 + rng.random() * .35, 4)
            cues.append(dict(t=time, key=key, gain=gain, pitch=pitch, speaker=who,
                             char=char, glyph_index=index, line_start=line['start'], writer_timer=spacing, pan=pan, stopPrevious=who in ('queen', 'tenna'),
                             voiceEnd=line['end']))
            if who == 'ralsei' and line.get('chorus'):
                for delay, side in ((.07, -.24), (.13, .24)):
                    cues.append(dict(t=time + delay, key=key, gain=.22, pitch=1,
                                     speaker=who, char=char, pan=side,
                                     voiceEnd=line['end'], chorus=True))
    for index, change in enumerate(story.DOUBLINGS):
        cues.extend((
            dict(t=change['t'], key='grow', gain=.38 + min(index, 4) * .025,
                 pitch=1.14 - min(index, 8) * .035, event='doubling', pan=0),
            dict(t=change['t'] + .06, key='magic', gain=.20, pitch=1,
                 event='split_sparkle', pan=0),
        ))
    event_cues = {
        'clone_bump': ('bump', .48, 1),
        'clone_fall': ('fall', .42, 1),
        'clone_recover': ('land', .24, 1),
        'crowd_pressure': ('push', .32, 1),
        'crowd_explosion': ('explosion', .70, 1),
        'space_dolls': ('magic', .28, 1),
        'black_hole': ('ominous', .42, 1),
        'last_doll_absorbed': ('absorb', .42, 1),
        'starwalker_final': ('land', .18, 1),
        'queen_enters': ('land', .18, 1.1),
        'cake_appears': ('magic', .22, 1.2),
        'susie_pulls_kris_back': ('push', .25, 1),
        'kris_realizes': ('jump', .25, 1),
        'susie_jumps_aside': ('jump', .24, 1),
        'susie_lands': ('land', .20, 1.1),
        'susie_laugh': ('susieLaugh', .55, 1),
        'starwalker_enters': ('land', .18, 1.2),
        'kris_runs': ('jump', .34, 1),
        'kris_stops': ('land', .28, 1),
        'hug': ('magic', .36, 1),
    }
    for event in getattr(story, 'EVENTS', ()):
        kind = event['type']
        if kind in event_cues:
            key, gain, pitch = event_cues[kind]
            cue = dict(t=event['t'], key=key, gain=gain, pitch=pitch, event=kind, pan=0)
            if 'speaker' in event:
                cue['speaker'] = event['speaker']
            cues.append(cue)
        elif kind == 'tenna_enters' and 'tennaCheer' in available:
            cues.append(dict(t=event['t'], key='tennaCheer', gain=.18, pitch=1,
                             event=kind, pan=0))
    cues.append(dict(t=story.TIMES['fall'] + .9, key='susieLaugh', gain=.45,
                     pitch=1, speaker='susie', event='susie_laugh_at_fall', pan=.12))
    # Only explicit visible falls qualify: ordinary microcontacts stay silent.
    accepted = [event['t'] for event in getattr(story, 'EVENTS', ())
                if event['type'] == 'clone_fall']
    for contact in sorted(contact_events, key=lambda item: item['fall_time']):
        if contact.get('visible', True) is False:
            continue
        fall = float(contact['fall_time'])
        if any(abs(fall - previous) < .25 for previous in accepted):
            continue
        if not 0 <= fall < story.DURATION:
            continue
        accepted.append(fall)
        focus = 171 if fall >= story.TIMES['stop'] else 0
        pan = max(-.35, min(.35, float(contact.get('pan', (contact.get('x', focus) - focus) / 350))))
        for time, key, gain, kind in (
            (fall, 'bump', .22, 'contact_bump'),
            (fall + .035, 'fall', .25, 'contact_fall'),
            (float(contact['recovery_time']), 'land', .13, 'contact_recovery'),
        ):
            if time < story.DURATION:
                cues.append(dict(t=time, key=key, gain=gain, pitch=1, pan=pan,
                                 event=kind, actor=contact['id'],
                                 contact_event=dict(contact)))
    return sorted(cues, key=lambda cue: cue['t'])


def render_audio(story, destination, receipt, *, contact_events=()):
    """Write a measured 48 kHz stereo master and source-bound cue receipt."""
    destination, receipt = Path(destination), Path(receipt)
    available = sources()
    contact_events = tuple(contact_events)
    cue_list = build_cues(story, available=available, contact_events=contact_events)
    missing = sorted({cue['key'] for cue in cue_list} - available.keys())
    if missing:
        raise ValueError(f'Missing original audio sources: {", ".join(missing)}')
    sample_count = round(story.DURATION * RATE)
    stems = {name: np.zeros((sample_count, 2), dtype=np.float32)
             for name in ('music', 'effects', 'voice')}
    decoded = {}
    used = {}

    def load(key, pitch=1):
        cache_key = (key, pitch)
        if cache_key not in decoded:
            source = available[key]
            path = ROOT / source['path']
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != source['sha256']:
                raise ValueError(f'Audio source hash mismatch: {key}')
            filters = f'aresample={RATE},asetrate={round(RATE * pitch)},aresample={RATE}'
            raw = subprocess.check_output([
                'ffmpeg', '-v', 'error', '-i', str(path), '-af', filters,
                '-ac', '2', '-f', 'f32le', '-',
            ])
            decoded[cache_key] = np.frombuffer(raw, '<f4').reshape(-1, 2).copy()
            used[key] = {'path': source['path'], 'sha256': digest}
            for field in ('source', 'url', 'sourceName', 'derivation', 'usage', 'nativeWriterSample'):
                if field in source:
                    used[key][field] = source[field]
        return decoded[cache_key]

    upcoming = {}
    rendered_cues = []
    for cue in reversed(cue_list):
        key = cue['key']
        source = load(key, cue['pitch'])
        start = round(cue['t'] * RATE)
        end = min(start + len(source), sample_count)
        if cue.get('stopPrevious'):
            # All selected variants use one character channel for successive blips.
            channel = cue['speaker']
            end = min(end, upcoming.get(channel, sample_count))
            upcoming[channel] = start
        if 'voiceEnd' in cue:
            end = min(end, round(cue['voiceEnd'] * RATE))
        if not 0 <= start < end <= sample_count:
            raise ValueError(f'Empty or out-of-range cue: {key} at {cue["t"]}')
        segment = source[:end - start].copy()
        fade = min(0 if cue.get('stopPrevious') else 144, len(segment))
        if fade:
            segment[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)[:, None]
        voice = 'speaker' in cue
        trim = 1.10 if key in ('narratorVoice', 'starwalkerVoice') else .62 if voice else 1
        gain = cue['gain'] * trim
        pan = cue['pan']
        balance = np.array((1 - max(pan, 0), 1 + min(pan, 0)), dtype=np.float32)
        stems['voice' if voice else 'effects'][start:end] += segment * gain * balance
        rendered_cues.append({
            **cue, 'source': available[key]['path'], 'source_sha256': available[key]['sha256'],
            'source_offset': 0, 'start_sample': start, 'end_sample': end, 'mix_gain': gain,
        })

    music_start = story.INTRO['end'] - .12
    music_windows = [(music_start, story.DURATION, 'music', 0, .44)]
    if 'tennaMusic' in available:
        tenna_start = story.TIMES['tenna_enters']
        tenna_end = story.TIMES['starwalker_enters']
        music_windows = [
            (music_start, tenna_start + .25, 'music', 0, .44),
            (tenna_start, tenna_end + .25, 'tennaMusic', 0, .30),
            (tenna_end, story.DURATION, 'music', tenna_end - music_start, .44),
        ]
    music_receipt = []
    for start_time, end_time, key, offset, gain in music_windows:
        start, end = round(start_time * RATE), round(end_time * RATE)
        source_start = round(offset * RATE)
        source = load(key)
        length = end - start
        if source_start + length > len(source):
            source = np.tile(source, (int(np.ceil((source_start + length) / len(source))), 1))
        segment = source[source_start:source_start + length].copy()
        fade = min(round(.30 * RATE), length // 2)
        ramp = np.linspace(0, 1, fade, dtype=np.float32)[:, None]
        segment[:fade] *= ramp
        segment[-fade:] *= ramp[::-1]
        stems['music'][start:end] += segment * gain
        music_receipt.append(dict(key=key, start=start_time, end=end_time, offset=offset,
                                  gain=gain, source=used[key]))
    clock = np.arange(sample_count) / RATE
    envelope = np.ones(sample_count, dtype=np.float32)
    for line in story.DIALOGUE:
        start = line['start']
        end = min(line['end'], start + len(line['text']) / story.TEXT_RATE + .15)
        attack = np.clip((clock - start + .08) / .08, 0, 1)
        release = np.clip((end + .20 - clock) / .20, 0, 1)
        envelope = np.minimum(envelope, 1 - .34 * attack * release)
    # Native explosion breaks the music; space payoff leaves room for original effects.
    envelope *= 1 - .88 * np.clip((clock - story.TIMES['explosion']) / .25, 0, 1)
    envelope *= np.clip((story.DURATION - clock) / .65, 0, 1)
    stems['music'] *= envelope[:, None]
    premix = sum(stems.values())
    maximum = max(float(np.max(np.abs(data))) for data in (*stems.values(), premix))
    scale = min(1, .88 / maximum)
    destination.parent.mkdir(parents=True, exist_ok=True)
    receipt.parent.mkdir(parents=True, exist_ok=True)

    def write_wav(path, data):
        if not np.isfinite(data).all() or np.max(np.abs(data)) >= .902:
            raise ValueError(f'Non-finite or excessive PCM peak: {path}')
        with wave.open(str(path), 'wb') as stream:
            stream.setparams((2, 2, RATE, 0, 'NONE', 'not compressed'))
            stream.writeframes(np.rint(data * 32767).astype('<i2').tobytes())

    premix_path = destination.with_name(destination.stem + '-premix.wav')
    write_wav(premix_path, premix * scale)
    for name, data in stems.items():
        write_wav(destination.with_name(destination.stem + f'-{name}.wav'), data * scale)
    filters = 'loudnorm=I=-16:TP=-2:LRA=9'
    first = subprocess.run([
        'ffmpeg', '-nostdin', '-hide_banner', '-i', str(premix_path), '-af',
        filters + ':print_format=json', '-f', 'null', '-',
    ], capture_output=True, text=True, check=True).stderr
    measured = json.loads(first[first.rfind('{'):first.rfind('}') + 1])
    second_filter = (
        f'{filters}:measured_I={measured["input_i"]}:measured_TP={measured["input_tp"]}'
        f':measured_LRA={measured["input_lra"]}:measured_thresh={measured["input_thresh"]}'
        f':offset={measured["target_offset"]}:linear=true:print_format=json'
    )
    normalized = subprocess.run([
        'ffmpeg', '-n', '-nostdin', '-hide_banner', '-i', str(premix_path),
        '-af', second_filter, '-ar', str(RATE), '-c:a', 'pcm_s16le', str(destination),
    ], capture_output=True, text=True, check=True).stderr
    normalization = json.loads(normalized[normalized.rfind('{'):normalized.rfind('}') + 1])
    with wave.open(str(destination), 'rb') as stream:
        final = np.frombuffer(stream.readframes(stream.getnframes()), '<i2').reshape(-1, 2) / 32768
    if len(final) != sample_count or not np.isfinite(final).all() or np.max(np.abs(final)) >= .902:
        raise ValueError('Normalized audio has unexpected length or peak')
    report = {
        'story': {'title': story.TITLE, 'duration': story.DURATION, 'intro': story.INTRO,
                  'doublings': story.DOUBLINGS, 'dialogue': story.DIALOGUE,
                  'events': getattr(story, 'EVENTS', ())},
        'contact_events': contact_events,
        'mixer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'sample_rate': RATE, 'channels': 2, 'samples': sample_count,
        'duration': sample_count / RATE, 'sources': used,
        'music': music_receipt, 'cues': list(reversed(rendered_cues)),
        'premix_scale': scale, 'normalization': normalization,
        'peak_dbfs': float(20 * np.log10(np.max(np.abs(final)))),
        'rms_dbfs': float(20 * np.log10(np.sqrt(np.mean(final ** 2)))),
        'stems_rms_dbfs': {name: float(20 * np.log10(np.sqrt(np.mean(data ** 2))))
                           for name, data in stems.items()},
        'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
        'subjective_listening': 'not_observed',
    }
    receipt.write_text(json.dumps(report, indent=2) + '\n')
    return destination
