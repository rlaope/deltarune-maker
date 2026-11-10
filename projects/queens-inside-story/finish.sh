#!/bin/sh
set -eu
cd "$(dirname "$0")"
ffmpeg -hide_banner -loglevel error -y -i out/mix.wav \
  -af 'loudnorm=I=-16:TP=-2.0:LRA=9' \
  -ar 48000 -c:a aac -b:a 256k out/master-audio.m4a
ffmpeg -hide_banner -loglevel error -y -i out/short-picture.mp4 -i out/master-audio.m4a \
  -map 0:v -map 1:a -c copy -movflags +faststart "${1:-out/short.mp4}"
