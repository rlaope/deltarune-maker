"""Shared authored story clock for the multiplication episode."""

TITLE = 'What If Ralsei Kept Multiplying?'
VERSION = 'v3'
FPS = 60
DURATION = 118
TEXT_RATE = 28
INTRO = {'start': .10, 'end': 3.05, 'rate': 30,
         'text': 'What if Ralsei\nkept multiplying?'}
TIMES = {
    'bump': 23.20, 'fall': 23.20, 'recover': 26.80,
    'tenna_enters': 29.65, 'pullback': 38.92,
    'starwalker_enters': 41.5, 'starwalker_leaves': 46.9,
    'chorus': 50.0, 'realization': 54.55,
    'run': 58.2, 'hop': 58.8, 'land': 60.8,
    'stop': 62.1, 'hug': 62.8, 'laugh': 67.8,
    'release': 72.2, 'look_up': 72.4,
    'crowd_reveal': 79.2, 'pressure': 86.3,
    'explosion': 92.0, 'space': 93.6,
    'black_hole': 99.0, 'last_doll': 109.0,
    'starwalker_final': 110.5,
}
DOUBLINGS = tuple({'t': time, 'from': 2 ** index,
                  'to': 2 ** (index + 1), 'duration': .75}
                 for index, time in enumerate((3.5, 8.2, 13, 18.2, 23.3, 36,
                                                41.5, 47, 56.5, 66,
                                                73, 78, 82.5, 86.3, 89.4)))
