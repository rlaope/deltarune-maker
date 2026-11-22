# Production lessons

Lessons from finished crossovers, each learned from a rejected cut. They apply to every project in the studio. The workflow says what to do; this page records what went wrong when it was skipped.

## Match the original before inventing anything

- Measure the source before drawing. Cut dense frame sheets (0.05-0.12 s apart) around each event and read the exact frame of every throw, release, catch and contact. Sheets at 0.5 s alias with the beat and give unusable times.
- Copy the original's layout and mechanic: who stands where, what comes in, what the player does on the cue. Then swap the cast in. A medley of loose, invented actions was rejected. A few games done faithfully beat many loose ones.
- For a game move from DELTARUNE, port its behaviour from decompiled code and compare the result with real gameplay footage frame by frame. The Rude Buster bolt is not the beam sprite alone: `obj_rudebuster_bolt` leaves an afterimage every step (beam frame 4, y-scale 1.8 shrinking 0.1 per step, alpha 0.8 fading 0.04 per step). Those afterimages make the stacked fan of 10-17 chevrons that players recognise. A beam with three ghosts read as "not the original sprite".
- Keep the original's transitions. A remix that cuts between games on a few black frames should cut the same way. A folding-screen transition read as a glitch.

## Put every cue on the sound

- Look for an on-screen input indicator in the source run first, such as a badge, counter or judgement icon that reacts on each hit. Scan it at the video frame rate. It tells you which inputs exist. In a Korean Rhythm Heaven DS Perfect run, the pink "P" badge flashes blue for one frame on every successful input.
- The indicator frame is not the hit. Pair each flash with the nearest high-band audio onset and measure the lag (about 30 ms early in that run). Cue on the onset. Cues placed on the raw flash frames cut encoded-audio sync from 137 to 62 of 173 inputs within 30 ms.
- A partner's action (a throw, the other player's kick) is audible in the music. Take its time from the onset between two player inputs. A computed midpoint was up to 40 ms off, and a fixed lead time made a whole game feel off-beat.
- Let each flight last exactly the gap between its two strikes. A fixed-tempo rally drifts.
- After rendering, re-detect onsets in the encoded audio and report how many cues land within 30 and 70 ms, compared with the previous version. State that sync was measured, not heard, when nobody listened.

## Use native sprites the way the game uses them

- Never draw limbs, liquid streams or props when a native action sprite exists. Hand-drawn arms and tea streams were rejected as unnatural.
- A thrown object must be the object the thrower is holding. Crop it from the thrower's release frame and launch it from those pixels. A teacup flying from a hand that held an orange glass read as a prop swap.
- Bust sprites drawn for a counter go behind the counter at one fixed scale. Standing them on the floor made the character change height between frames.
- Draw every sprite at its native origin, and keep idle and action frames on the same feet line and scale.
- Rotate small sprites only in 90-degree steps. Free rotation garbles 30-pixel art.
- Give an airborne object a ground shadow, or it reads as a stray sprite.

## Cast for recognition

- Keep a game's approved cast and staging when it appears again in a later film. Port the approved code instead of rewriting it.
- Give each character a role built on their own signature action or prop. For example, Aqua throws her knife and Gerson bats back Rude Buster.
- The premise of the original game must be obvious with no explanation. Courtship needs a date scene. Farming needs crops coming out of soil and a basket. Two characters standing at a sunset meant nothing to the audience.

## Keep the picture full and quiet

- Fill the frame. Trim a native room's black void and scale it to cover the canvas. Never leave a black band under a cropped room.
- Do not add information panels nobody asked for. A progress counter and a full set list on the longform layout were rejected.
- Give each contact effect a short life and let it end before the next contact starts. Overlapping rings and a white flash on every hit read as clutter and strobing.

## Review the actual export

