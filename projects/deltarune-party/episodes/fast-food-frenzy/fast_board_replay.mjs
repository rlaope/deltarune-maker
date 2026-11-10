import {createHash} from 'node:crypto';
import {readFile, writeFile} from 'node:fs/promises';

const [output, ...extra] = process.argv.slice(2);
if (extra.length) throw new Error('Usage: node fast_board_replay.mjs [output.json]');
const mapPath = new URL('../../game/boards.mjs', import.meta.url);
const enginePath = new URL('../../game/engine.mjs', import.meta.url);
const {boards} = await import(mapPath);
const {BoardGame} = await import(enginePath);
const board = structuredClone(boards.find(({chapter}) => chapter === 5));
const dinerSpecial = board.spaces.find(({id}) => id === 'diner-012');
dinerSpecial.type = 'event';
dinerSpecial.event = {
  id: 'diner-special-pick', title: 'Diner Special',
  lines: [{speaker: 'flowery', text: 'Pick a menu. No peeking!'}],
  choices: [['left', 'Menu 1', 1], ['middle', 'Menu 2', 8], ['right', 'Menu 3', 20]]
    .map(([id, label, amount]) => ({id, label, effect: {type: 'coins', amount}})),
};
const setup = {seed: 2368, rounds: 1,
  players: ['lancer', 'susie', 'noelle', 'flowery'],
  starts: {
    lancer: 'diner-014', susie: 'diner-005', noelle: 'diner-009', flowery: 'diner-counter',
  }};
const game = new BoardGame(board, setup);
const initial = game.state;
const landings = {};
const selected = 'middle';
for (const player of setup.players) {
  if (game.state.active !== player) throw new Error('The replay turn order changed.');
  const events = game.dispatch({type: 'roll'});
  const landing = events.find(event => event.type === 'land');
  const kind = {lancer: 'blue', susie: 'blue', noelle: 'event', flowery: 'red'}[player];
  if (landing?.kind !== kind) {
    throw new Error(`Unexpected landing for ${player}.`);
  }
  landings[player] = landing.kind;
  if (player === 'noelle') {
    if (landing.space !== dinerSpecial.id || game.state.encounter?.id !== dinerSpecial.event.id) {
      throw new Error('Noelle must stop on the Diner Special space.');
    }
    game.dispatch({type: 'choose', option: selected});
  }
  game.dispatch({type: 'end'});
}
if (game.state.phase !== 'results' || game.state.round !== 1) {
  throw new Error('The single round must be complete before the minigame draw.');
}
const hashes = {};
for (const [name, path] of [['board', mapPath], ['engine', enginePath]]) {
  hashes[name] = createHash('sha256').update(await readFile(path)).digest('hex');
}
const trace = game.trace;
// Mario Party DS rolls an end-of-round colour for a green-space player.
const teamSeed = 1;
const greenRoll = (Math.imul(teamSeed, 1664525) + 1013904223) >>> 0;
const teams = Object.fromEntries(Object.entries(landings).map(([player, kind]) =>
  [player, kind === 'event' ? (greenRoll < 2 ** 31 ? 'blue' : 'red') : kind]));
const event = {
  player: 'noelle', space: dinerSpecial.id, selected, prompt: dinerSpecial.event.lines[0].text,
  options: dinerSpecial.event.choices.map(({id, label, effect}) => ({id, label, coins: effect.amount})),
};
const data = {board, setup, initial, trace, final: game.state, hashes, event, grouping: {teamSeed, teams}};
await writeFile(output ?? new URL('./fast-board-replay.json', import.meta.url), JSON.stringify(data, null, 2) + '\n');
