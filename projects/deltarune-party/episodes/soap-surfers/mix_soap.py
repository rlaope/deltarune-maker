"""Mix the Soap Surfers film against the replay's absolute event times."""

from mix import Mixer, ROOT, VOICES


AUDIO = ROOT / 'assets/audio/soap'
OUTPUT = ROOT / 'out/mix.wav'
PANS = {'queen': -.40, 'gerson': -.16, 'flowery': .16, 'ralsei': .40}
FLOWER_VOICE = '../chapter5/guests/flower-text.wav'
VOICE_CUES = {
    **{who: (f'soap/{source}', gain) for who, (source, gain) in VOICES.items()},
    'seth': (FLOWER_VOICE, .86),
    'aqua': (FLOWER_VOICE, .86),
}


def render_audio(duration, events, dialogue, text_rate):
    mix = Mixer(duration)

    def add(stem, time, name, level, length=None, **options):
        mix.add(stem, time, f'soap/{name}', level, length, **options)

    phases = {event['phase']: event['t'] for event in events if event['type'] == 'phase'}
    times = {event['type']: event['t'] for event in events}
    go, finish = times['go'], times['finish']
    victory = times['win']
    tracks = (
        (phases['castle'], phases['rules'], 'mpds-wiggler.flac', .43, 0),
        (phases['rules'], phases['soap'], 'mpds-intro.flac', .44, 0),
        (phases['soap'], finish, 'mpds-into-the-fairy-tale.flac', .52, 0),
        (victory, phases['return'], 'mpds-result.flac', .48, 0),
        (phases['return'], duration, 'mpds-wiggler.flac', .42, phases['rules']),
    )
    for start, end, source, gain, offset in tracks:
        if end > start:
            add('music', start, source, gain, end - start, offset=offset, fade=.045)

    die_hit = next(event['t'] for event in events if event['type'] == 'die' and event['action'] == 'hit')
    roulette_lock = next(event['t'] for event in events if event['type'] == 'roulette' and event['action'] == 'lock')
    for event in events:
        kind, time = event['type'], event['t']
        pan = PANS.get(event.get('id'), 0)
        if kind == 'die':
            if event['action'] == 'start':
                add('sound', time, 'mpds-dice-spin.wav', .36, die_hit - time, fade=.006)
            else:
                add('sound', time, 'mpds-die-hit.wav', .66, fade=.002)
        elif kind == 'step':
            add('sound', time, 'mpds-board-step.wav', .32, fade=.002)
        elif kind == 'coin_contact':
            mix.add('sound', time, 'mpds-coin-contact.wav', .30, fade=.003, pan=pan)
        elif kind == 'party_reward':
            mix.add('sound', time, 'mpds-coin.wav', .45, fade=.003, pan=pan)
        elif kind == 'roulette':
            if event['action'] == 'start':
                mix.add('sound', time, 'mpds-roulette.wav', .54, roulette_lock - time, fade=.003)
            else:
                add('sound', time, 'mpds-menu.wav', .53, fade=.002)
        elif kind == 'rules':
            add('sound', time, 'mpds-menu.wav', .34, fade=.002)
        elif kind == 'input' and event['action'] == 'start_minigame':
            add('sound', time, 'mpds-soap-confirm.wav', .43, fade=.003)
        elif kind == 'go':
            add('sound', time, 'mpds-soap-start.wav', .62, fade=.003)
            add('sound', time + .04, 'mpds-soap-slide.wav', .24, fade=.013)
        elif kind == 'bump':
            gain = .35 + .16 * min(1, event['speed'])
            add('sound', time, 'mpds-soap-bump.wav', gain, fade=.003, pan=.46 * event['x'])
        elif kind == 'fall':
            add('sound', time, 'mpds-soap-fall.wav', .66, fade=.004, pan=.46 * event['x'])
            mix.duck(time, time + .40, .74)
        elif kind == 'finish':
            add('sound', time, 'mpds-soap-finish.wav', .69, fade=.004)

    for line in dialogue:
        source, gain = VOICE_CUES[line['speaker']]
        blips = [line['start'] + index / text_rate for index, char in enumerate(line['text'])
                 if char.isalnum() and line['start'] + index / text_rate < line['end']]
        for index, time in enumerate(blips):
            end = blips[index + 1] if index + 1 < len(blips) else time + .09
            mix.add('voice', time, source, gain, min(end, line['end']) - time, fade=.004)
        if blips:
            mix.duck(blips[0], min(blips[-1] + .17, line['end']), .54)

    mix.write(OUTPUT, AUDIO / 'mix-receipt.json')


def main():
    from soap_film import DIALOGUE, DIALOGUE_RATE, DURATION, FPS, build

    frames, events = build(FPS)
    if len(frames) != round(DURATION * FPS):
        raise ValueError('Soap Surfers frame count disagrees with film duration')
    render_audio(DURATION, events, DIALOGUE, DIALOGUE_RATE)


if __name__ == '__main__':
    main()
