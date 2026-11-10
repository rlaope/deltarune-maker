"""Mix original DS music and effects with native DELTARUNE text sounds."""

from boo_film import (DURATION, FINISH, GO, LOCK, MATCH, PAYOUT,
                      RETURN, ROOT, RULES, TEXT_RATE, WIN_REVEAL)
from mix import Mixer
from party_turns import PARTY_SOUND_CUES


SOUNDS = {
    **PARTY_SOUND_CUES,
    'chest_open': ('../cast/chest-open.wav', .55),
    'board_boo': ('../boo-native/enter.wav', .51),
    'go': ('mpds-native-start.wav', .69),
    'boo_spawn': ('../boo-native/enter.wav', .52),
    'boo_attach': ('../boo-native/tag.wav', .60),
    'tag': ('../boo-native/tag.wav', .62),
    'finish': ('mpds-native-finish.wav', .66),
}

PANS = {'kris': -.27, 'susie': .27, 'ralsei': -.16, 'gerson': .17}


def render_audio(film):
    mixer = Mixer(DURATION)
    for start, stop, path, gain, offset in (
        (0, RULES, 'mpds-wiggler.flac', .40, 0),
        (RULES, MATCH, 'mpds-intro.flac', .40, 0),
        (GO, FINISH, '../boo-native/pressure-native.flac', .44, 0),
        (WIN_REVEAL, RETURN, 'mpds-result.flac', .43, 0),
        (RETURN, DURATION, 'mpds-wiggler.flac', .36, RULES),
    ):
        mixer.add('music', start, path, gain, stop - start, offset=offset, fade=.09)

    mixer.add('sound', MATCH + .06, '../boo-native/chest.wav', .48, GO - MATCH - .08, fade=.08)
    mixer.add('sound', RETURN + 2.23, '../boo-native/enter.wav', .23, fade=.013)
    for event in film.events:
        kind, t = event['type'], event['t']
        if kind == 'die_spin':
            mixer.add('sound', t, 'mpds-dice-spin.wav', .35, event['duration'], fade=.008,
                      pan=PANS.get(event.get('id'), 0))
        elif kind == 'roulette_spin':
            mixer.add('sound', t, 'mpds-roulette.wav', .52, LOCK - t, fade=.008)
        elif kind == 'board_hit':
            mixer.add('sound', t, '../boo-native/tag.wav', .66, .44, fade=.035)
            mixer.duck(t, t + .35, .65)
        elif kind == 'lost_coin_contact':
            mixer.add('sound', t, 'mpds-coin-contact.wav', .28, .125, fade=.009, pan=.16)
        elif kind == 'score_lock':
            mixer.add('sound', t, 'mpds-menu.wav', .19, .13, fade=.015, pan=PANS[event['id']])
        elif kind in SOUNDS:
            path, gain = SOUNDS[kind]
            mixer.add('sound', t, path, gain, fade=.003, pan=PANS.get(event.get('id'), 0))
            if kind in ('turn_banner', 'tag', 'boo_spawn'):
                mixer.duck(t, t + .19, .74)
    for index in range(5):
        mixer.add('sound', PAYOUT - .28 + index * .07, 'mpds-coin-contact.wav', .25, fade=.003)

    for cue in film.dialogue:
        start, end = cue['start'], cue['end']
        filename = f"../cast/{cue['speaker']}-text.wav"
        blips = [start + i / TEXT_RATE for i, char in enumerate(cue['text'])
                 if char.isalnum() and start + i / TEXT_RATE < end]
        for i, t in enumerate(blips):
            next_time = blips[i + 1] if i + 1 < len(blips) else t + .085
            mixer.add('voice', t, filename, .88, min(next_time, end) - t, fade=.004,
                      pan=PANS[cue['speaker']] * .6)
        if blips:
            mixer.duck(blips[0], min(blips[-1] + .15, end), .55)

    output = ROOT / 'out/mix.wav'
    mixer.write(output, ROOT / 'qa/mix.json')
    return output
