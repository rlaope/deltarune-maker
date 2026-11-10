# DELTARUNE Party DS – Dark World Tour

Play a four-person local board game across Card Kingdom, Cyber World, TV World, the Sanctuaries, and Flower Kingdom. Each chapter has its own directed routes, districts, shortcuts, star locations, and encounters. The upper screen shows the world overview and standings. The lower screen follows the active piece across the two-dimensional board.

## Launch

Run from the repository root with Python 3.10 or later. Use Pillow when preparing the assets.

```sh
python3 -m pip install Pillow
python3 projects/deltarune-party/game/prepare_assets.py \
  --workspace /path/to/private-board-workspace \
  --shared-assets /path/to/private-boo-tag-workspace/assets
python3 projects/deltarune-party/game/serve.py \
  --workspace /path/to/private-board-workspace --open
```

The server listens on loopback at `http://127.0.0.1:8765/`. The preparation command keeps the original location images and SHA-256 receipts under `sources/` in the private workspace. It also copies the previously prepared DELTARUNE cast and Mario Party DS UI and audio. Run it with `--offline` to reuse retained source images. Original art and audio remain in the private workspace. See the [original-art inventory](https://deltarune.wiki/w/Category:Location_files) and the [studio asset policy](../../../AGENTS.md).

## Play and reuse

- Choose a chapter and the number of rounds, then roll and pass the controls to the next player when your turn ends. Follow the prompts for route choices, items, encounters and star purchases.
- Open **Map** to see the whole chapter. Drag the lower screen and zoom to inspect a district. Use **Sound** to enable the original board cues.
- Blue and red spaces add or remove coins on landing. Item spaces provide Double Dice. Stars cost 20 coins and can be bought when passed. Stars determine the result before coins.
- `boards.mjs` defines the chapters, world-space coordinates and route graphs. A directed connection can include its own label and coin cost. A landed encounter can offer dialogue, choices, a reward, a toll, an item, or a warp. Put each chapter's scene text and outcomes next to its route data.
- `engine.mjs` is the browser-independent rules engine. Construct `new BoardGame(board, {seed, rounds, start})` to begin an authored sequence from a particular space. Omit `start` for the chapter's regular start. Dispatch roll, item, choice and end-turn commands. The resulting events identify each move, landing, effect and handoff.
- Use **Replay** to download the board definition, setup, and action trace as JSON. Create `new BoardGame(replay.boardDefinition, replay.setup)`, then dispatch each `action` in `replay.trace` in order. The saved map keeps a scene reproducible after the live board is edited.

Run the engine and chapter graph tests with Node.js.

```sh
node --test projects/deltarune-party/game/tests/*.test.mjs
```
