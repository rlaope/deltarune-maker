# Deltarune Party

Render Mario Party DS crossover episodes as 9:16 Shorts from the same board, HUD, and export code. The shared framing keeps the two 240 × 180 DS screens, their borders, and the dialogue gap in the same positions in every episode. The exporter scales the pixel art to 2160 × 3840 at 60 fps and adds stereo audio.

The [playable board game](game/README.md) contains five large chapter maps, local four-player turns, and a deterministic rules engine for staging future episodes.

## Render an episode

Use Python 3.10 or newer, Pillow, NumPy, and FFmpeg. Run these commands from the repository root. Each workspace is a private directory containing the prepared `assets/` for that episode. The renderer loads the episode code and shared modules from this checkout and writes outputs under the workspace.

```sh
python3 -m pip install Pillow NumPy

python3 projects/deltarune-party/render.py boo-tag --workspace /path/to/boo-workspace -- --stills 8.9 11.5 17.6 23
python3 projects/deltarune-party/render.py boo-tag --workspace /path/to/boo-workspace

python3 projects/deltarune-party/render.py soap-surfers --workspace /path/to/soap-workspace --mix-only
python3 projects/deltarune-party/render.py soap-surfers --workspace /path/to/soap-workspace -- --output out/final/deltarune-party-soap-surfers.mp4

python3 projects/deltarune-party/render.py fast-food-frenzy --workspace /path/to/diner-workspace
```

Boo Tag and Fast Food Frenzy build their own mixes and write `out/final/boo-tag-short-v5.mp4` and `out/final/fast-food-frenzy-short-v7.mp4`. Soap Surfers reads `out/mix.wav` by default. The `--stills` episode option renders representative frames under `qa/`. Pass episode options after `--` to the launcher.

| Episode | Original asset inputs under the workspace |
| --- | --- |
| [Boo Tag](episodes/boo-tag/) | `assets/mpds/` (including both Double Dice cards, controls and red roll faces), `assets/deltarune/` (dialogue font), `assets/cast/`, `assets/board/courtyard.png`, `assets/boo-native/`, and `assets/audio/` |
| [Soap Surfers](episodes/soap-surfers/) | `assets/mpds/` (including `soap/`), `assets/deltarune/`, `assets/chapter5/` (including `guests/` and `action/`), and `assets/audio/` (including `soap/` and `fight/`) |
| [Fast Food Frenzy](episodes/fast-food-frenzy/README.md) | `assets/mpds/`, `assets/deltarune/` (including `jarona-aura/`), `assets/cast/`, `assets/boards/chapter-5/second-diner.png`, `assets/fast-food-native/`, and `assets/audio/` |

