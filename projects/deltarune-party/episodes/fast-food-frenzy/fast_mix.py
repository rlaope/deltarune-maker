"""Mix the DS cartridge cues and DELTARUNE text voices against the recorded action."""

from mix import Mixer
from reel_art import ROOT


NATIVE = '../fast-food-native/'
PANS = {'lancer': 0, 'susie': -.28, 'noelle': .28, 'flowery': .12}
BOARD_SOUNDS = {
    'turn_banner': ('mpds-turn-banner.wav', .49),
    'die_hit': ('mpds-die-hit.wav', .57),
    'board_step': ('mpds-board-step.wav', .29),
    'blue_coin': ('mpds-coin-blue.wav', .53),
    'food_event_open': ('mpds-menu.wav', .38),
    'food_focus': ('mpds-item-focus.wav', .32),
    'food_select': ('mpds-item-confirm.wav', .54),
    'food_reveal': ('mpds-menu.wav', .47),
    'food_coin_contact': ('mpds-coin-contact.wav', .28),
    'food_reward': ('mpds-coin-blue.wav', .54),
    'green_team_assign': ('mpds-item-confirm.wav', .37),
    'roulette_lock': ('mpds-menu.wav', .49),
    'rules': ('mpds-menu.wav', .31),
    'confirm': ('mpds-menu.wav', .49),
    'game_go': ('mpds-native-start.wav', .66),
    'game_finish': ('mpds-native-finish.wav', .68),
}
GAME_SOUNDS = {
    'drop': (NATIVE + 'food-drop.wav', .51),
    'jump': (NATIVE + 'jump.wav', .30),
    'impact': (NATIVE + 'impact.wav', .57),
    'out': ('../deltarune/fall.wav', .49),
}


def render_audio(film, text_rate):
    mixer = Mixer(film.duration)
    for start, stop, path, gain in (
        (0, film.rules, 'mpds-wiggler.flac', .41),
        (film.rules, film.arena, 'mpds-intro.flac', .37),
        (film.go, film.finish, NATIVE + 'another-crazy-match.flac', .45),
        (film.reveal, film.duration, 'mpds-result.flac', .40),
    ):
        mixer.add('music', start, path, gain, stop - start, fade=.09)

    for event in film.events:
        kind, t = event['type'], event['t']
        pan = PANS.get(event.get('player', event.get('id')), 0)
        if kind == 'die_spin':
            mixer.add('sound', t, 'mpds-dice-spin.wav', .36, event['duration'], fade=.008, pan=pan)
        elif kind == 'roulette_spin':
            mixer.add('sound', t, 'mpds-roulette.wav', .52, film.lock - t, fade=.008)
        elif kind == 'red_coin':
            for index in range(3):
                mixer.add('sound', t + index * .082, 'mpds-coin-contact.wav', .32 - .04 * index,
                          fade=.005, pan=pan)
        elif kind in BOARD_SOUNDS:
            path, gain = BOARD_SOUNDS[kind]
            mixer.add('sound', t, path, gain, fade=.005, pan=pan)
        elif kind in GAME_SOUNDS:
            path, gain = GAME_SOUNDS[kind]
            if kind == 'impact' and event.get('status') == 'sticky':
                path = NATIVE + 'sticky.wav'
            if kind == 'drop':
                pan = event['lane'] * .32
            mixer.add('sound', t, path, gain, fade=.005, pan=pan)
            if kind in ('out', 'impact'):
                mixer.duck(t, t + .24, .73)

    for cue in film.dialogue:
        start, end = cue['start'], cue['end']
        who = cue['speaker']
        if 'voice' in cue:
            mixer.add('voice', start, cue['voice'], .86, end - start, fade=.012, pan=PANS[who] * .6)
            mixer.duck(start, end, .49)
            continue
        blips = [start + index / text_rate for index, char in enumerate(cue['text'])
                 if char.isalnum() and start + index / text_rate < end]
        for index, t in enumerate(blips):
            next_time = blips[index + 1] if index + 1 < len(blips) else t + .085
            mixer.add('voice', t, f'../cast/{who}-text.wav', .87, min(next_time, end) - t,
                      fade=.004, pan=PANS[who] * .6)
        mixer.duck(blips[0], min(blips[-1] + .15, end), .57)

    output = ROOT / 'out/mix.wav'
    mixer.write(output, ROOT / 'qa/mix.json')
    return output
