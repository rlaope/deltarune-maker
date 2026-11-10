import { encounter } from './scene.mjs';

export const FPS = 60;
export const DURATION = encounter.duration;
export const ACTIONS = ['a', 'b'];
export const COMMANDS = ['jump', 'hammer', 'item', 'flee'];
export const MAX_HP = encounter.battle.hp;
export const QUEEN_HP = encounter.battle.queenHp;
export const BOSS_BURST_AT = 1.95;

const START = encounter.battle.starts;
const QUEEN = encounter.battle.queen;
const WALK_SPEED = 76;
const MAP_WIDTH = 640;
const MAP_HEIGHT = 300;
const FOLLOW_FRAMES = 25;
const JUMP_LENGTH = 0.62;
const JUMP_HEIGHT = 48;
const FIELD_JUMP_LENGTH = 0.64;
const FIELD_JUMP_HEIGHT = 40;
const BUMP_LENGTH = 0.34;
const BUMP_HEIGHT = 36;
const ITEM_HEAL = 12;
const BLOCK_BUMP_LENGTH = 0.25;
const FIELD_REWARD_LENGTH = 0.72;
const COMMAND_STEP_LENGTH = 13;
const COMMAND_STEP_TIME = 0.21;
const FIELD_LINE_LENGTH = 2.40;
const AIR_DODGE_HEIGHT = 22;
const TELL_LENGTH = encounter.battle.tellDuration;
const FIRST_STOMP = 0.97;
const REBOUND = 0.56;
const RETURN = 0.86;
const HIT_WINDOW = 0.15;
const REBOUND_WINDOW = 0.11;
const HAMMER_CONTACT = 1.54;
const HAMMER_SWING = 0.116;
const HAMMER_CHARGE_START = 0.73;
const HAMMER_CHARGE_MIN = 0.27;
const HAMMER_FOLLOW = 0.21;
const HAMMER_REACH = QUEEN.x - 32;
const SWORD_REACH = QUEEN.x - 18;
const EPSILON = 0.00001;

const clip = (n, lo, hi) => Math.max(lo, Math.min(n, hi));
const mix = (a, b, u) => a + (b - a) * u;
const ease = u => u * u * (3 - 2 * u);
const arc = (u, h) => 4 * u * (1 - u) * h;
const crossed = (before, after, value) =>
  before < value - EPSILON && after >= value - EPSILON;

function event(state, type, props = {}) {
  state.events.push({ t: state.t, type, ...props });
}

export function createGame() {
  const face = 'right';
  const { kris, susie, queen, block, switch: powerSwitch } = encounter.field;
  return {
    t: 0, scene: 'map', clock: 0, line: null, dialogueIndex: 0,
    inventory: { mushrooms: 0 },
    map: {
      ...kris, face, moving: false, queenX: queen.x, queenY: queen.y,
      susieX: susie.x, susieY: susie.y, susieFace: face, susieMoving: false,
      jumps: [0, 0], jumpTime: [null, null], press: [0, 0],
      block: { ...block, used: false, bump: 0 },
      pickup: null, reactionPending: false,
      switch: { ...powerSwitch, on: false },
      trail: Array.from({ length: FOLLOW_FRAMES }, () =>
        ({ ...susie, face, moving: false })),
    },
    battle: null, result: null, events: [],
  };
}

function scene(state, name) {
  state.scene = name;
  state.clock = 0;
  event(state, name);
}

function dialogue(state, line) {
  state.line = { ...line, age: 0, reveal: false };
  event(state, 'line', { ...line, scene: state.scene });
}

export function visibleLine(line) {
  if (!line) return '';
  const rate = line.speaker === 'queen' ? 30 : 32;
  return line.reveal ? line.text : line.text.slice(0, Math.floor((line.age + EPSILON) * rate));
}

function fieldPosition(map, target) {
  return target === 0 ? [map.x, map.y] : [map.susieX, map.susieY];
}

