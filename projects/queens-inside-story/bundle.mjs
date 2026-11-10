import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { assetRoot } from './asset-root.mjs';
import { audioAssets } from './audio.mjs';

const read = path => readFileSync(new URL(path, import.meta.url));
const asset = path => readFileSync(join(assetRoot, path));
const mimes = { png: 'image/png', json: 'application/json', mp3: 'audio/mpeg', wav: 'audio/wav', ogg: 'audio/ogg' };
const images = JSON.parse(asset('dr/images.json')).map(file => `dr/${file}`);
const bisImages = JSON.parse(asset('bis/ui/images.json')).map(file => `bis/ui/${file}`);
const paths = new Set([...images, ...bisImages, 'bis/ui/images.json', 'dr/images.json', 'dr/font.json', ...audioAssets]);
const assets = Object.fromEntries([...paths].map(path => [
  path, `data:${mimes[path.split('.').at(-1)]};base64,${asset(path).toString('base64')}`,
]));
const modules = [
  ['scene', 'encounter'],
  ['engine', 'createGame,step,ACTIONS,FPS,DURATION,BOSS_BURST_AT,visibleLine'],
  ['replay', 'replayInput'],
  ['audio', 'music,cues'],
  ['render', 'render,loadAssets,assetURL'],
  ['app', ''],
].map(([name, exports]) => {
  const source = String(read(`./${name}.mjs`)).replace(/^import .*?;\r?\n/gm, '').replace(/^export /gm, '');
  return exports ? `const {${exports}}=(()=>{\n${source}\nreturn {${exports}};})();` : source;
}).join('\n');
const html = String(read('./index.html')).replace('<script type="module" src="./app.mjs"></script>',
  () => `<script type="module">globalThis.QUEEN_ASSETS=${JSON.stringify(assets)};\n${modules}\n</script>`);
mkdirSync(new URL('./out/', import.meta.url), { recursive: true });
writeFileSync(new URL('./out/queens-inside-story-play.html', import.meta.url), html);
