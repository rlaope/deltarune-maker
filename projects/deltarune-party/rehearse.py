"""Render a board reward, cast exchange, and next turn using the shared modules."""

import argparse
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True,
                        help='new directory for the check video, stills, and receipts')
    args = parser.parse_args()
    workspace = args.workspace.expanduser().resolve()
    if not (workspace / 'assets/boards/chapter-5/second-diner.png').is_file():
        parser.error('Use a Fast Food Frenzy workspace containing the original diner assets')
    output = args.output.expanduser().resolve()
    if output.exists():
        parser.error('Choose a new output directory to keep earlier check results')
    output.mkdir(parents=True)

    os.environ['DELTARUNE_PARTY_WORKSPACE'] = str(workspace)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(__file__).resolve().parent / 'template'))
    from party_rehearsal import Rehearsal

    Rehearsal().render_check(output)


if __name__ == '__main__':
    main()