function updateFieldBlock(state, dt) {
  const { map } = state;
  const { block } = map;
  block.bump = Math.max(0, block.bump - dt);
  if (block.used) return;
  for (const target of [0, 1]) {
    const [x, y] = fieldPosition(map, target);
    const jumpTime = map.jumpTime[target];
    const rising = jumpTime !== null && jumpTime <= FIELD_JUMP_LENGTH / 2 + EPSILON;
    const belowBlock = Math.abs(x - block.x) <= 13 && Math.abs(y - block.y) <= 11;
    if (!rising || !belowBlock || map.jumps[target] < 22) continue;
    block.used = true;
    block.bump = BLOCK_BUMP_LENGTH;
    state.inventory.mushrooms++;
    map.pickup = { x: block.x, y: block.y, target, age: 0 };
    map.reactionPending = true;
    event(state, 'fieldBlock', { target, x: block.x, y: block.y });
    event(state, 'fieldPickup', { target, x: block.x, y: block.y, item: 'mushroom' });
    return;
  }
}

function updateFieldEvents(state, dt) {
  const { map } = state;
  if (state.line?.age >= FIELD_LINE_LENGTH) state.line = null;
  if (map.pickup) {
    map.pickup.age += dt;
    if (map.pickup.age > FIELD_REWARD_LENGTH) map.pickup = null;
  }
  updateFieldBlock(state, dt);
  if (map.reactionPending && map.moving && !map.pickup) {
    dialogue(state, encounter.dialogue.fieldReward);
    map.reactionPending = false;
  }
  const pressure = map.switch;
  if (!pressure.on && map.jumps[0] <= 5 && Math.hypot(map.x - pressure.x, map.y - pressure.y) <= 14) {
    pressure.on = true;
    event(state, 'fieldPower', { target: 0, x: pressure.x, y: pressure.y });
    dialogue(state, encounter.dialogue.power);
  }
}

function updateMap(state, dt, input) {
  const map = state.map;
  const dx = Number(!!input.right) - Number(!!input.left);
  const dy = Number(!!input.down) - Number(!!input.up);
  const length = Math.hypot(dx, dy);
  const x = map.x;
  const y = map.y;
  if (length) {
    map.x = clip(x + dt * WALK_SPEED * dx / length, 28, MAP_WIDTH - 28);
    map.y = clip(y + dt * WALK_SPEED * dy / length, 80, MAP_HEIGHT - 44);
    map.face = dx ? (dx > 0 ? 'right' : 'left') : (dy > 0 ? 'down' : 'up');
  }
  map.moving = x !== map.x || y !== map.y;
  map.trail.push({ x: map.x, y: map.y, face: map.face, moving: map.moving });
  const followed = map.trail.shift();
  const distance = Math.hypot(map.x - followed.x, map.y - followed.y);
  if (distance > 26 || map.moving) {
    map.susieX = followed.x;
    map.susieY = followed.y;
    map.susieFace = followed.face;
    map.susieMoving = followed.moving;
  } else {
    map.susieMoving = false;
  }
  if (input.a && Math.hypot(map.x - map.queenX, map.y - map.queenY) <= 85) {
    map.moving = false;
    map.susieMoving = false;
    map.face = map.x < map.queenX ? 'right' : 'left';
    map.susieFace = map.face;
    scene(state, 'dialogue');
    event(state, 'gate');
    dialogue(state, encounter.dialogue.meeting[0]);
    map.jumps.fill(0);
    map.jumpTime.fill(null);
    return;
  }
  for (const target of [0, 1]) {
    map.press[target] = Math.max(0, map.press[target] - dt);
    if (input[ACTIONS[target]]) {
      map.press[target] = 0.20;
      if (map.jumpTime[target] === null) {
        map.jumpTime[target] = 0;
        event(state, 'jump', { target, mode: 'field' });
      }
    }
    if (map.jumpTime[target] === null) continue;
    map.jumpTime[target] += dt;
    const u = clip(map.jumpTime[target] / FIELD_JUMP_LENGTH, 0, 1);
    map.jumps[target] = arc(u, FIELD_JUMP_HEIGHT);
    if (u === 1) map.jumpTime[target] = null;
  }
  updateFieldEvents(state, dt);
}

