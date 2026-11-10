"""Mix the Soap Surfers film against the replay's absolute event times."""

from mix import Mixer, ROOT, VOICES


AUDIO = ROOT / 'assets/audio/soap'
OUTPUT = ROOT / 'out/mix.wav'
PANS = {'queen': -.40, 'gerson': -.16, 'flowery': .16, 'ralsei': .40, 'seth': .21, 'aqua': -.28}
FLOWER_VOICE = '../chapter5/guests/flower-text.wav'
ACTION_AUDIO = '../chapter5/action'
VOICE_CUES = {
    **{who: (f'soap/{source}', gain) for who, (source, gain) in VOICES.items()},
    'seth': (FLOWER_VOICE, .86),
    'aqua': (FLOWER_VOICE, .86),
}
BOARD_KNIFE = {
    'throw': (f'{ACTION_AUDIO}/aqua-knife-throw.wav', .60, 1.5),
    'dodge': ('fight/snd_graze.wav', .33, 1),
    'hit': ('fight/snd_damage.wav', .55, 1),
    'fall': ('fight/snd_fall.wav', .46, 1),
}
SKILL_RELEASE = {
    'energy': (f'{ACTION_AUDIO}/queen-laser-fire.wav', .53),
    'jarona': ('fight/snd_smallswing.wav', .43),
    'fire': (f'{ACTION_AUDIO}/ralsei-fire-ignite.wav', .60),
    'hammer': (f'{ACTION_AUDIO}/gerson-hammer-throw.wav', .58),
}


def render_audio(duration, events, dialogue, text_rate):
    mix = Mixer(duration)

    def add(stem, time, name, level, length=None, **options):
        mix.add(stem, time, f'soap/{name}', level, length, **options)

    phases = {event['phase']: event['t'] for event in events if event['type'] == 'phase'}
    times = {event['type']: event['t'] for event in events}
    finish = times['finish']
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
    skill_hit_times = {event['t'] for event in events if event['type'] == 'skill_hit'}
    jarona_calls = 0
    for event in events:
        kind, time = event['type'], event['t']
        pan = PANS.get(event.get('id'), 0)
        if kind == 'turn_banner':
            mix.add('sound', time, 'mpds-turn-banner.wav', .49, fade=.004)
            mix.duck(time, time + .38, .77)
        elif kind == 'die':
            if event['action'] == 'start':
                add('sound', time, 'mpds-dice-spin.wav', .36, die_hit - time, fade=.006)
            else:
                add('sound', time, 'mpds-die-hit.wav', .66, fade=.002)
        elif kind == 'step':
            add('sound', time, 'mpds-board-step.wav', .32, fade=.002)
        elif kind == 'guest_step':
            pitch = .87 if event['id'] == 'seth' else 1.13
            add('sound', time, 'mpds-board-step.wav', .15, .13, pitch=pitch,
                fade=.010, pan=-.36)
        elif kind == 'board_event' and event['action'] == 'land':
            mix.add('sound', time + .05, 'fight/snd_power.wav', .34, .48, fade=.016)
        elif kind == 'board_knife' and event['action'] == 'windup':
            mix.add('sound', time, f'{ACTION_AUDIO}/aqua-knife-throw.wav', .17, .19,
                    pitch=1.24, fade=.010, pan=pan)
        elif kind == 'board_knife' and event['action'] in BOARD_KNIFE:
            source, gain, pitch = BOARD_KNIFE[event['action']]
            mix.add('sound', time, source, gain, pitch=pitch, fade=.004, pan=pan)
            if event['action'] in ('hit', 'fall'):
                mix.duck(time, time + .33, .71)
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
        elif kind == 'input':
            if event['action'] == 'start_minigame':
                add('sound', time, 'mpds-soap-confirm.wav', .43, fade=.003)
            elif event['action'] == 'continue_results':
                add('sound', time, 'mpds-menu.wav', .43, fade=.003)
        elif kind == 'go':
            add('sound', time, 'mpds-soap-start.wav', .62, fade=.003)
            add('sound', time + .04, 'mpds-soap-slide.wav', .24, fade=.013)
        elif kind == 'skill_cast' and event['skill'] == 'energy':
            mix.add('sound', time, f'{ACTION_AUDIO}/queen-laser-warning.wav', .32, fade=.008, pan=pan)
        elif kind == 'skill_cast' and event['skill'] == 'hammer':
            mix.add('sound', time + .18, f'{ACTION_AUDIO}/gerson-hammer-swing.wav', .22, .30,
                    fade=.023, pan=pan)
        elif kind == 'skill_release':
            skill = event['skill']
            source, gain = SKILL_RELEASE[skill]
            mix.add('sound', time, source, gain, fade=.004, pan=pan)
            if skill == 'fire':
                for offset in (.37, .27, .17, .07):
                    mix.add('sound', time - offset, f'{ACTION_AUDIO}/ralsei-fire-burst.wav',
                            .23, .10, fade=.005, pan=pan)
            if skill == 'jarona':
                index = 1 + jarona_calls % 4
                mix.add('voice', time - .22, f'{ACTION_AUDIO}/flowery-jarona-voice-{index}.wav',
                        .87, fade=.004, pan=pan)
                mix.duck(time - .22, time + .92, .51)
                jarona_calls += 1
        elif kind == 'skill_hit':
            source = (f'{ACTION_AUDIO}/flowery-jarona-punch.wav' if event['skill'] == 'jarona'
                      else 'fight/snd_damage.wav')
            mix.add('sound', time, source, .52, .52, fade=.008, pan=.46 * event['x'])
        elif kind == 'skill_dodge':
            mix.add('sound', time, 'fight/snd_graze.wav', .25, fade=.004, pan=pan)
        elif kind == 'bump':
            strength = event['strength']
            pan = .46 * event['x']
            gain = .36 if time in skill_hit_times else .30 + .34 * strength
            add('sound', time, 'mpds-soap-bump.wav', gain, fade=.003, pan=pan)
            if strength >= .5:
                add('sound', time + .08, 'mpds-soap-slide.wav', .13 + .16 * strength,
                    .28, fade=.026, pan=pan)
        elif kind == 'save':
            add('sound', time, 'mpds-soap-slide.wav', .25, .32, pitch=.94,
                fade=.028, pan=.46 * event['x'])
        elif kind == 'fall':
            add('sound', time, 'mpds-soap-fall.wav', .66, fade=.004, pan=.46 * event['x'])
            mix.duck(time, time + .40, .74)
        elif kind == 'finish':
            add('sound', time, 'mpds-soap-finish.wav', .69, fade=.004)

    for line in dialogue:
        if not line.get('voice', True):
            continue
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
    from soap_film import DIALOGUE_RATE, FPS, build, dialogue

    frames, events = build(FPS)
    render_audio(len(frames) / FPS, events, dialogue(events), DIALOGUE_RATE)


if __name__ == '__main__':
    main()
