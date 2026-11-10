# Deltarune Party

Render Mario Party DS crossover episodes as 9:16 Shorts from the same board, HUD, and export code. The shared framing keeps the two 240 × 180 DS screens, their borders, and the dialogue gap in the same positions in every episode. The exporter scales the pixel art to 2160 × 3840 at 60 fps and adds stereo audio.

## Render an episode

Use Python 3.10 or newer, Pillow, NumPy, and FFmpeg. Run these commands from the repository root. Each workspace is a private directory containing the prepared `assets/` for that episode. The renderer loads the episode code and shared modules from this checkout and writes outputs under the workspace.

```sh
python3 -m pip install Pillow NumPy

python3 projects/deltarune-party/render.py boo-tag --workspace /path/to/boo-workspace -- --stills 8.9 11.5 17.6 23
python3 projects/deltarune-party/render.py boo-tag --workspace /path/to/boo-workspace

python3 projects/deltarune-party/render.py soap-surfers --workspace /path/to/soap-workspace --mix-only
python3 projects/deltarune-party/render.py soap-surfers --workspace /path/to/soap-workspace -- --output out/final/deltarune-party-soap-surfers.mp4
```

Boo Tag builds its own mix and writes `out/final/boo-tag-short-v5.mp4`. Soap Surfers reads `out/mix.wav` by default. The stills commands render representative frames under `qa/` for either episode. Pass episode options after `--` to the launcher.

| Episode | Original asset inputs under the workspace |
| --- | --- |
| [Boo Tag](episodes/boo-tag/) | `assets/mpds/` (including both Double Dice cards, controls and red roll faces), `assets/deltarune/` (dialogue font), `assets/cast/`, `assets/board/courtyard.png`, `assets/boo-native/`, and `assets/audio/` |
| [Soap Surfers](episodes/soap-surfers/) | `assets/mpds/` (including `soap/`), `assets/deltarune/`, `assets/chapter5/` (including `guests/` and `action/`), and `assets/audio/` (including `soap/` and `fight/`) |

Keep extracted sprites, game audio, and their provenance records in the private workspace. See the [studio asset policy](../../AGENTS.md) and the [original Mario Party DS manual](https://www.nintendo.com/eu/media/downloads/games_8/emanuals/nintendo_ds_21/Manual_NintendoDS_MarioPartyDS_EN.pdf).

## Build the next episode

1. Add a directory under `episodes/` and register its film entry point and any episode-specific asset checks in `render.py`. Use the Boo Tag entry for an episode that mixes audio and renders in one command.
2. Give the episode a cast, map plate, board route, and space types. Pass these to `PartyBoard` and feed both screens from the same `BoardState`. Use `party_turns.py` to schedule rolls, moves, rewards, and camera handoffs. Leave room for the active player's banner and the full coin reward before the next turn or minigame draw.
3. Use `party_items.py` for the native Double Dice selection, confirmation, and two rolls. Keep the episode's board encounter and dialogue in its own module. Connect any new effects to the same events the board uses to update the coin counters and poses.
4. Put the minigame simulation in the episode directory and keep the native rules card and title art in the private workspace. Use `ShortsReel` for the roulette, rules, and final screen composition, the shared mixer for cue timing, and `start_encoder` for the final MP4.
5. Render stills around each handoff before encoding the full episode. Verify the final MP4 by playing the transitions and ending and checking the export dimensions, frame rate, audio, and SHA-256.

Boo Tag demonstrates a Boo encounter, native Double Dice, a three-turn board sequence, and a treasure chase. Soap Surfers demonstrates a Flower Castle event and a different minigame simulation using the same board and Shorts framing.
