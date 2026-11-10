import { ACTIONS, FPS } from './engine.mjs';
import { encounter } from './scene.mjs';

const EPSILON = 0.00001;
const between = (t, from, to) => t >= from - EPSILON && t < to - EPSILON;
const tick = (elapsed, time) => between(elapsed, time, time + 1 / FPS);

export function replayInput(state) {
  switch (state.scene) {
    case 'map': {
      const t = state.t;
      return {
        right: between(t, 0.30, 1.37) || between(t, 2.10, 6.52),
        up: between(t, 2.66, 3.88) || between(t, 6.52, 6.90),
        a: tick(t, 1.18) || tick(t, 4.77) || tick(t, 7.52),
        b: tick(t, 1.67) || tick(t, 5.12),
      };
    }
    case 'dialogue':
      return { a: tick(state.line.age, [2.05, 1.73, 1.36, 1.76][state.dialogueIndex]) };
    case 'battle': {
      const battle = state.battle;
      const action = ACTIONS[battle.turn];
      if (battle.phase === 'command') {
        const { phaseClock, turn, wave } = battle;
        const first = wave === 0 && turn === 0;
        return {
          left: first && [0.25, 0.57, 0.91, 1.22].some(time => tick(phaseClock, time)),
          right: wave === 0 && turn === 1 && tick(phaseClock, 0.61),
          [action]: tick(phaseClock, wave > 0 ? 1.00 : first ? 1.63 : 1.48),
        };
      }
      if (battle.phase === 'target') {
        return { [action]: tick(battle.phaseClock, battle.wave > 0 ? 0.28 : battle.turn === 0 ? 0.55 : 0.45) };
      }
      if (battle.phase === 'stomp' && battle.stomp.stage !== 'return') {
        const { kind, elapsed, duration } = battle.stomp;
        if (kind === 'hammer') {
          return {
            [action]: tick(elapsed, 0.85),
            [action + 'Held']: between(elapsed, 0.85, 1.42),
          };
        }
        return { [action]: tick(elapsed, duration - 0.045) };
      }
      if (battle.phase !== 'dodge') return {};
      const input = {};
      for (const [id, row] of encounter.battle.waves[Number(battle.wave > 0)].attacks.entries()) {
        const [tell, target, kind, flight] = row;
        if (battle.wave === 1 && id === 7) continue;
        const jumpAt = tell + encounter.battle.tellDuration + flight - (kind === 'battery' ? 0.24 : 0.21);
        if (tick(battle.phaseClock, jumpAt)) input[ACTIONS[target]] = true;
      }
      return input;
    }
    default: return {};
  }
}