Keep extracted sprites, game audio, and their provenance records in the private workspace. See the [studio asset policy](../../AGENTS.md) and the [original Mario Party DS manual](https://www.nintendo.com/eu/media/downloads/games_8/emanuals/nintendo_ds_21/Manual_NintendoDS_MarioPartyDS_EN.pdf).

## Build the next episode

1. Add a directory under `episodes/` and register its film entry point and any episode-specific asset checks in `render.py`. Use the Boo Tag entry for an episode that mixes audio and renders in one command.
2. Give the episode a cast, map plate, board route, and space types. Pass these to `PartyBoard` and feed both screens from the same `BoardState`. Use `party_turns.py` to schedule rolls, moves, rewards, and camera handoffs. Use the reward and dialogue timing rule below to let each turn finish on screen before starting the next camera move.
3. Use `party_items.py` for the native Double Dice selection, confirmation, and two rolls. Keep the episode's board encounter and dialogue in its own module. Connect any new effects to the same events the board uses to update the coin counters and poses.
4. Put the minigame simulation in the episode directory and keep the native rules card and title art in the private workspace. Use `ShortsReel` for the roulette, rules, and final screen composition, the shared mixer for cue timing, and `start_encoder` for the final MP4. Schedule cast replies from gameplay events and give each important action its native sound cue.
5. Review the opening, a handoff, a busy gameplay beat, and the payoff at phone size. Compare a native render still with the same timestamp decoded from the export to locate any loss of readability. Play the transitions and ending and check the final MP4's dimensions, frame rate, audio, and SHA-256.

### Hold the camera after a reward

Use `next_turn_start` from `party_turns.py` to schedule the next pan from the current `BoardTurn` and the end time of its optional reaction. The defaults hold for at least 1.60 seconds after the coin count updates and for 0.82 seconds after a reaction finishes. The later boundary wins. Apply the same calculation to the final award before handing off to the draw.

```python
from party_turns import next_turn_start

camera_start = next_turn_start(turn, dialogue_end=reaction["end"] if reaction else None)
```

[Fast Food Frenzy](episodes/fast-food-frenzy/README.md) uses this timing for Lancer and Susie's coin reactions and Noelle's covered-menu reward.

### Schedule a character exchange

Write a call and a reply that depend on the same visible event. Use the reply to reveal a different intention, contradict the first speaker, or set up a later payoff. Keep both characters readable when a look, laugh, or physical response lands the joke. A reward, mistake, or result can carry the exchange while routine dice rolls and movement have room to play.

```python
from party_dialogue import PartyDialogue, Reply, Speaker
from party_turns import next_turn_start

dialogue = PartyDialogue({
    "susie": Speaker("susie-face", "../cast/susie-text.wav", -.2),
    "lancer": Speaker("lancer-face", "../cast/lancer-text.wav", .2),
})
reaction_end = dialogue.exchange(
    award_event, Reply("susie", "* That's snack money!"),
    Reply("lancer", "* So... one snack?", portrait="lancer-laugh-face"),
)
camera_start = next_turn_start(turn, dialogue_end=reaction_end)
```

Initialize `ShortsReel` with `dialogue.text_rate`, call `dialogue.validate_fit(reel.font)` after scheduling, and pass `dialogue.cues` to `compose`. Call `dialogue.mix(mixer)` after adding music and action cues. The box and voice blips use the same schedule, and the voice mix ducks music while leaving the action stem audible. For minigame chatter, pass `until` with the time of the next protected cue or cut. The exchange must fit before that time, including the last line's reading hold.

### Review the picture, action sounds, and reactions

| Feedback | What the existing episodes show | Gate for the next episode |
| --- | --- | --- |
| The first episode looked sharper. | Camera Shy v2 puts the photographed actor in the foreground against quiet walls at 17.19 and 29.50 s. In Fast Food Frenzy v7 the floor competes with Susie at 14.68 s, and at 50.18 s the runners are small beside the bright belts and food. The local masters both use 2160 × 3840, 60 fps and integer nearest-neighbor enlargement. Average video bitrate is 0.96 Mbps for Camera Shy and 3.15 Mbps for Fast Food Frenzy. | Use wide shots to establish geography, then give the current player, action, or reaction visual priority. Check that the actor's silhouette and relevant prop read at phone size during motion. Use a closer view, quieter backdrop, or staging in the source render where needed. |
| The latest sound has more detail. | Fast Food Frenzy ties the 26.99–27.34 s coin contacts, 47.91 s START, and 61.327 and 68.093 s falls to source sounds in the mix receipt. | Map important action events to their original source files and check their actual placement with `missing_sound_cues(events, mixer.cues, expected_sources)` from `mix.py`. The map values are the expected filenames relative to `assets/audio/`. Review dice, coin contacts, start and finish, and minigame impacts in context. |
| Give the cast more back-and-forth. | Study Fall v5 builds from Berdly's trap reaction into Lancer and Susie's teasing at 19.80–24.53 s, then the rematch at 26.14–29.45 s. Fast Food Frenzy v7 has an opening exchange, while the +3 coin reactions at 8.68 and 14.97 s are solo lines. | Give the episode's turning point a visible action, a specific reaction from another character, and a payoff. Use the exchange scheduler for lines triggered by that action, and keep the camera in place through the reply and turn hold. |

The picture comparison uses local masters at a common phone-size preview. Across six Camera Shy frames and seven Fast Food Frenzy frames, the native render and the decoded master differed by under 0.05 levels per 8-bit YUV channel on average at source-pixel centers. The sound comparison uses event and mix receipts.
