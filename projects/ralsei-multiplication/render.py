"""Run the multiplication film using prepared original assets in a private workspace."""
import argparse
import importlib
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parent
MANIFESTS = ('native.json', 'extras.json', 'observers.json', 'staging-v3.json',
             'voices-v3.json', 'town/town.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--prepare-from', type=Path,
                        help='link assets from an existing private production workspace')
    wrapper = sys.argv[1:]
    forwarded = []
    if '--' in wrapper:
        split = wrapper.index('--')
        forwarded, wrapper = wrapper[split + 1:], wrapper[:split]
    args = parser.parse_args(wrapper)
    workspace = args.workspace.expanduser().resolve()
    repository = PROJECT.parents[1]
    if repository == workspace or repository in workspace.parents:
        parser.error('Keep the asset/output workspace outside this public repository')
    if args.prepare_from:
        assets = args.prepare_from.expanduser().resolve() / 'assets'
        if repository == assets or repository in assets.parents:
            parser.error('Prepared original assets must remain outside this public repository')
        if not assets.is_dir():
            parser.error(f'Prepared source assets are missing: {assets}')
        workspace.mkdir(parents=True, exist_ok=True)
        target = workspace / 'assets'
        if target.exists() or target.is_symlink():
            if target.resolve() != assets:
                parser.error('Workspace assets already exist; no files were overwritten')
        else:
            target.symlink_to(assets, target_is_directory=True)
    runtime_assets = (workspace / 'assets').resolve()
    if repository == runtime_assets or repository in runtime_assets.parents:
        parser.error('Runtime original assets must remain outside this public repository')
    missing = [name for name in MANIFESTS if not (workspace / 'assets' / name).is_file()]
    if missing:
        parser.error('Missing private runtime manifests: ' + ', '.join(missing))
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(PROJECT / 'source'))
    # The unchanged production modules resolve assets/output against ROOT.
    # Override it in memory; never copy source into or edit the private workspace.
    for name in ('visual', 'audio', 'render'):
        module = importlib.import_module(name)
        module.ROOT = workspace
    sys.argv = [str(PROJECT / 'source/render.py'), *forwarded]
    # Production export hashing expects the same six files under ROOT. Supply
    # read-only source links only when absent, without replacing local versions.
    if not any(option == '--stills' for option in forwarded):
        for name in ('story.py', 'crowd.py', 'visual.py', 'cosmic.py', 'audio.py', 'render.py'):
            target = workspace / name
            original = PROJECT / 'source' / name
            if target.exists():
                if target.read_bytes() != original.read_bytes():
                    parser.error(f'Workspace source differs: {name}; use a fresh workspace')
            else:
                target.symlink_to(original)
    importlib.import_module('render').main()


if __name__ == '__main__':
    main()
