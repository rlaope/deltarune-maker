"""Render the original-assets multiplication story from one shared scene clock."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from PIL import Image

import story
from visual import Visual


ROOT = Path(__file__).resolve().parent


def encode(scene, edition, audio, destination, scale):
    size = (360, 640) if edition == 'short' else (640, 360)
    command = [
        'ffmpeg', '-n', '-hide_banner', '-loglevel', 'error', '-f', 'rawvideo',
        '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}', '-r', str(story.FPS), '-i', '-',
        '-i', str(audio), '-vf',
        f'scale={size[0] * scale}:{size[1] * scale}:flags=neighbor:in_range=full:out_range=tv:out_color_matrix=bt709,format=yuv420p',
        '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'veryfast',
        '-threads', '6', '-crf', '8', '-colorspace', 'bt709', '-color_primaries', 'bt709',
        '-color_trc', 'bt709', '-color_range', 'tv',
        '-bsf:v', 'h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0',
        '-c:a', 'aac', '-b:a', '320k', '-ar', '48000', '-ac', '2',
        '-movflags', '+faststart', str(destination),
    ]
    with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
        for index in range(round(story.DURATION * story.FPS)):
            frame = scene.frame(index / story.FPS, edition=edition)
            if frame.mode != 'RGB' or frame.size != size:
                raise ValueError(f'Unexpected {edition} frame at {index}: {frame.mode} {frame.size}')
            encoder.stdin.write(frame.tobytes())
            if index % (story.FPS * 10) == 0:
                print(f'{edition} {index / story.FPS:.0f}/{story.DURATION}s', flush=True)
        encoder.stdin.close()
        if encoder.wait():
            raise RuntimeError(f'{edition} export failed')
    probe = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(destination),
    ]))
    return {
        'path': str(destination), 'bytes': destination.stat().st_size,
        'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(), 'probe': probe,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stills', type=float, nargs='+')
    parser.add_argument('--edition', choices=('short', 'gameplay', 'both'), default='both')
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    story.validate()
    scene = Visual(story)
    qa = ROOT / 'qa'
    qa.mkdir(exist_ok=True)
    editions = ('short', 'gameplay') if args.edition == 'both' else (args.edition,)
    timeline = {
        'title': story.TITLE, 'duration': story.DURATION, 'intro': story.INTRO,
        'doublings': story.DOUBLINGS, 'dialogue': story.DIALOGUE, 'events': story.EVENTS,
    }
    (qa / 'timeline.json').write_text(json.dumps(timeline, indent=2) + '\n')
    if args.stills:
        for edition in editions:
            for time in args.stills:
                if not 0 <= time < story.DURATION:
                    parser.error(f'Still time must be within the episode: {time}')
                frame = scene.frame(time, edition=edition)
                size = (540, 960) if edition == 'short' else (960, 540)
                frame.resize(size, Image.Resampling.NEAREST).save(qa / f'{edition}-{time:06.2f}.png')
        return

    from audio import render_audio

    output = ROOT / 'out' / ('preview' if args.preview else 'final')
    output.mkdir(parents=True, exist_ok=True)
    destinations = {edition: output / f'ralsei-multiplication-{edition}-{story.VERSION}.mp4'
                    for edition in editions}
    if any(path.exists() for path in destinations.values()):
        parser.error('Use a fresh export directory for a new render')
    inputs = ('story.py', 'visual.py', 'crowd.py', 'audio.py', 'render.py',
              'assets/native.json', 'assets/town/town.json', 'assets/extras.json',
              'assets/observers.json')
    inputs += tuple(name for name in (
        'cosmic.py', 'assets/staging-v3.json', 'assets/voices-v3.json',
    ) if (ROOT / name).is_file())
    before = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in inputs}
    audio = output / 'mix.wav'
    render_audio(story, audio, output / 'mix.json',
                 contact_events=scene.crowd.collision_events)
    exports = []
    for edition, path in destinations.items():
        scale = 3 if edition == 'short' else 2
        if not args.preview:
            scale = 6 if edition == 'short' else 3
        exports.append(encode(scene, edition, audio, path, scale))
    after = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in inputs}
    if before != after:
        raise RuntimeError('Render inputs changed during export. Review the changed sources and render again.')
    for export in exports:
        export['input_sha256'] = before
    (output / 'exports.json').write_text(json.dumps(exports, indent=2) + '\n')


if __name__ == '__main__':
    main()
