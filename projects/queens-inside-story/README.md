# Kris & Susie: Queen’s Inside Story

Play a DELTARUNE × Mario & Luigi: Bowser’s Inside Story encounter in Queen’s mansion. Open the service lift, survive Queen’s alternating attacks, then time Kris’s sword or Susie’s axe with the Nintendo DS command blocks. The same simulation supports manual play and the one-minute Shorts replay.

## Play locally

Use Node.js 22 or newer. Prepare the private runtime asset directory with `dr/` and `bis/` from your production workspace. See the [asset source notes](provenance/README.md) for the required files and their sources.

```sh
cd projects/queens-inside-story
export QUEEN_ASSET_DIR=/absolute/path/to/prepared/assets
npm start
```

Open `http://127.0.0.1:8623/` and select **Play** or **Watch replay**. You can also run `npm run build:game` and open `out/queens-inside-story-play.html` directly. The portable HTML embeds the private runtime assets locally.

- Use the arrows to move. A jumps with Kris and B jumps with Susie. Hit the question block from below to add its Mushroom directly to inventory.
- Press A near Queen to advance dialogue. In battle, A and B dodge independently. Look for each attack’s tell.
- When a hero steps forward, cycle command blocks with Left and Right. Press that hero’s action button to jump into the selected block. Press it again to target Queen. Tap on both sword contacts, or hold and release the axe when it flashes.
- The Item block spends a Mushroom. L or Escape goes back. The on-screen controls support touch and pointer input.

## Reuse the encounter

Edit the field positions, HP, dialogue, and two attack waves in [scene.mjs](scene.mjs). Each attack row has its tell time, target hero, projectile, and flight time. [engine.mjs](engine.mjs) owns input, movement, collision, inventory, and turn phases. [render.mjs](render.mjs) draws the Nintendo DS command interface and DELTARUNE cast. [audio.mjs](audio.mjs) maps events to source cues. Edit [replay.mjs](replay.mjs) to re-time the authored playthrough after changing the encounter. Manual play uses the same engine and accepts ordinary keyboard input.

## Verify and render a short

Install FFmpeg with `libx264`, Python with NumPy, and Playwright’s Chromium. Use `CHROMIUM` only to select an existing compatible executable. [Playwright browser setup](https://playwright.dev/docs/browsers#install-browsers)

```sh
npm ci
npx playwright install chromium
npm test
npm run build:game
npm run test:browser
node capture.mjs events
node capture.mjs short
python3 mix.py
./finish.sh
```

The result is `out/short.mp4`, 2160 × 3840 at 60 fps, with stereo AAC. To name an export, pass its output path to `finish.sh`. For a saved-file playback check, run `node qa/playback.cjs out/short.mp4`.
