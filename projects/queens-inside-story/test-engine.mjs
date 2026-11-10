import assert from 'node:assert/strict';
import test from 'node:test';
import { BOSS_BURST_AT, createGame, DURATION, FPS, MAX_HP, QUEEN_HP, step, visibleLine } from './engine.mjs';
import { replayInput } from './replay.mjs';

const dt = 1 / FPS;
const advance = (state, input = {}, seconds = dt) => {
  for (let frame = 0; frame < Math.round(seconds * FPS); frame++) {
    step(state, dt, typeof input === 'function' ? input(state) : input);
  }
  return state;
};

function advanceTo(state, when) {
  for (let frame = 0; frame < DURATION * FPS; frame++) {
    if (when(state)) return state;
    step(state, dt, replayInput(state));
  }
  assert.fail('Replay did not reach the requested phase.');
}

test('play starts on a bounded map and only A near Queen opens the encounter', () => {
  const state = createGame();
  advance(state, { a: true });
  assert.equal(state.scene, 'map');
  advance(state, { left: true, up: true }, 12);
  assert.equal(state.map.x, 28);
  assert.equal(state.map.y, 80);
  advance(state, { right: true }, 7);
  assert.ok(state.map.susieX < state.map.x);
  advance(state, { b: true });
  assert.equal(state.scene, 'map');
  advance(state, { a: true });
  assert.equal(state.scene, 'dialogue');
  assert.equal(state.line.speaker, 'queen');
  assert.equal(visibleLine(state.line), '');
  advance(state, {}, 0.25);
  advance(state, { a: true });
  assert.equal(visibleLine(state.line), state.line.text);
  assert.equal(state.line.speaker, 'queen');
  advance(state, { a: true });
  assert.equal(state.line.speaker, 'susie');
});

test('field hops use independent arcs and emit once per takeoff', () => {
  const state = createGame();
  advance(state, { a: true });
  advance(state, { a: true, b: true });
  assert.ok(state.map.jumps[0] > state.map.jumps[1]);
  assert.ok(state.map.jumps[1] > 0);
  assert.deepEqual(state.events.filter(e => e.mode === 'field').map(e => e.target), [0, 1]);
  advance(state, {}, 0.27);
  assert.ok(state.map.jumps[0] > 39, 'the field hop reaches approximately 40 px');
  advance(state, {}, 0.40);
  assert.deepEqual(state.map.jumps, [0, 0]);
});

test('only a rising hop under the block grants one Mushroom on the same frame', () => {
  const state = createGame();
  advance(state, { right: true }, 0.52);
  advance(state, { right: true, a: true });
  advance(state, { right: true }, 0.56);
  assert.equal(state.map.block.used, false, 'the descending hop passes the block');
  advance(state, {}, 0.10);
  advance(state, { a: true });
  advanceTo(state, s => s.map.block.used);
  assert.ok(state.map.block.bump > 0);
  assert.equal(state.inventory.mushrooms, 1);
  assert.deepEqual(state.map.pickup, { x: 157, y: 210, target: 0, age: 0 });
  assert.equal(Object.hasOwn(state.map, 'mushroom'), false);
  const bump = state.events.find(e => e.type === 'fieldBlock');
  const reward = state.events.find(e => e.type === 'fieldPickup');
  assert.equal(reward.t, bump.t);

  advance(state, { left: true }, 0.78);
  assert.equal(state.inventory.mushrooms, 1);
  assert.equal(state.map.pickup, null);
  assert.equal(state.line.speaker, 'susie');
  assert.equal(state.map.moving, true);
  advance(state, { right: true }, 0.78);
  advance(state, { a: true });
  advance(state, {}, 0.68);
  assert.equal(state.events.filter(e => e.type === 'fieldBlock').length, 1);
  assert.equal(state.events.filter(e => e.type === 'fieldPickup').length, 1);
});

