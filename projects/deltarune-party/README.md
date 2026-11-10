# Deltarune Party

Deltarune Party is the studio's reusable Mario Party DS production project. The modules under `template/` share the DS board, player panels, dice, minigame roulette, rules, results, and vertical layout. The episode supplies the cast, story cues, map plate, and minigame.

```sh
cp projects/deltarune-party/template/*.py /path/to/episode/
```

Use Python 3.10 or newer with Pillow and NumPy. The module copies read assets from the episode directory.

| Input | Location or interface |
| --- | --- |
| Original DS panels, fonts, dice, and controls | `assets/mpds/`, including `font.json` and `raw/` |
| Original DELTARUNE sprites and dialogue font | `assets/deltarune/`, including `font.json` |
| Original Chapter 5 cast sprites and Castle plate | `assets/chapter5/`, with Seth and Aqua sprites, mini-faces, and shared text sound under `guests/` |
| Original DS effects and episode sound mix inputs | `assets/audio/`, including `mpds-roulette.wav`, `mpds-coin-contact.wav`, `mpds-coin.wav`, and the `soap/` sounds and music |
| Episode assets and simulation | The episode supplies native rules, title, preview, and rendered minigame screens |

## Soap Surfers example

[Ralsei Found a Lucky Space in Mario Party DS](episodes/soap-surfers/) is a reference episode. Ralsei lands on a question-mark space and earns ten coins from Seth and Aqua. The board turn ends and the four-player roulette draws Soap Surfers. The title stays on screen before the rules, and the four players use one steering and collision model. [Original Mario Party DS manual](https://www.nintendo.com/eu/media/downloads/games_8/emanuals/nintendo_ds_21/Manual_NintendoDS_MarioPartyDS_EN.pdf)

From the repository root, copy the shared modules and example into a local production directory containing the asset folders above.

```sh
cp projects/deltarune-party/template/*.py /path/to/episode/
cp projects/deltarune-party/episodes/soap-surfers/*.py /path/to/episode/
cd /path/to/episode
mkdir -p out/final
python3 mix_soap.py
python3 soap_film.py --output out/final/deltarune-party-ds-flower-short-v4.mp4
```

Install FFmpeg for audio mixing and export. Keep the extracted assets and their source records in the local production directory. The repository carries the production code and documentation.

## Shared interfaces

- Create `PartyBoard(background, route, spaces, players, sprite, heights)` with a board plate 180 pixels high and at least 240 pixels wide. Pass `CASTLE_LOOP` and `CASTLE_SPACES` for the established 12-space Castle map. Custom routes use one `blue`, `red`, or `event` entry per coordinate. The renderer connects the final space to the first.
- Use `route_position(space, progress)` for movement. A full step after the final space wraps to the first. Store each player's world position in `Pose`. Both screens derive positions from that state.
- Pass current poses, coins, stars, active player, and turn totals in `BoardState`. Set `Roll` during dice input and movement. `markers` accepts optional space index and asset pairs for episode mechanics.
- Call `upper(state)` for the minimap and standings and `lower(state, t)` for the board view and camera offset. Apply rewards once in the episode's timeline, then pass the updated state to `results(state, winner, award)` and the next turn.
- Use `PartyReel.roulette(lower, title, elapsed, lock_at)` after the board turn. Leave time between locking the title and opening `PartyReel.rules`, which renders the native rules and preview. `PartyReel.compose` frames the two 240 × 180 DS screens and dialogue in the 270 × 480 vertical composition. The episode supplies the minigame frames and transition times.

Copy from this template when starting an episode. Make shared UI changes here and copy them into the episode before rendering.