function updateDialogue(state, input) {
  if (!input.a || state.line.age < 0.15) return;
  if (visibleLine(state.line).length < state.line.text.length) {
    state.line.reveal = true;
    return;
  }
  state.dialogueIndex++;
  if (state.dialogueIndex < encounter.dialogue.meeting.length) {
    dialogue(state, encounter.dialogue.meeting[state.dialogueIndex]);
  } else {
    state.battle = createBattle(state.inventory.mushrooms);
    scene(state, 'transition');
    dialogue(state, encounter.dialogue.battleEntry);
  }
}

function changePhase(state, phase) {
  const battle = state.battle;
  battle.phase = phase;
  battle.phaseClock = 0;
  event(state, phase, { wave: battle.wave, turn: battle.turn, command: battle.command });
}

function beginBattleStep(player, x) {
  if (Math.abs(player.x - x) < EPSILON) return;
  player.step = { fromX: player.x, toX: x, age: 0 };
  player.face = x > player.x ? 'right' : 'left';
}

function updateBattleStep(player, dt) {
  const movement = player.step;
  if (!movement) return;
  movement.age += dt;
  const progress = clip(movement.age / COMMAND_STEP_TIME, 0, 1);
  player.x = mix(movement.fromX, movement.toX, ease(progress));
  if (progress === 1) {
    player.step = null;
    player.face = 'right';
  }
}

function openCommand(state, command = 'jump') {
  const battle = state.battle;
  battle.command = command;
  beginBattleStep(battle.players[battle.turn], START[battle.turn].x + COMMAND_STEP_LENGTH);
  changePhase(state, 'command');
}

function createBattle(mushrooms) {
  return {
    phase: 'dodge', phaseClock: 0, wave: 0, elapsed: 0, turn: 0,
    command: 'jump', menuDirection: 0, bump: null, held: [false, false],
    items: mushrooms, itemTarget: 0, notice: null,
    hp: [...MAX_HP], qhp: QUEEN_HP,
    players: START.map(p => ({ ...p, hurt: 0, face: 'right', step: null })),
    queen: { ...QUEEN, hurt: 0 },
    jumps: [0, 0], jumpTime: [null, null], press: [0, 0],
    telegraph: null, telegraphs: [], shots: [], feedback: [null, null],
    fx: [], stomp: null,
  };
}

function beginBattle(state) {
  scene(state, 'battle');
  changePhase(state, 'dodge');
}

function addFX(battle, type, x, y, extra = {}) {
  battle.fx.push({ type, x, y, time: 0.75, age: 0, ...extra });
}

function feedback(battle, target, text) {
  battle.feedback[target] = { text, time: 0.82 };
}

function jump(state, target) {
  const battle = state.battle;
  if (battle.jumpTime[target] !== null || battle.players[target].hurt > 0.12) return;
  const player = battle.players[target];
  battle.jumpTime[target] = 0;
  addFX(battle, 'dust', player.x, player.y);
  event(state, 'jump', { target, mode: 'dodge' });
}

function updateJumps(battle, dt) {
  for (const target of [0, 1]) {
    if (battle.jumpTime[target] === null) continue;
    battle.jumpTime[target] += dt;
    const u = clip(battle.jumpTime[target] / JUMP_LENGTH, 0, 1);
    battle.jumps[target] = arc(u, JUMP_HEIGHT);
    if (u === 1) battle.jumpTime[target] = null;
  }
}

function startShot(state, target, kind, flight, id) {
  const battle = state.battle;
  const fromX = battle.queen.x - 24;
  const fromY = battle.queen.y - 21;
  const player = START[target];
  battle.shots.push({
    id, target, kind, flight, age: 0, tested: false,
    fromX, fromY, toX: player.x, toY: player.y - 3,
    x: fromX, y: fromY, z: 0,
  });
  addFX(battle, 'muzzle', fromX, fromY, { kind });
  event(state, 'shot', { target, kind, id });
}