test('skipping the field pickup leaves the battle Item inventory empty', () => {
  const state = advance(createGame(), s => {
    const input = replayInput(s);
    if (s.scene === 'map' && !s.map.switch.on) return { ...input, a: false, b: false };
    return input;
  }, 17);
  assert.equal(state.scene, 'battle');
  assert.equal(state.map.block.used, false);
  assert.equal(state.inventory.mushrooms, 0);
  assert.equal(state.battle.items, 0);
  assert.equal(state.map.switch.on, true);
  assert.equal(state.events.filter(e => e.type === 'fieldPower').length, 1);
});

test('a B jump cannot protect Kris from an incoming A-lane projectile', () => {
  const state = advanceTo(createGame(), s => s.scene === 'battle');
  advanceTo(state, s => replayInput(s).a === true);
  advance(state, { b: true });
  assert.equal(state.battle.jumps[0], 0);
  assert.ok(state.battle.jumps[1] > 0);
  advance(state, {}, 0.40);
  assert.equal(state.battle.hp[0], MAX_HP[0] - 6);
  assert.equal(state.battle.hp[1], MAX_HP[1]);
  assert.ok(state.events.some(e => e.type === 'hit' && e.target === 0));
});

test('only the active hero steps forward on command entry and Jump starts from there', () => {
  const state = advanceTo(createGame(), s => s.battle?.phase === 'command');
  const [kris, susie] = state.battle.players;
  const start = kris.x;
  const partner = { ...susie };
  advance(state, {}, 0.10);
  assert.ok(kris.x > start && kris.x < start + 13);
  assert.deepEqual(susie, partner);
  advance(state, {}, 0.14);
  assert.equal(kris.x, start + 13);
  assert.equal(kris.step, null);
  advance(state, { a: true });
  advance(state, {}, 0.36);
  assert.equal(kris.x, start + 13);
  advance(state, { a: true });
  assert.equal(state.battle.stomp.startX, kris.x);
  advance(state, {});
  assert.ok(kris.x > start + 13);
});

test('the command accepts a fast confirmation during the step without snapping forward', () => {
  const state = advanceTo(createGame(), s => s.battle?.phase === 'command');
  const kris = state.battle.players[0];
  const start = kris.x;
  advance(state, { a: true });
  assert.equal(state.battle.phase, 'bump');
  assert.ok(kris.x >= start && kris.x < start + 2);
  const settled = kris.x;
  advance(state, {}, 0.36);
  assert.equal(kris.x, settled);
  advance(state, { a: true });
  assert.equal(state.battle.stomp.startX, settled);
});

test('the command bump and target confirmation precede a held and released Hammer strike', () => {
  const state = advanceTo(createGame(), s => s.battle?.phase === 'command');
  advance(state, { right: true }, 0.20);
  assert.equal(state.battle.command, 'hammer');
  assert.equal(state.events.filter(e => e.type === 'select').length, 1);
  advance(state, { b: true });
  assert.equal(state.battle.phase, 'command');
  advance(state, { a: true });
  assert.equal(state.battle.phase, 'bump');
  advance(state, {}, 0.20);
  assert.ok(state.battle.jumps[0] > 30);
  assert.equal(state.events.filter(e => e.mode === 'menu').length, 1);
  assert.equal(state.events.filter(e => e.type === 'blockHit').length, 1);
  advance(state, {}, 0.16);
  assert.equal(state.battle.phase, 'target');
  assert.equal(state.battle.stomp, null);
  advance(state, { b: true });
  assert.equal(state.battle.phase, 'target');
  advance(state, { a: true });
  assert.equal(state.battle.stomp.kind, 'hammer');
  assert.equal(state.battle.stomp.startX, state.battle.players[0].x);
  advance(state, {}, 0.85);
  assert.equal(state.battle.jumps[0], 0);
  assert.ok(state.battle.players[0].x > 240);
  advance(state, { aHeld: true }, 0.57);
  assert.equal(state.battle.stomp.pose, 'charge');
  assert.equal(state.battle.stomp.charged, true);
  assert.equal(state.battle.qhp, QUEEN_HP);
  advance(state, {});
  assert.equal(state.battle.stomp.pose, 'swing');
  assert.equal(state.events.find(e => e.type === 'release').timed, true);
  advance(state, {}, 0.12);
  assert.equal(state.battle.stomp.stage, 'return');
  assert.equal(state.battle.qhp, QUEEN_HP - 27);
  assert.equal(state.battle.feedback[0].text, 'EXCELLENT!');
  assert.equal(state.battle.stomp.pose, 'follow');
  const planted = { ...state.battle.players[0] };
  advance(state, {}, 0.19);
  assert.deepEqual(state.battle.players[0], planted);
  assert.equal(state.battle.players[0].face, 'right');
  advance(state, {}, 0.08);
  assert.equal(state.battle.stomp.pose, 'recover');
  assert.equal(state.battle.players[0].face, 'left');
  assert.ok(state.battle.players[0].x < planted.x);
});

