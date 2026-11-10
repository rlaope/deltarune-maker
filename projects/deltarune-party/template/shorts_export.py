"""Encode the shared dual-screen Shorts composition without smoothing its pixels."""

import subprocess

from party_reel import ShortsReel


def start_encoder(destination, audio, *, fps=60, scale=8):
    width, height = ShortsReel.size
    output_size = f'{width * scale}:{height * scale}'
    command = [
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-n', '-f', 'rawvideo',
        '-pix_fmt', 'rgb24', '-s', f'{width}x{height}', '-r', str(fps), '-i', '-',
        '-i', str(audio), '-vf',
        f'scale={output_size}:flags=neighbor:in_range=full:out_range=tv:out_color_matrix=bt709,format=yuv420p',
        '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'veryfast', '-threads', '6',
        '-crf', '8', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
        '-color_range', 'tv',
        '-bsf:v', 'h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0',
        '-c:a', 'aac', '-b:a', '320k', '-movflags', '+faststart', str(destination),
    ]
    return subprocess.Popen(command, stdin=subprocess.PIPE)