GROWTH = DOUBLINGS
DIALOGUE = [
    {'start': 3.65, 'end': 6.10, 'speaker': 'ralsei', 'text': 'Oh! There are two of me now.'},
    {'start': 6.25, 'end': 8.00, 'speaker': 'susie', 'text': "Kris. You're counting, right?"},
    {'start': 8.65, 'end': 10.85, 'speaker': 'ralsei', 'text': 'Now we can help four times as much!'},
    {'start': 10.98, 'end': 12.85, 'speaker': 'susie', 'text': 'You lost count at four?'},
    {'start': 13.30, 'end': 15.75, 'speaker': 'queen', 'text': 'Eight Free Assistants. Excellent'},
    {'start': 15.88, 'end': 18.00, 'speaker': 'ralsei', 'text': 'We can bake you a cake!'},
    {'start': 18.50, 'end': 20.70, 'speaker': 'queen', 'text': 'I Only Needed One Spreadsheet'},
    {'start': 20.82, 'end': 22.90, 'speaker': 'susie', 'text': "Kris. Don't encourage them."},
    {'start': 23.35, 'end': 25.20, 'speaker': 'ralsei', 'actor': 'ralsei-5',
     'text': 'S-Sorry! Was that your foot?'},
    {'start': 25.35, 'end': 27.25, 'speaker': 'ralsei', 'actor': 'ralsei-6',
     'text': "They're all my feet!"},
    {'start': 27.40, 'end': 29.60, 'speaker': 'susie',
     'text': "Kris. They're tripping over themselves."},
    {'start': 30.25, 'end': 32.95, 'speaker': 'tenna', 'text': 'THIRTY-TWO GUESTS! ONE LOW FEE!'},
    {'start': 33.08, 'end': 35.30, 'speaker': 'ralsei', 'text': 'Actually, thirty-two fees.'},
    {'start': 36.35, 'end': 38.55, 'speaker': 'tenna', 'text': "I'M PAYING BY THE GOAT?!"},
    {'start': 38.70, 'end': 40.95, 'speaker': 'susie', 'text': "We're just watching, Kris."},
    {'start': 41.88, 'end': 44.18, 'speaker': 'starwalker', 'text': 'These are not the original.'},
    {'start': 44.32, 'end': 46.75, 'speaker': 'queen', 'text': 'Statistically One Of Them Is'},
    {'start': 47.35, 'end': 49.70, 'speaker': 'ralsei', 'text': 'Everyone remembers the plan?'},
    {'start': 50.00, 'end': 51.25, 'speaker': 'ralsei', 'actor': 'ralsei-0', 'chorus': True, 'text': 'Hug Kris!'},
    {'start': 51.40, 'end': 52.65, 'speaker': 'ralsei', 'actor': 'ralsei-5', 'chorus': True, 'text': 'Hug Kris!'},
    {'start': 52.80, 'end': 54.10, 'speaker': 'ralsei', 'actor': 'ralsei-6', 'chorus': True, 'text': 'Hug Kris!'},
    {'start': 54.25, 'end': 56.35, 'speaker': 'susie', 'text': 'They mean YOU, Kris.'},
    {'start': 56.65, 'end': 57.95, 'speaker': 'ralsei', 'chorus': True, 'text': 'Hug Kris!'},
    {'start': 58.60, 'end': 60.90, 'speaker': 'susie', 'text': 'Hey! Watch it, Kris!'},
    {'start': 64.00, 'end': 66.40, 'speaker': 'ralsei', 'text': 'Kris... you found the original?'},
    {'start': 66.55, 'end': 68.95, 'speaker': 'susie', 'text': 'You hugged the first one, Kris.'},
    {'start': 69.10, 'end': 71.30, 'speaker': 'ralsei', 'text': 'That counts as helping, right?'},
    {'start': 71.45, 'end': 73.80, 'speaker': 'susie', 'text': 'Next time, we watch from up there.'},
    {'start': 74.00, 'end': 76.40, 'speaker': 'tenna', 'text': 'SAME TIME TOMORROW?'},
    {'start': 76.55, 'end': 79.20, 'speaker': 'queen', 'text': 'I Am Deleting The Spreadsheet'},
    {'start': 79.35, 'end': 81.65, 'speaker': 'ralsei', 'text': 'I think we need a bigger town.'},
    {'start': 82.00, 'end': 84.45, 'speaker': 'susie', 'text': "Kris. That's not a town anymore."},
    {'start': 84.65, 'end': 85.85, 'speaker': 'ralsei', 'chorus': True, 'text': 'Hug Kris!'},
    {'start': 86.00, 'end': 88.15, 'speaker': 'queen', 'text': 'This Is Becoming A Storage Problem'},
    {'start': 88.30, 'end': 89.55, 'speaker': 'ralsei', 'chorus': True, 'text': 'Hug Kris!'},
    {'start': 96.40, 'end': 98.65, 'speaker': 'ralsei', 'text': 'Can we still help?'},
    {'start': 111.50, 'end': 115.20, 'speaker': 'starwalker',
     'text': 'I am the Original Starwalker.'},
]
EVENTS = [
    {'t': .10, 'type': 'narrator_intro'},
    *[dict(change, type='doubling') for change in DOUBLINGS],
    {'t': 6.85, 'type': 'kris_counts'},
    {'t': 11.45, 'type': 'kris_loses_count'},
    {'t': 11.75, 'type': 'susie_laugh', 'speaker': 'susie'},
    {'t': 12.5, 'type': 'queen_enters'},
    {'t': 16.15, 'type': 'cake_appears'},
    {'t': 20.95, 'type': 'kris_reaches_for_cake'},
    {'t': TIMES['bump'], 'type': 'clone_bump', 'actors': (5, 6)},
    {'t': TIMES['fall'], 'type': 'clone_fall', 'actors': (5,)},
    {'t': TIMES['recover'], 'type': 'clone_recover', 'actors': (5, 6)},
    {'t': TIMES['tenna_enters'], 'type': 'tenna_enters'},
    {'t': TIMES['pullback'], 'type': 'susie_pulls_kris_back'},
    {'t': TIMES['starwalker_enters'], 'type': 'starwalker_enters'},
    {'t': TIMES['starwalker_leaves'], 'type': 'starwalker_leaves'},
    *[{'t': line['start'], 'type': 'hug_chorus'} for line in DIALOGUE if line.get('chorus')],
    {'t': TIMES['realization'], 'type': 'kris_realizes'},
    {'t': TIMES['run'], 'type': 'kris_runs'},
    {'t': TIMES['hop'], 'type': 'susie_jumps_aside'},
    {'t': TIMES['land'], 'type': 'susie_lands'},
    {'t': TIMES['stop'], 'type': 'kris_stops'},
    {'t': TIMES['hug'], 'type': 'hug'},
    {'t': TIMES['laugh'], 'type': 'susie_laugh', 'speaker': 'susie'},
    {'t': TIMES['look_up'], 'type': 'observers_look_up'},
    {'t': TIMES['crowd_reveal'], 'type': 'crowd_reveal'},
    {'t': TIMES['pressure'], 'type': 'crowd_pressure'},
    {'t': TIMES['explosion'], 'type': 'crowd_explosion'},
    {'t': TIMES['space'], 'type': 'space_dolls'},
    {'t': TIMES['black_hole'], 'type': 'black_hole'},
    {'t': TIMES['last_doll'], 'type': 'last_doll_absorbed'},
    {'t': TIMES['starwalker_final'], 'type': 'starwalker_final'},
]


def validate():
    for cue in DIALOGUE:
        typed = (len(cue['text']) - 1) / TEXT_RATE
        if cue['end'] - cue['start'] < typed + .45:
            raise ValueError(f"Dialogue needs a longer reading hold: {cue['text']}")
    if any(a['end'] > b['start'] for a, b in zip(DIALOGUE, DIALOGUE[1:])):
        raise ValueError('Cast dialogue overlaps')
    if DIALOGUE[0]['start'] < INTRO['end'] or DIALOGUE[-1]['end'] > DURATION:
        raise ValueError('Dialogue exceeds the episode boundaries')
