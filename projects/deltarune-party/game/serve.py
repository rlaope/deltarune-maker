"""Serve Deltarune Party and its private asset workspace on loopback."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
import webbrowser


GAME = Path(__file__).resolve().parent
GAME_SUFFIXES = {'.css', '.html', '.mjs'}
ASSET_SUFFIXES = {'.flac', '.json', '.mp3', '.ogg', '.png', '.wav', '.webp'}


class GameHandler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, '.mjs': 'text/javascript'}

    def __init__(self, *args, assets, **kwargs):
        self.assets = assets
        super().__init__(*args, directory=GAME, **kwargs)

    def translate_path(self, path):
        url_path = unquote(urlsplit(path).path)
        root, suffixes = GAME, GAME_SUFFIXES
        if url_path.startswith('/assets/'):
            root, suffixes = self.assets, ASSET_SUFFIXES
            url_path = url_path.removeprefix('/assets/')
        elif url_path == '/':
            url_path = '/index.html'
        candidate = (root / url_path.lstrip('/')).resolve()
        if candidate.is_relative_to(root) and candidate.suffix in suffixes:
            return str(candidate)
        return str(GAME / '.unavailable')

    def list_directory(self, path):
        self.send_error(404)
        return None

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'")
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True,
                        help='private game workspace containing assets/')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--open', action='store_true', help='open the local game in a browser')
    args = parser.parse_args()
    assets = (args.workspace.expanduser() / 'assets').resolve()
    if not assets.is_dir():
        parser.error(f'Asset directory does not exist: {assets}')

    handler = partial(GameHandler, assets=assets)
    with ThreadingHTTPServer(('127.0.0.1', args.port), handler) as server:
        url = f'http://127.0.0.1:{server.server_port}/'
        print(url, flush=True)
        if args.open:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
