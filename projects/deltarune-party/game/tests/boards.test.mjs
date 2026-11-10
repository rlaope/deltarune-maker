import assert from 'node:assert/strict';
import test from 'node:test';
import {boards} from '../boards.mjs';
import {BoardGame} from '../engine.mjs';

const target = exit => typeof exit === 'string' ? exit : exit.to;

function distances(start, edges) {
  const result = new Map([[start, 0]]);
  const queue = [start];
  for (const id of queue) {
    for (const exit of edges.get(id)) {
      if (result.has(exit)) continue;
      result.set(exit, result.get(id) + 1);
      queue.push(exit);
    }
  }
  return result;
}

test('five large chapter maps have six covered regions and distinct route geometry', () => {
  assert.deepEqual(boards.map(board => board.chapter), [1, 2, 3, 4, 5]);
  const geometry = new Set();
  for (const board of boards) {
    assert.ok(board.width >= 3200 && board.height >= 1500, board.id);
    assert.ok(board.spaces.length >= 130, board.id);
    assert.equal(board.regions.length, 6, board.id);
    assert.equal(board.regions.reduce((area, region) => area + region.width * region.height, 0),
      board.width * board.height, board.id);
    assert.ok(board.regions.every(region => region.asset.startsWith(`boards/${board.id}/`)), board.id);
    assert.ok(board.spaces.every(space => board.regions.filter(region =>
      space.x >= region.x && space.x < region.x + region.width &&
      space.y >= region.y && space.y < region.y + region.height).length === 1), board.id);
    geometry.add(JSON.stringify(board.spaces.map(space => [space.x, space.y])));
  }
  assert.equal(geometry.size, 5);
});

test('every district can be reached and left, with nearby opening encounters and stars', () => {
  const encounterIds = new Set();
  for (const board of boards) {
    const forward = new Map(board.spaces.map(space => [space.id, space.next.map(target)]));
    const reverse = new Map(board.spaces.map(space => [space.id, []]));
    for (const [from, destinations] of forward) {
      for (const to of destinations) reverse.get(to).push(from);
    }
    const steps = distances(board.start, forward);
    assert.equal(steps.size, board.spaces.length, board.id);
    assert.equal(distances(board.start, reverse).size, board.spaces.length, board.id);
    const encounters = board.spaces.filter(space => space.event);
    assert.ok(encounters.length >= 4, board.id);
    assert.ok(Math.min(...encounters.map(space => steps.get(space.id))) <= 12, board.id);
    assert.ok(steps.get(board.starSpots[0]) <= 20, board.id);
    assert.ok(board.spaces.filter(space => space.next.length > 1).length >= 4, board.id);
    assert.ok(board.spaces.filter(space => space.next.length > 1)
      .every(space => space.next.every(exit => exit.label)), board.id);
    for (const {event} of encounters) {
      assert.ok(!encounterIds.has(event.id), event.id);
      encounterIds.add(event.id);
    }
    assert.equal(new BoardGame(board).state.star, board.starSpots[0]);
  }
});