- Check a reworked hand-off one still per phase: hold, raise, release, first flight frame, apex, catch, toss. Ask whether the same object is in the hand, then in the air, then caught, and whether the actor's size stays constant. Three renders in a row each found the next defect that this check would have caught first.
- Review fast exchanges on a strip of 12-18 consecutive encoded frames, and ask where the projectile is and what covers whom in each frame. Single stills hid blobs, teleports and strobing.
- Cut encoded frames of every scene touched in a revision, not only the ones in the feedback. A scene that passed as a still can freeze or skip its key frame in the encode. Fix a failed beat and render again before delivering.

## Pick the format from data

- Before pitching ideas, search the platform and collect the view count, length and channel of a few hundred recent fan shorts. Group them by format and compare medians. Pitches made without numbers were all rejected.
- In one snapshot of about 300 DELTARUNE shorts under three minutes, the medians were: songs with lyrics about 800K, battle animations about 560K, "what if" or "but it's X" about 250K, dialogue skits about 120K, and crossovers that drop the cast into another game about 4K. Re-measure before trusting these numbers; trends move.
- "DELTARUNE, but it's X" works as a series. Each episode keeps the frame (a handheld, a fighting game, an anime opening) and swaps the subject. Plan the next boss or opening as an episode with a title card.
- For an anime-opening remake, first search for openings that have already been remade with the game, and pick a popular one that has not.

## Pace for reading, not for length

- A story that hurries from walk to boss to win reads as rushed, even when every beat is present. Let each beat hold for its text at about 21 glyphs per second plus a hold, and put the cause on screen before each reaction.
- When the runtime has to shrink, cut whole beats (an extra attack, a flavour line, a heal) rather than speeding everything up. Keep the story beats (the walk, the reveal, the boss's own lines) and shorten the middle of the battle.
- Give a series episode a short title card ("EPISODE: <BOSS>") after the boot screen.
- On a small screen, draw battle sprites slightly smaller than the field sprites and leave visible room in the bullet box. A full-size cast pressed against the box left no space to read a dodge.

## Port the boss, then make it readable

- Port each attack's spawn pattern, speed and timing from the decompiled object code, and quote the native line that announces it. Then thin the bullets until they read at the target resolution, and say so in the notes.
- A bullet that touches the SOUL always causes a hurt flash and an HP drop. Plan the SOUL's path so near misses and hits both happen on purpose.
- Use the reward the game actually gives for the route shown. Sparing a boss and fighting him to defeat give different items, so check the event code for which flag gives which reward.
- In a fighting-game parody, keep the opponent's signature attacks from the boss fight (arrow volleys, shell pinball, the swing-down) and drop decoration that duplicates them. Every reaction still needs its cause on screen.
- After a knockout, let the boss return to his overworld form and react in character before the win screen. A body hanging in mid-air after the K.O. read as a bug.
- Frame both fighters whole during every beat that matters to both of them, including the post-K.O. reaction. A camera biased to one side clipped the other fighter off the edge.

## Music, Content ID and length

- Game music is the composer's work. Chiptune or MIDI arrangements of it still match Content ID, and the publisher claims them. Never describe an arrangement as original music in a hand-off.
- On YouTube, a vertical Short of one to three minutes with any active claim is blocked worldwide. Under 60 seconds it stays viewable, though the claimant may take the revenue. Long-form videos over three minutes, and horizontal videos, stay viewable with a monetise or track claim.
- So a Short that uses game or label music must be 59 seconds or less. Assert the limit in the story clock and check the encoded file's duration before delivering. To run longer, either write fully original music or publish as a different format.
- Replacing a boss theme with original music to keep the length was rejected: the audience expects that boss's theme. Prefer the theme in a 59-second cut.
- Do not dispute a claim on music you did use, and do not detune or retime a theme to slip past matching.

## Editions

- A longform edition gets its own 16:9 layout around the same game screen, not the vertical frame with bars.
- Split a long vertical cut into parts on the original's own scene changes, about a minute each. Re-encode each part for a frame-exact cut, with a short audio fade at both ends.
- If the source ends with a results screen, keep a few seconds of it after the ending.
- Discord attachments over 10 MB are dropped silently. Encode a review copy under that limit and keep the full-resolution master separately.
