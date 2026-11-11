# What If Ralsei Kept Multiplying?

A 118-second rendered DELTARUNE fan film: Ralsei doubles into a jostling crowd, Kris and Susie react, and the town gives way to a native explosion, tumbling training dummies, a black hole, and the Original Starwalker. This is a deterministic film renderer, not a playable game or editor.

## Run with private assets

Use Python 3.12+, NumPy, Pillow, FFmpeg and FFprobe. Install Python dependencies with `python3 -m pip install -r projects/ralsei-multiplication/requirements.txt`. The pinned NumPy dependency requires Python 3.12 or later. The production environment used Python 3.14.7, NumPy 2.5.3, Pillow 13.0.0 and FFmpeg 9.0.2.

Run from the repository root. An existing prepared production workspace must contain the original runtime `assets/` tree:

```sh
# Render selected stills using an existing private workspace.
python3 projects/ralsei-multiplication/render.py \
  --workspace /path/to/private-ralsei-workspace -- --stills 23.3 43 91 104 114.5

# Prepare a separate output workspace by linking an existing private asset tree.
python3 projects/ralsei-multiplication/render.py \
  --workspace /path/to/new-private-render \
  --prepare-from /path/to/private-ralsei-workspace -- --stills 23.3 91

# Render both editions into the fresh workspace; existing MP4s are not overwritten.
python3 projects/ralsei-multiplication/render.py \
  --workspace /path/to/new-private-render -- --edition both

# Asset-independent checks for population identity, births and physical contact.
python3 projects/ralsei-multiplication/check.py \
  --output /path/to/new-private-render/qa/crowd-checks.json
```

Pass production options after `--`: `--edition short`, `--edition gameplay`, `--edition both`, `--stills <seconds...>`, or `--preview`. Stills go to `qa/`; final video, mix and measurements go to `out/final/`. Preview encoding goes to `out/preview/`. The launcher reads production code from this checkout and rebinds asset/output roots in memory. For full exports it links missing source files into the private workspace so the production renderer can hash its inputs; differing existing source files are rejected. Preparation creates an asset symlink, never copies or redistributes the asset bundle. Keep that link's source available.

The required private runtime manifests are:

| Manifest | Runtime content it indexes |
| --- | --- |
| `assets/native.json` | Original cast sprites, portraits, fonts, music and effects |
| `assets/extras.json` | Queen/Tenna/Starwalker staging, cake and additional voices |
| `assets/observers.json` | Original directional Kris/Susie poses and laughter |
| `assets/staging-v3.json` | Original thrown Ralsei, training dummy, stars and explosion |
| `assets/voices-v3.json` | Extracted native writer voices and action effects |
| `assets/town/town.json` | Original room composites and source inventory |

Keep every file referenced by those manifests at its original relative path. The public [provenance inventory](provenance/README.md) is sanitized metadata, not a drop-in runtime asset bundle. This package does not download, reconstruct or distribute copyrighted sprites, font atlases, audio or compiled game files. Missing private assets must be prepared separately from a source the operator is entitled to use.

## Reusable production structure

- `source/story.py`: one shared clock for dialogue, births, reactions and the ending.
- `source/crowd.py`: deterministic local separation and measured contact/fall events; cached simulation for up to 1,024 actors and parent-linked population layers through 32,768 stable IDs.
- `source/visual.py`: native sprite staging, observer reactions, camera, dialogue and edition-specific layout.
- `source/cosmic.py`: native explosion/stars/training-dummy art with authored drift and black-hole motion.
- `source/audio.py`: original writer voices, music and event-driven effects on the same clock.
- `source/render.py`: full-frame rendering, audio mix, FFmpeg export and input hashes.

Change story beats and character reactions together, then review the actual contact motion, dialogue holds and audio before exporting. The far crowd has individual positions but does not run a separate physical contact solver for all 32,768 actors. The black-hole geometry and movement are authored; the character, star and explosion images are original game assets.

## Approved v3 exports

[export.json](export.json) records the measured, approved Shorts and landscape pair: 118 seconds, 60 fps, 7,080 frames, H.264 and stereo AAC. Approved MP4 files are not included here. No publication or Release upload is implied by this production package.

The packaged six source files match the final private source hashes in [source-hashes.json](provenance/source-hashes.json). The landscape-only correction preserves a minimum nearest-neighbour native sprite footprint so distant hats and robes do not collapse into pink scarf pixels, and moves its counter into a reserved band above dialogue. The Shorts branch was checked against its approved source snapshot at 0, 23, 43, 73, 91, 104 and 114.5 seconds with byte-identical RGB frames. No duplicate old source tree is needed to run that unchanged branch.

Fresh encoding can differ in MP4 bytes with toolchain versions. Preserve approved delivery hashes by copying the original files verbatim; use the regeneration commands for production work, not as a promise of bit-identical binary encoding. Verify new exports with FFprobe, hashes, full playback and audio review as required by the [studio workflow](../../docs/workflow.md).
