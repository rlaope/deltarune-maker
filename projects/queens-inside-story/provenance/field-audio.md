# Nintendo DS field and jump audio

The US CLJE release of *Mario & Luigi: Bowser’s Inside Story* stores these sequences at `Sound/sound_data.sdat`. Its SHA-256 is `e25df87f7eb49e2dbd0e59bdef7d7af4b1460c05ea48509d29c09569602b3f76`. The WAVs exported for this revision retain the sequence’s note, pitch, envelope and bank data through Nintendo DS sound-driver emulation at 48 kHz stereo. [DualRip f69e23c](https://github.com/TetraSsky/DualRip/tree/f69e23c63a7d0985a474d0cbaeb2b364174748ac)

| Local file | Original resource | Use |
| --- | --- | --- |
| `field-jump.wav` | SSAR 2 entry 5, `SE_ML_JUMP` | Kris and Susie’s field takeoff |
| `field-block.wav` | SSAR 2 entry 37, `SE_BLOCK2` | Mushroom block contact |
| `field-pickup.wav` | SSAR 2 entry 27, `SE_BLOCK_ITEM_GET` | Mushroom pickup, 60 ms after block contact |
| `battle-jump.wav` | SSAR 3 entry 17, `SE_BTL_ML_JUMP1` | Command block hop and attack takeoff |
| `dodge.wav` | SSAR 3 entry 82, `SE_BTL_ML_JUMP_SMALL` | Defensive hop, using the existing named DS extraction |
| `stomp.wav` | SSAR 3 entry 33, `SE_BTL_STOMP1` | Stomp contact and rebound, using the existing named DS extraction |
| `peachs-castle.mp3` | SSEQ 71, `MUS_PE_CASTLE` | Field music |

The battle capture aligns the full hop with the command and attack actions and the stomp with the first contact that starts the rebound. The first contact and the rebound share an event frame, so they use one sound. [Nintendo DS gameplay reference](https://tasvideos.org/4071M) · [Earlier DS sound extraction](https://drive.google.com/drive/folders/1S4hokXz6Mx-AawH5Te2tu1ZY5sBWw-yJ)

The 2SF archive lists the track as *Peach’s Castle*. Waveform correlation between its render and ROM sequence 71 was 0.993, 0.996 and 0.976 at three test windows. The browser file contains the steady-state loop from the 44.1 kHz stereo sequence render, beginning at PCM frame 4,587,221 and ending immediately before frame 8,939,418. The resulting 4,352,197 PCM frames decode to 98.689274 seconds. [Nintendo DS 2SF track list](https://www.zophar.net/music/nintendo-ds-2sf/mario-luigi-bowsers-inside-story) · [Composer’s project page](https://yokoshimomura.com/solo-lead-composer/mario-luigi-bowsers-inside-story/)

To reproduce the extracts, run DualRip on the game’s sound archive.

```sh
dualrip --file sound_data.sdat --archive 2 --only 5 27 37 --out field --rate 48000
dualrip --file sound_data.sdat --archive 3 --only 17 --out battle --rate 48000
dualrip --file sound_data.sdat --sequence 71 --out music --rate 44100
ffmpeg -i music/SSEQ/071_MUS_PE_CASTLE.wav \
  -af 'atrim=start_sample=4587221:end_sample=8939418,asetpts=PTS-STARTPTS' \
  -c:a libmp3lame -q:a 2 -metadata title="Peach's Castle" \
  -metadata artist='Yoko Shimomura' peachs-castle.mp3
```
