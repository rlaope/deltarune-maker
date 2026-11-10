"""Run a studio episode with its original assets in a private workspace."""

import argparse
import os
from pathlib import Path
import runpy
import sys


PROJECT = Path(__file__).resolve().parent
SHARED_ASSETS = (
    'assets/deltarune/font.json',
    'assets/deltarune/font.png',
    'assets/mpds/font.json',
    'assets/mpds/font.png',
    'assets/mpds/raw/minigame-menu.png',
)
EPISODES = {
    'boo-tag': {
        'film': 'boo_film.py',
        'assets': (
            'assets/board/courtyard.png',
            'assets/cast/ralsei-down-0.png',
            'assets/boo-native/boo-rules.png',
            'assets/mpds/item-double-card.png',
            'assets/mpds/double-dice-roll/01.png',
        ),
    },
    'soap-surfers': {
        'film': 'soap_film.py',
        'mix': 'mix_soap.py',
        'assets': (
            'assets/chapter5/board.png',
            'assets/mpds/soap/sink.png',
        ),
    },
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('episode', choices=EPISODES)
    parser.add_argument('--workspace', type=Path, required=True,
                        help='existing private asset and output directory')
    parser.add_argument('--mix-only', action='store_true',
                        help='run the episode’s standalone audio mixer, if available')
    parser.epilog = 'Pass episode options after --, for example -- --stills 0 10 25.'
    wrapper_args = sys.argv[1:]
    forwarded = []
    if '--' in wrapper_args:
        delimiter = wrapper_args.index('--')
        forwarded = wrapper_args[delimiter + 1:]
        wrapper_args = wrapper_args[:delimiter]
    args = parser.parse_args(wrapper_args)
    episode = EPISODES[args.episode]
    entry = episode.get('mix') if args.mix_only else episode['film']
    if args.mix_only and (not entry or forwarded):
        parser.error('--mix-only needs an episode with a standalone mixer and takes no episode options')

    workspace = args.workspace.expanduser().resolve()
    if not workspace.is_dir():
        parser.error(f'Workspace directory does not exist: {workspace}')
    missing = [path for path in (*SHARED_ASSETS, *episode.get('assets', ()))
               if not (workspace / path).is_file()]
    if missing:
        parser.error(f'Missing assets in {workspace}: {", ".join(missing)}')

    source = PROJECT / 'episodes' / args.episode
    script = source / entry
    os.environ['DELTARUNE_PARTY_WORKSPACE'] = str(workspace)
    os.chdir(workspace)
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(PROJECT / 'template'), str(source)]
    sys.argv = [str(script), *forwarded]
    runpy.run_path(str(script), run_name='__main__')


if __name__ == '__main__':
    main()