test('Item heals the selected injured hero, spends the Mushroom, and advances the turn', () => {
  const state = advanceTo(createGame(), s => s.scene === 'battle');
  advanceTo(state, s => replayInput(s).b === true);
  advance(state, {}, 0.40);
  assert.equal(state.battle.hp[1], MAX_HP[1] - 6);
  advanceTo(state, s => s.battle.phase === 'command');
  advance(state, { left: true });
  advance(state);
  advance(state, { left: true });
  assert.equal(state.battle.command, 'item');
  advance(state, { a: true });
  advance(state, {}, 0.36);
  assert.equal(state.battle.phase, 'item');
  assert.equal(state.battle.itemTarget, 0);
  advance(state, { right: true });
  assert.equal(state.battle.itemTarget, 1);
  advance(state, { a: true });
  assert.equal(state.battle.items, 0);
  assert.equal(state.inventory.mushrooms, 0);
  assert.equal(state.battle.hp[1], MAX_HP[1]);
  assert.equal(state.battle.phase, 'command');
  assert.equal(state.battle.turn, 1);
  const [kris, susie] = state.battle.players;
  assert.ok(kris.step.toX < kris.x);
  assert.ok(susie.step.toX > susie.x);
  advance(state, {}, 0.24);
  assert.equal(kris.x, 83);
  assert.equal(susie.x, 126);
});

test('Flee can be canceled, and confirming it explains why the exit is blocked', () => {
  const state = advanceTo(createGame(), s => s.battle?.phase === 'command');
  advance(state, { left: true, a: true });
  advance(state, {}, 0.36);
  assert.equal(state.battle.phase, 'flee');
  advance(state, { cancel: true });
  assert.equal(state.battle.phase, 'command');
  assert.equal(state.battle.command, 'flee');
  advance(state, { a: true });
  advance(state, {}, 0.36);
  advance(state, { a: true });
  assert.equal(state.battle.phase, 'notice');
  assert.equal(state.battle.notice, 'THE EXIT IS LOCKED.');
  advance(state, {}, 1.36);
  assert.equal(state.battle.phase, 'command');
  assert.equal(state.battle.items, 1);
  assert.equal(state.battle.turn, 0);
});

test('a GOOD jump rebounds and needs its own correctly timed input for EXCELLENT', () => {
  const state = advanceTo(createGame(), s => s.battle?.stomp?.stage === 'rebound');
  assert.equal(state.battle.feedback[0].text, 'GOOD!');
  assert.equal(state.battle.qhp, QUEEN_HP - 13);
  advance(state, {}, 0.58);
  assert.equal(state.battle.feedback[0].text, 'MISS');
  assert.equal(state.battle.qhp, QUEEN_HP - 16);
  assert.ok(!state.events.some(e => e.type === 'excellent'));
});

test('the early attack tap lands a basic stomp and cannot grant a bonus rebound', () => {
  const state = advanceTo(createGame(), s => s.battle?.phase === 'stomp');
  advance(state, {}, 0.50);
  advance(state, { a: true });
  assert.equal(state.battle.feedback[0].text, 'EARLY');
  advance(state, {}, 1.45);
  assert.equal(state.battle.phase, 'command');
  assert.equal(state.battle.turn, 1);
  assert.equal(state.battle.qhp, QUEEN_HP - 13);
  assert.ok(!state.events.some(e => e.type === 'excellent'));
});