function testShot(state, shot) {
  const battle = state.battle;
  const { target, kind, id } = shot;
  const player = battle.players[target];
  shot.tested = true;
  if (battle.jumps[target] > AIR_DODGE_HEIGHT) {
    feedback(battle, target, 'DODGE!');
    addFX(battle, 'graze', player.x, player.y - battle.jumps[target], { target });
    event(state, 'dodge', { target, kind, id, height: battle.jumps[target] });
    return;
  }
  const damage = battle.wave === 0 ? 6 : kind === 'battery' ? 10 : 8;
  battle.hp[target] = Math.max(0, battle.hp[target] - damage);
  player.hurt = 0.38;
  shot.hit = true;
  feedback(battle, target, '-' + damage);
  addFX(battle, 'hit', player.x, player.y - 12, { target, damage });
  event(state, 'hit', { target, kind, damage, id, height: battle.jumps[target] });
}

function moveShots(state, dt) {
  const battle = state.battle;
  for (const shot of battle.shots) {
    shot.age += dt;
    const u = shot.age / shot.flight;
    shot.x = mix(shot.fromX, shot.toX, u);
    shot.y = mix(shot.fromY, shot.toY, Math.min(1, u));
    shot.z = shot.kind === 'battery' ? arc(clip(u, 0, 1), 44) : 0;
    if (u >= 1 - EPSILON && !shot.tested) testShot(state, shot);
  }
  battle.shots = battle.shots.filter(shot => !shot.hit && shot.x > -30);
}

function updateDodge(state, dt, input) {
  const battle = state.battle;
  const now = battle.phaseClock;
  const before = now - dt;
  for (const target of [0, 1]) {
    if (input[ACTIONS[target]]) jump(state, target);
  }
  updateJumps(battle, dt);

  battle.telegraphs = [];
  const wave = encounter.battle.waves[Number(battle.wave > 0)];
  for (const [id, row] of wave.attacks.entries()) {
    const [tell, target, kind, flight] = row;
    const launch = tell + TELL_LENGTH;
    if (crossed(before, now, tell)) {
      event(state, 'tell', { target, kind, id });
    }
    if (crossed(before, now, launch)) {
      startShot(state, target, kind, flight, id);
    }
    if (now >= tell && now < launch) {
      battle.telegraphs.push({ target, kind, remaining: launch - now, duration: TELL_LENGTH });
    }
  }
  battle.telegraph = battle.telegraphs[0] ?? null;
  moveShots(state, dt);

  if (battle.hp.includes(0)) {
    changePhase(state, 'defeat');
  } else if (now >= wave.duration) {
    battle.jumps.fill(0);
    battle.jumpTime.fill(null);
    battle.shots.length = 0;
    battle.turn = battle.wave < 2 ? 0 : (battle.wave - 1) % 2;
    openCommand(state);
  }
}

function beginStomp(state) {
  const battle = state.battle;
  const target = battle.turn;
  const player = battle.players[target];
  const kind = battle.command;
  const hammer = kind === 'hammer';
  const weapon = target === 0 ? 'sword' : 'axe';
  battle.stomp = {
    target, kind, weapon, startX: player.x, startY: player.y,
    elapsed: 0, duration: hammer ? HAMMER_CONTACT : FIRST_STOMP,
    stage: 'first', pose: hammer ? 'approach' : 'air',
    window: HIT_WINDOW, attempted: false, quality: 'basic', charged: false,
    chargeStart: null, swingStart: null,
  };
  addFX(battle, 'dust', player.x, player.y);
  event(state, hammer ? 'hammer' : 'jump', { target, mode: 'stomp', kind, weapon });
  changePhase(state, 'stomp');
}

