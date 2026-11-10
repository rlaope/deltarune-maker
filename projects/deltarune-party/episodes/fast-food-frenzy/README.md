# Flowery’s Diner Went Full Mario Party DS

Lancer orders the whole menu at the Second Diner in DELTARUNE Chapter 5. Lancer, Susie, Noelle, and Flowery each take a board turn from a separate starting space. Noelle lands on the green question mark, chooses the middle of three covered menus, and wins eight coins. After the fourth turn settles, the board assigns Noelle to the blue team and draws Fast Food Frenzy.

Flowery runs the conveyor alone against Susie, Lancer, and Noelle. Five Jarona rushes bring the original voice clips and blue punch silhouettes into the kitchen. Susie goes out to a burger, Lancer gets caught by the pancakes, and Noelle survives to win for all three. Lancer asks for his order to go.

## Render the episode

From the repository root, use Python with Pillow and NumPy, and put FFmpeg and FFprobe on `PATH`. The production workspace used Python 3.14.7, Pillow 13.0.0, NumPy 2.5.3, and FFmpeg 9.0.2. Set `workspace` to a prepared private directory outside this checkout.

```sh
workspace="../fast-food-workspace"

python3 projects/deltarune-party/render.py fast-food-frenzy --workspace "$workspace" -- --stills 8.9 27.5 37.9 52.68 82.72
python3 projects/deltarune-party/render.py fast-food-frenzy --workspace "$workspace"
```

Stills and the event timeline go under `qa/`. The full render mixes audio to `out/mix.wav` and writes `out/final/fast-food-frenzy-short-v7.mp4`. Pass `-- --preview` to write the smaller test encode under `out/preview/`.

The renderer uses the checked-in [board replay](fast-board-replay.json). With Node.js, regenerate the same round using the current [board engine](../../game/README.md). Pass a separate output path to inspect the regenerated replay while keeping the approved input file. Omitting the output path rewrites the replay next to its generator.

```sh
node projects/deltarune-party/episodes/fast-food-frenzy/fast_board_replay.mjs "$workspace/replay-check.json"
```

## Private inputs and source credits

| Workspace input | Original game assets and source records |
| --- | --- |
| `assets/boards/chapter-5/second-diner.png` | Toby Fox and team’s DELTARUNE Chapter 5 room art. The unchanged 640 × 480 capture and its hash are recorded in `assets/boards/chapter-assets.json`. [Original room capture](https://deltarune.wiki/w/File:Garden_location_Ideal_Diner.png) |
| `assets/cast/` and `assets/deltarune/` | DELTARUNE cast sprites, portraits, voice blips, dialogue font, and the fall effect. Four Jarona clips use `snd_flowery_voiceclip_jarona1` through `snd_flowery_voiceclip_jarona4`. The rush reuses `spr_flowery_puuunch_left` and its original mask with the fog and afterimage colors from the Chapter 5 draw code. See the private cast provenance, `jarona-sources.json`, and `jarona-aura/sources.json`. [DELTARUNE](https://deltarune.com/) · [Chapter 5 attack source snapshot](https://github.com/Kris1225-hash/deltarune-chapt5-decomp/blob/8cd29bcd24697f73c9c6f25e66526a9c41df1018/objects/obj_orangeheart_floweryjarona/Step_0.gml) |
| `assets/mpds/` and `assets/audio/` | Nintendo and Hudson Soft’s Mario Party DS board HUD, dice, fonts, roulette sheets, and game cues. The private UI and audio manifests record source sheets, cartridge captures, and edits. [Nintendo’s English manual](https://www.nintendo.com/eu/media/downloads/games_8/emanuals/nintendo_ds_21/Manual_NintendoDS_MarioPartyDS_EN.pdf) |
| `assets/fast-food-native/` | Mario Party DS USA Rev 2 cartridge captures in DeSmuME. Includes the motion plates, picker and on-belt food sprites, rules, timer, result screen, *Another Crazy Match*, and minigame effects. The private `PROVENANCE.md` records the cartridge hash, native layer filtering, and sound wave IDs. [Nintendo’s Fast Food Frenzy reference](https://www.nintendo.co.jp/ds/a8tj/minigame/index21.html) |

The asset bundles and capture records stay in the private workspace under the [studio asset policy](../../../../AGENTS.md). The [studio workflow](../../../../docs/workflow.md) uses GitHub Releases for approved videos when they are published.

## Approved v7 export

[Export metadata](export.json) records the verified local vertical MP4. It has 5,107 frames at 2160 × 3840 and 60 fps, with a duration of 85.116667 seconds. Its AAC-LC audio is 48 kHz stereo.

The delivered file matched the recorded SHA-256 and played to the end muted with 5,107 decoded frames and zero drops or errors. FFmpeg decoded both streams and measured a peak of −1.4 dBFS. Audio was assessed technically through the stream decode, cue receipts, and waveform comparisons. The private evidence is in `qa/delivery.json` and `qa/independent/v7/`.

```sh
video="$workspace/out/final/fast-food-frenzy-short-v7.mp4"
shasum -a 256 "$video"
ffprobe -v error -show_streams -show_format -of json "$video"
ffmpeg -v error -xerror -i "$video" -map 0:v:0 -map 0:a:0 -f null -
```
