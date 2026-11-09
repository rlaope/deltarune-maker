"""Compare downloaded showcase videos with the original release files."""

import argparse
import hashlib
import json
from pathlib import Path


CATALOG = Path(__file__).resolve().parents[1] / "examples" / "catalog.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("download_directory", type=Path)
    args = parser.parse_args()
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    failed = False

    for project in catalog["projects"]:
        for video in project["videos"]:
            path = args.download_directory / video["asset"]
            try:
                with path.open("rb") as source:
                    digest = hashlib.sha256()
                    size = 0
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(chunk)
                        size += len(chunk)
            except OSError as error:
                print(f"FAIL {path.name} ({error.strerror})")
                failed = True
                continue

            if size != video["bytes"] or digest.hexdigest() != video["sha256"]:
                print(f"FAIL {path.name} (file differs from the original)")
                failed = True
            else:
                print(f"OK   {path.name}")

    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