function stompDamage(state) {
  const battle = state.battle;
  const { target, quality, kind, weapon, stage } = battle.stomp;
  const bonus = stage === 'rebound';
  const hammer = kind === 'hammer';
  const excellent = quality === 'excellent';
  let damage = target === 0 ? 13 : 18;
  if (hammer) damage = (target === 0 ? 16 : 20) + (excellent ? 11 : 0);
  if (bonus) damage = excellent ? (target === 0 ? 10 : 12) : 3;

  battle.qhp = Math.max(0, battle.qhp - damage);
  battle.queen.hurt = excellent ? 0.48 : 0.24;
  const impactType = excellent ? 'excellent' : 'impact';
  const grade = excellent ? 'EXCELLENT!' : quality === 'good' ? 'GOOD!' : bonus ? 'MISS' : null;
  const impact = { damage, bonus, target, grade, kind, weapon };
  addFX(battle, impactType, QUEEN.x, QUEEN.y - (hammer ? 24 : 59), impact);
  feedback(battle, target, grade ?? String(damage));
  event(state, impactType, { ...impact, quality });
}

function stompStage(stomp, stage, duration, window = HIT_WINDOW) {
  Object.assign(stomp, { stage, elapsed: 0, duration, window, attempted: false, quality: 'basic' });
}

function timeStrike(battle, stomp, input, progress) {
  const { target, stage } = stomp;
  if (!input[ACTIONS[target]] || stomp.attempted || progress <= 0.40) return;
  stomp.attempted = true;
  if (stomp.duration - stomp.elapsed <= stomp.window + EPSILON) {
    stomp.quality = stage === 'rebound' ? 'excellent' : 'good';
  } else {
    feedback(battle, target, 'EARLY');
  }
}

function finishTurn(state) {
  const battle = state.battle;
  beginBattleStep(battle.players[battle.turn], START[battle.turn].x);
  if (battle.qhp === 0) {
    changePhase(state, 'victory');
    event(state, 'win');
  } else if (battle.wave === 0 && battle.turn === 0) {
    battle.turn = 1;
    openCommand(state);
  } else {
    battle.wave++;
    changePhase(state, 'dodge');
  }
}

function finishStomp(state, target) {
  const battle = state.battle;
  Object.assign(battle.players[target], START[target], { face: 'right' });
  battle.jumps[target] = 0;
  battle.stomp = null;
  finishTurn(state);
}

function beginSwing(state, stomp, released) {
  const { target, weapon, elapsed } = stomp;
  stomp.swingStart = elapsed;
  stomp.duration = elapsed + HAMMER_SWING;
  stomp.pose = 'swing';
  if (!released) return;
  const chargeTime = elapsed - stomp.chargeStart;
  const timed = chargeTime >= HAMMER_CHARGE_MIN &&
    Math.abs(HAMMER_CONTACT - stomp.duration) <= HIT_WINDOW + EPSILON;
  if (timed) stomp.quality = 'excellent';
  else feedback(state.battle, target, 'EARLY');
  event(state, 'release', { target, weapon, kind: 'hammer', timed });
}

function updateHammer(state, input) {
  const battle = state.battle;
  const stomp = battle.stomp;
  const { target, elapsed, chargeStart, swingStart, weapon } = stomp;
  const player = battle.players[target];
  const walk = ease(clip(elapsed / HAMMER_CHARGE_START, 0, 1));
  player.x = mix(stomp.startX, HAMMER_REACH, walk);
  player.y = mix(stomp.startY, QUEEN.y, walk);

  if (swingStart === null) {
    const held = !!input[ACTIONS[target] + 'Held'];
    if (chargeStart === null && held && elapsed >= HAMMER_CHARGE_START) {
      stomp.chargeStart = elapsed;
      stomp.pose = 'charge';
      event(state, 'charge', { target, weapon, kind: 'hammer' });
    } else if (chargeStart !== null) {
      stomp.charged = elapsed - chargeStart >= HAMMER_CHARGE_MIN;
      if (battle.held[target] && !held) beginSwing(state, stomp, true);
    }
    if (stomp.swingStart === null && elapsed >= HAMMER_CONTACT) beginSwing(state, stomp, false);
  }
  if (stomp.swingStart !== null && elapsed >= stomp.duration - EPSILON) {
    stompDamage(state);
    stompStage(stomp, 'return', RETURN);
    stomp.pose = 'follow';
  }
}