test('the replay lands two timed sword combos, one held axe strike, and the missed dodge', () => {
  const state = advance(createGame(), replayInput, DURATION);
  assert.equal(state.scene, 'end');
  assert.equal(state.result, 'win');
  assert.equal(state.battle.qhp, 0);
  assert.equal(state.battle.items, 1);
  assert.deepEqual(state.battle.hp, [42, 40]);
  assert.equal(state.events.filter(e => e.type === 'fieldPickup').length, 1);
  assert.deepEqual(state.events.filter(e => e.type === 'line' && e.scene === 'map').map(e => e.text),
    ['Dibs. Unless it grows legs.', 'Kris. That opened something.']);
  assert.deepEqual(state.events.filter(e => e.type === 'line' && e.scene === 'dialogue').map(e => e.speaker),
    ['queen', 'susie', 'queen', 'susie']);
  const entrance = state.events.find(e => e.type === 'line' && e.scene === 'transition');
  assert.equal(entrance.text, "Let's go!");
  assert.equal(entrance.t, state.events.find(e => e.type === 'transition').t);
  assert.equal(state.events.find(e => e.type === 'battle').t.toFixed(2), '16.67');
  const win = state.events.find(e => e.type === 'win');
  const bursts = state.events.filter(e => e.type === 'bossBurst');
  assert.equal(bursts.length, 1);
  assert.ok(Math.abs(bursts[0].t - win.t - BOSS_BURST_AT) <= dt);
  const lastLine = state.events.filter(e => e.type === 'line').at(-1);
  assert.equal(lastLine.text, 'I Have Opted Out Of My Own Test.');
  assert.ok(lastLine.t > bursts[0].t);
  const hits = state.events.filter(e => e.type === 'hit');
  assert.equal(hits.length, 1);
  assert.equal(hits[0].target, 1);
  assert.equal(hits[0].damage, 8);
  assert.equal(hits[0].height, 0);
  assert.equal(state.events.filter(e => e.type === 'dodge' && e.target !== undefined).length, 16);
  const timed = state.events.filter(e => e.type === 'excellent');
  assert.deepEqual(timed.map(e => [e.target, e.weapon]), [[0, 'sword'], [1, 'axe'], [0, 'sword']]);
  assert.deepEqual(state.events.filter(e => e.grade === 'GOOD!').map(e => e.target), [0, 0]);
  assert.deepEqual(state.events.filter(e => e.type === 'target').map(e => e.command),
    ['jump', 'hammer', 'jump']);
  assert.deepEqual(state.events.filter(e => e.type === 'select').map(e => e.command),
    ['flee', 'item', 'hammer', 'jump', 'hammer']);
  assert.deepEqual(state.events.filter(e => e.type === 'select').map(e => e.direction), [-1, -1, -1, -1, 1]);
  assert.deepEqual(state.events.filter(e => e.mode === 'field').map(e => e.target), [0, 1, 0, 1]);
  assert.equal(state.events.filter(e => e.mode === 'menu').length, 3);
  assert.equal(state.events.filter(e => e.mode === 'bonus').length, 2);
  const simultaneous = state.events.some((e, i, events) =>
    e.type === 'jump' && e.mode === 'dodge' && e.target === 0
    && events[i + 1]?.target === 1 && events[i + 1]?.type === 'jump' && events[i + 1]?.t === e.t);
  assert.equal(simultaneous, true);
});

test('skipping defense loses the encounter once a hero reaches zero health', () => {
  const state = advance(createGame(), s => s.battle?.phase === 'dodge' ? {} : replayInput(s), DURATION);
  assert.equal(state.scene, 'end');
  assert.equal(state.result, 'loss');
  assert.ok(state.battle.hp.includes(0));
});
