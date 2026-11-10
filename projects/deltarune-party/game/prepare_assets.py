"""Prepare private art for the playable boards from retained original game images."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
from shutil import copyfile
from urllib.parse import quote
from urllib.request import Request, urlopen

from PIL import Image


WIKI = 'https://deltarune.wiki'
ROOMS = (
    {
        'field': 'Field location card suit puzzle.png',
        'great-board': 'Great Board location 2.png',
        'card-castle': 'Card Castle location.png',
        'forest': 'Forest location Entrance.png',
        'bake-sale': 'Bake Sale location.png',
        'prison': 'Card Castle location Prison.png',
    },
    {
        'cyber-field': 'Cyber Field location.png',
        'coaster': 'Cyber Field location roller coaster.png',
        'mansion': "Queen's Mansion location platter room.png",
        'trash-zone': 'Trash Zone location.png',
        'cyber-city': 'Cyber City location traffic lights.png',
        'acid-tunnel': 'Queen statue sinking in acid screenshot.png',
    },
    {
        'green-room': 'Green Room location.png',
        'desert-board': 'Desert Board map.png',
        'island-board': 'Island Board map.png',
        'cold-place': 'Cold Place location parental lock puzzle.png',
        'couch-cliffs': 'Couch cliffs location.png',
        'tv-studio': 'TV World location Shadowguy crossroads.png',
    },
    {
        'dark-sanctuary': 'Dark Sanctuary location Atrium.png',
        'gold-piano': 'Dark Sanctuary location golden piano.png',
        'second-sanctuary': '2nd Sanctuary location.png',
        'library': 'Dark Sanctuary location Library.png',
        'bell-hall': 'Dark Sanctuary location East Belltower base.png',
        'third-sanctuary': '3rd Sanctuary location Stairs.png',
    },
    {
        'garden': 'Garden location.png',
        'cliffs': 'Cliffs location Below Castle.png',
        'floral-castle': 'Flower Castle location.png',
        'shrine': 'Garden location locked door.png',
        'second-diner': 'Garden location Ideal Diner.png',
        'castle-roof': 'Top of Castle location.png',
    },
)
ROOM_CROPS = {
    (3, 'desert-board'): (460, 1510, 1490, 2280),
    (3, 'island-board'): (850, 2350, 3250, 4150),
}


def room_asset(workspace, offline, entry):
    chapter, region, filename = entry
    key = f'chapter-{chapter}/{region}.png'
    raw = workspace / 'sources/deltarune' / f'chapter-{chapter}' / filename
    asset = workspace / 'assets/boards' / key
    encoded = quote(filename.replace(' ', '_'))
    source_url = f'{WIKI}/images/{encoded}'
    raw.parent.mkdir(parents=True, exist_ok=True)
    if not raw.exists():
        if offline:
            raise FileNotFoundError(raw)
        request = Request(source_url, headers={'User-Agent': 'DeltaruneParty local fan game asset study'})
        with urlopen(request, timeout=20) as response:
            data = response.read()
        temporary = raw.with_suffix('.download')
        temporary.write_bytes(data)
        try:
            with Image.open(temporary) as source:
                source.verify()
            temporary.replace(raw)
        finally:
            temporary.unlink(missing_ok=True)
    crop = ROOM_CROPS.get((chapter, region))
    asset.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(raw) as source:
        if source.format != 'PNG':
            raise ValueError(f'Expected an original PNG at {raw}')
        dimensions = source.size
        if crop:
            source.crop(crop).save(asset)
    if crop is None:
        copyfile(raw, asset)
    return {
        'asset': str(asset.relative_to(workspace)),
        'original': str(raw.relative_to(workspace)),
        'source': f'{WIKI}/w/File:{encoded}',
        'image': source_url,
        'dimensions': dimensions,
        'sha256': sha256(raw.read_bytes()).hexdigest(),
        'crop': crop,
        'asset_sha256': sha256(asset.read_bytes()).hexdigest(),
    }


def copy_shared(workspace, shared):
    patterns = {
        'cast': ('*.png', '*.wav', 'PROVENANCE.md'),
        'deltarune': ('font.png', 'font.json', 'PROVENANCE.md'),
        'mpds': ('*.png', 'font.json', 'PROVENANCE.md', 'double-dice-roll/*.png'),
        'audio': ('mpds-*.wav', 'mpds-wiggler.flac', '*sources.json', '*captures.json'),
    }
    copied = {}
    for folder, globs in patterns.items():
        original = shared / folder
        target = workspace / 'assets' / folder
        for pattern in globs:
            for source in sorted(original.glob(pattern)):
                destination = target / source.relative_to(original)
                destination.parent.mkdir(parents=True, exist_ok=True)
                if source.resolve() != destination.resolve():
                    copyfile(source, destination)
                copied[str(destination.relative_to(workspace))] = sha256(destination.read_bytes()).hexdigest()
    return copied


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--shared-assets', type=Path,
                        help='existing private Mario Party DS and DELTARUNE asset directory')
    parser.add_argument('--offline', action='store_true', help='use only retained source images')
    args = parser.parse_args()
    workspace = args.workspace.expanduser().resolve()
    if args.shared_assets is not None:
        shared = args.shared_assets.expanduser().resolve()
        if not all((shared / directory).is_dir() for directory in ('cast', 'deltarune', 'mpds', 'audio')):
            parser.error('--shared-assets must contain cast/, deltarune/, mpds/ and audio/')
        shared_receipt = copy_shared(workspace, shared)
    else:
        shared_receipt = {}
    entries = [(chapter, region, filename)
               for chapter, regions in enumerate(ROOMS, start=1)
               for region, filename in regions.items()]
    with ThreadPoolExecutor(max_workers=6) as workers:
        receipts = list(workers.map(lambda entry: room_asset(workspace, args.offline, entry), entries))
    receipt = {
        'game_art': 'DELTARUNE by Toby Fox and team; location image captures hosted by The Deltarune Wiki',
        'regions': receipts,
        'shared_assets': shared_receipt,
    }
    (workspace / 'sources/board-assets.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(f'Prepared {len(receipts)} original regions and {len(shared_receipt)} shared assets in {workspace}')


if __name__ == '__main__':
    main()