function updateStomp(state, dt, input) {
  const battle = state.battle;
  const stomp = battle.stomp;
  const { target, stage, kind, weapon } = stomp;
  const start = START[target];
  const player = battle.players[target];
  stomp.elapsed += dt;
  const u = clip(stomp.elapsed / stomp.duration, 0, 1);
  const hammer = kind === 'hammer';
  const reach = hammer ? HAMMER_REACH : SWORD_REACH;
  if (stage === 'return') {
    if (hammer && stomp.elapsed <= HAMMER_FOLLOW) return;
    const retreat = hammer ? ease(clip((stomp.elapsed - HAMMER_FOLLOW) / (RETURN - HAMMER_FOLLOW), 0, 1)) : u;
    player.x = mix(reach, start.x, retreat);
    player.y = mix(QUEEN.y, start.y, retreat);
    player.face = 'left';
    stomp.pose = 'recover';
    if (!hammer) battle.jumps[target] = 60 * (1 - u * u);
    if (u >= 1 - EPSILON) finishStomp(state, target);
    return;
  }
  if (hammer) {
    updateHammer(state, input);
    return;
  }
  stomp.pose = u >= 0.84 ? 'strike' : 'air';
  if (stage === 'rebound') {
    battle.jumps[target] = 60 + arc(u, 47);
  } else {
    const to = Math.min(u / 0.84, 1);
    player.x = mix(stomp.startX, reach, to);
    player.y = mix(stomp.startY, QUEEN.y, to);
    battle.jumps[target] = 60 * u + arc(u, 78);
  }
  timeStrike(battle, stomp, input, u);
  if (u < 1 - EPSILON) return;
  stompDamage(state);
  if (stage === 'first' && stomp.quality === 'good' && battle.qhp > 0) {
    stompStage(stomp, 'rebound', REBOUND, REBOUND_WINDOW);
    stomp.pose = 'air';
    event(state, 'jump', { target, mode: 'bonus', kind, weapon });
  } else {
    stompStage(stomp, 'return', RETURN);
    stomp.pose = 'recover';
  }
}

function freshDirection(battle, input) {
  const direction = Number(!!input.right) - Number(!!input.left);
  return direction === battle.menuDirection ? 0 : direction;
}

function updateCommand(state, input) {
  const battle = state.battle;
  const direction = freshDirection(battle, input);
  if (direction) {
    const index = (COMMANDS.indexOf(battle.command) + direction + COMMANDS.length) % COMMANDS.length;
    battle.command = COMMANDS[index];
    event(state, 'select', { turn: battle.turn, target: battle.turn, command: battle.command, direction });
  }
  if (!input[ACTIONS[battle.turn]]) return;
  battle.players[battle.turn].step = null;
  battle.bump = { target: battle.turn, elapsed: 0, duration: BUMP_LENGTH, command: battle.command };
  event(state, 'jump', { target: battle.turn, mode: 'menu', command: battle.command });
  changePhase(state, 'bump');
}

function updateBump(state, dt) {
  const battle = state.battle;
  const { bump } = battle;
  const before = bump.elapsed;
  bump.elapsed += dt;
  const u = clip(bump.elapsed / bump.duration, 0, 1);
  battle.jumps[bump.target] = arc(u, BUMP_HEIGHT);
  if (crossed(before, bump.elapsed, bump.duration / 2)) {
    event(state, 'blockHit', { target: bump.target, command: bump.command });
  }
  if (u < 1) return;
  battle.bump = null;
  if (battle.command === 'item') {
    battle.itemTarget = battle.turn;
    changePhase(state, 'item');
  } else {
    changePhase(state, battle.command === 'flee' ? 'flee' : 'target');
  }
}

function showNotice(state, message) {
  state.battle.notice = message;
  changePhase(state, 'notice');
}

function updateSubmenu(state, input) {
  const battle = state.battle;
  const confirm = input[ACTIONS[battle.turn]];
  if (input.cancel || (battle.phase === 'notice' && (confirm || battle.phaseClock >= 1.35))) {
    battle.notice = null;
    openCommand(state, battle.command);
    return;
  }
  if (battle.phase === 'item') {
    if (freshDirection(battle, input)) {
      battle.itemTarget = 1 - battle.itemTarget;
      event(state, 'select', { turn: battle.turn, target: battle.itemTarget, command: 'item' });
    }
    if (!confirm) return;
    const target = battle.itemTarget;
    const heal = Math.min(ITEM_HEAL, MAX_HP[target] - battle.hp[target]);
    if (!battle.items || !heal) {
      showNotice(state, battle.items ? 'HP IS ALREADY FULL.' : 'NO MUSHROOMS LEFT.');
      return;
    }
    battle.items--;
    state.inventory.mushrooms--;
    battle.hp[target] += heal;
    const player = battle.players[target];
    feedback(battle, target, '+' + heal + ' HP');
    addFX(battle, 'heal', player.x, player.y - 20, { target, heal });
    event(state, 'heal', { target, heal });
    finishTurn(state);
    return;
  }
  if (battle.phase === 'flee' && confirm) {
    event(state, 'fleeBlocked', { target: battle.turn });
    showNotice(state, 'THE EXIT IS LOCKED.');
  }
  if (battle.phase === 'target' && confirm) beginStomp(state);
}

function updateBattle(state, dt, input) {
  const battle = state.battle;
  battle.elapsed += dt;
  battle.phaseClock += dt;

  for (const target of [0, 1]) {
    const player = battle.players[target];
    updateBattleStep(player, dt);
    player.hurt = Math.max(0, player.hurt - dt);
    battle.press[target] = Math.max(0, battle.press[target] - dt);
    if (battle.feedback[target]) {
      battle.feedback[target].time -= dt;
      if (battle.feedback[target].time <= 0) battle.feedback[target] = null;
    }
    if (input[ACTIONS[target]]) {
      battle.press[target] = 0.20;
      event(state, 'press', { target, phase: battle.phase });
    }
  }
  battle.queen.hurt = Math.max(0, battle.queen.hurt - dt);
  for (const fx of battle.fx) {
    fx.time -= dt;
    fx.age += dt;
  }
  battle.fx = battle.fx.filter(fx => fx.time > 0);

  switch (battle.phase) {
    case 'dodge':
      updateDodge(state, dt, input);
      break;
    case 'command':
      updateCommand(state, input);
      break;
    case 'bump':
      updateBump(state, dt);
      break;
    case 'target':
    case 'item':
    case 'flee':
    case 'notice':
      updateSubmenu(state, input);
      break;
    case 'stomp':
      updateStomp(state, dt, input);
      break;
    case 'victory':
      if (crossed(battle.phaseClock - dt, battle.phaseClock, BOSS_BURST_AT)) {
        event(state, 'bossBurst', { speaker: 'queen', x: battle.queen.x, y: battle.queen.y });
      }
      if (battle.phaseClock >= BOSS_BURST_AT + 1.85) {
        state.result = 'win';
        scene(state, 'end');
        dialogue(state, encounter.dialogue.victory);
      }
      break;
    case 'defeat':
      if (battle.phaseClock >= 1.40) {
        state.result = 'loss';
        scene(state, 'end');
        dialogue(state, encounter.dialogue.defeat);
      }
      break;
  }
  battle.menuDirection = Number(!!input.right) - Number(!!input.left);
  battle.held = ACTIONS.map(action => !!input[action + 'Held']);
}

export function step(state, dt, input = {}) {
  state.t += dt;
  state.clock += dt;
  if (state.line) state.line.age += dt;
  switch (state.scene) {
    case 'map': updateMap(state, dt, input); break;
    case 'dialogue': updateDialogue(state, input); break;
    case 'transition':
      if (state.clock >= 2.13) {
        state.line = null;
        beginBattle(state);
      }
      break;
    case 'battle': updateBattle(state, dt, input); break;
  }
  return state;
}
