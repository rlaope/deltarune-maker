import assert from 'node:assert/strict'
import test from 'node:test'
import {BoardGame} from '../engine.mjs'

const NEXT = {type: 'end'}
const ROLL = {type: 'roll'}
const choose = option => ({type: 'choose', option})
const event = (id, effect, choices) => ({
  id,
  title: 'Test encounter',
  lines: [{speaker: 'ralsei', text: '* A test encounter.'}],
  effect,
  choices,
})

function space(id, next, overrides = {}) {
  return {id, x: 16, y: 24, type: 'path', next, ...overrides}
}

function board(spaces, starSpots = []) {
  return {id: 'test', chapter: 1, title: 'Test Board', width: 64, height: 64,
    start: spaces[0].id, starSpots, spaces}
}

function loop(overrides = {}, starSpots = []) {
  return board(Array.from({length: 12}, (_, i) => space(
    `p${i}`, [`p${(i + 1) % 12}`], overrides[i],
  )), starSpots)
}

test('plays four hot-seat turns and replays a trace with the same seed', () => {
  const map = board([space('home', ['home'])])
  const game = new BoardGame(map, {seed: 1, rounds: 2})
  const order = ['kris', 'susie', 'ralsei', 'gerson']
  for (let index = 0; index < 8; index += 1) {
    assert.equal(game.state.active, order[index % order.length])
    assert.equal(game.state.round, index < 4 ? 1 : 2)
    const [die, ...events] = game.dispatch(ROLL)
    assert.equal(die.type, 'roll')
    assert.equal(die.player, order[index % order.length])
    assert.equal(events.filter(entry => entry.type === 'move').length, die.values[0])
    assert.equal(game.state.phase, 'end')
    const [result] = game.dispatch(NEXT)
    assert.equal(result.type, index === 7 ? 'results' : 'handoff')
  }
  assert.equal(game.state.phase, 'results')
  assert.equal(game.state.winner, 'kris')
  assert.deepEqual(game.state.standings, order)
  const replay = new BoardGame(map, {seed: 1, rounds: 2})
  for (const {action, events} of game.trace) assert.deepEqual(replay.dispatch(action), events)
  assert.deepEqual(replay.state, game.state)
})

test('a scene can start at another valid space on the same board', () => {
  const map = loop()
  const game = new BoardGame(map, {start: 'p8'})
  assert.deepEqual(game.state.players.map(player => player.space), Array(4).fill('p8'))
  assert.equal(game.dispatch(ROLL).find(entry => entry.type === 'move').from, 'p8')
  assert.equal(game.state.players[0].space, 'p11')
  assert.equal(new BoardGame(map).state.players[0].space, 'p0')
  assert.throws(() => new BoardGame(map, {start: 'missing'}), /Unknown starting space/)
})

test('per-player starts override the common start and replay a dispersed round', () => {
  const map = loop()
  const setup = {rounds: 1, start: 'p8', starts: {kris: 'p1', ralsei: 'p5', gerson: 'p10'}}
  const game = new BoardGame(map, setup)
  const starts = ['p1', 'p8', 'p5', 'p10']
  assert.deepEqual(game.state.players.map(player => player.space), starts)
  for (const start of starts) {
    assert.equal(game.dispatch(ROLL).find(entry => entry.type === 'move').from, start)
    game.dispatch(NEXT)
  }
  assert.equal(game.state.phase, 'results')
  const replay = new BoardGame(map, setup)
  for (const {action, events} of game.trace) assert.deepEqual(replay.dispatch(action), events)
  assert.deepEqual(replay.state, game.state)
  assert.equal(new BoardGame(map, {starts: {susie: 'p2'}}).state.players[0].space, 'p0')
  assert.throws(() => new BoardGame(map, {starts: null}), /Starts must map player IDs to spaces/)
  assert.throws(() => new BoardGame(map, {starts: {lancer: 'p1'}}), /Unknown starting player: lancer/)
  assert.throws(() => new BoardGame(map, {starts: {kris: 'missing'}}), /Unknown starting space for kris/)
})

test('branches charge on traversal and red or blue rewards only apply on landing', () => {
  const map = board([
    space('start', ['pass']),
    space('pass', ['fork'], {type: 'blue', event: event('passing-only', {type: 'coins', amount: 9})}),
    space('fork', ['safe', {to: 'gate', label: 'Toll gate', cost: 4}]),
    space('safe', ['start'], {type: 'red'}),
    space('gate', ['start'], {type: 'blue'}),
  ])
  const game = new BoardGame(map)
  const first = game.dispatch(ROLL)
  assert.deepEqual(first[0], {type: 'roll', player: 'kris', values: [3]})
  assert.equal(game.state.phase, 'branch')
  assert.equal(game.state.remaining, 1)
  assert.equal(game.state.players[0].coins, 10)
  assert.deepEqual(game.state.options, [
    {id: 'safe', label: 'safe', enabled: true},
    {id: 'gate', label: 'Toll gate', enabled: true, cost: 4},
  ])
  const result = game.dispatch(choose('gate'))
  assert.deepEqual(result.map(entry => entry.type), ['coins', 'move', 'land', 'coins'])
  assert.deepEqual(result.filter(entry => entry.type === 'coins').map(entry => entry.amount), [-4, 3])
  assert.equal(game.state.players[0].coins, 9)
  assert.equal(game.state.phase, 'end')
})

test('an invalid action preserves the full state, trace, and future dice', () => {
  const map = board([
    space('start', ['fork']),
    space('fork', [{to: 'toll', cost: 11}, 'free']),
    space('toll', ['start']),
    space('free', ['fork']),
  ])
  const game = new BoardGame(map)
  const control = new BoardGame(map)
  assert.throws(() => game.dispatch({type: 'use-item'}), /not available/)
  assert.deepEqual(game.state, control.state)
  assert.deepEqual(game.trace, [])
  assert.deepEqual(game.dispatch(ROLL), control.dispatch(ROLL))
  const snapshot = game.state
  const trace = game.trace
  assert.equal(snapshot.options[0].enabled, false)
  assert.throws(() => game.dispatch(choose('toll')), /unavailable/)
  assert.throws(() => game.dispatch(ROLL), /roll phase/)
  assert.throws(() => game.dispatch(NEXT), /completed turn/)
  assert.deepEqual(game.state, snapshot)
  assert.deepEqual(game.trace, trace)
  assert.deepEqual(game.dispatch(choose('free')), control.dispatch(choose('free')))
})

test('offers a star during movement, relocates a purchase, and finishes the same roll', () => {
  const map = loop({
    3: {type: 'event', event: event('gift', {type: 'coins', amount: 15})},
    7: {type: 'red'},
  }, ['p5', 'p8'])
  const game = new BoardGame(map, {players: ['kris']})
  game.dispatch(ROLL)
  game.dispatch(choose('continue'))
  game.dispatch(NEXT)
  const events = game.dispatch(ROLL)
  assert.deepEqual(events.map(entry => entry.type), ['roll', 'move', 'move', 'star-offer'])
  assert.equal(game.state.phase, 'star')
  assert.equal(game.state.star, 'p5')
  assert.equal(game.state.remaining, 2)
  const purchase = game.dispatch(choose('buy'))
  assert.deepEqual(purchase.map(entry => entry.type), ['coins', 'star', 'move', 'move', 'land', 'coins'])
  assert.deepEqual(game.state.players[0], {id: 'kris', space: 'p7', coins: 2, stars: 1, items: []})
  assert.equal(game.state.star, 'p8')
  assert.equal(game.state.phase, 'end')
})

test('skipping an unaffordable star on exact landing still awards that space', () => {
  const game = new BoardGame(loop({3: {type: 'blue'}}, ['p3']))
  game.dispatch(ROLL)
  assert.equal(game.state.phase, 'star')
  assert.equal(game.state.remaining, 0)
  assert.equal(game.state.options[0].enabled, false)
  const events = game.dispatch(choose('skip'))
  assert.deepEqual(events.map(entry => entry.type), ['land', 'coins'])
  assert.equal(game.state.players[0].coins, 13)
  assert.equal(game.state.phase, 'end')
})

test('encounter choices apply costs, give Double Dice, and warp without another landing', () => {
  const map = loop({
    3: {type: 'event', event: event('gate', {type: 'coins', amount: 99}, [
      {id: 'pay', label: 'Pay and travel', cost: 6, effect: [
        {type: 'item'},
        {type: 'warp', to: 'p9'},
      ]},
      {id: 'stay', label: 'Stay here', effect: {type: 'toll', amount: 3}},
    ])},
    9: {type: 'blue'},
  })
  const game = new BoardGame(map, {players: ['kris']})
  game.dispatch(ROLL)
  assert.deepEqual(game.state.encounter, {id: 'gate', title: 'Test encounter',
    lines: [{speaker: 'ralsei', text: '* A test encounter.'}], space: 'p3'})
  const reward = game.dispatch(choose('pay'))
  assert.deepEqual(reward.map(entry => entry.type), ['coins', 'item', 'warp', 'event-resolved'])
  assert.deepEqual(game.state.players[0], {id: 'kris', space: 'p9', coins: 4, stars: 0,
    items: ['double-dice']})
  game.dispatch(NEXT)
  assert.deepEqual(game.dispatch({type: 'use-item'}), [
    {type: 'item', player: 'kris', item: 'double-dice', action: 'use'},
  ])
  assert.equal(game.state.armedItem, 'double-dice')
  const [die, ...path] = game.dispatch(ROLL)
  assert.deepEqual(die.values, [4, 6])
  assert.equal(path.filter(entry => entry.type === 'move').length, 10)
  assert.equal(game.state.armedItem, null)
  assert.deepEqual(game.state.players[0].items, [])
})

test('results sort by stars before coins', () => {
  const map = loop({
    3: {type: 'event', event: event('gift', {type: 'coins', amount: 20})},
    4: {type: 'event', event: event('larger-gift', {type: 'coins', amount: 40})},
  }, ['p6', 'p11'])
  const game = new BoardGame(map, {players: ['kris', 'susie'], rounds: 2})
  game.dispatch(ROLL)
  game.dispatch(choose('continue'))
  game.dispatch(NEXT)
  game.dispatch(ROLL)
  game.dispatch(choose('continue'))
  game.dispatch(NEXT)
  game.dispatch(ROLL)
  game.dispatch(choose('buy'))
  game.dispatch(NEXT)
  game.dispatch(ROLL)
  while (game.state.phase === 'star') game.dispatch(choose('skip'))
  game.dispatch(NEXT)
  assert.equal(game.state.winner, 'kris')
  assert.ok(game.state.players[0].coins < game.state.players[1].coins)
  assert.deepEqual(game.state.standings, ['kris', 'susie'])
})

test('coins break ties between players with the same number of stars', () => {
  const game = new BoardGame(loop({3: {type: 'red'}, 4: {type: 'blue'}}),
    {players: ['kris', 'susie'], rounds: 1})
  for (const id of ['kris', 'susie']) {
    assert.equal(game.state.active, id)
    game.dispatch(ROLL)
    game.dispatch(NEXT)
  }
  assert.deepEqual(game.state.standings, ['susie', 'kris'])
})

test('public snapshots and returned events cannot change rules or trace', () => {
  const map = loop()
  const game = new BoardGame(map)
  map.spaces[0].next[0] = 'unknown'
  const snapshot = game.state
  snapshot.players[0].coins = 500
  const output = game.dispatch(ROLL)
  output[0].values[0] = 10
  const trace = game.trace
  trace[0].events[0].values[0] = 1
  assert.equal(game.state.players[0].coins, 10)
  assert.deepEqual(game.state.dice, [3])
  assert.deepEqual(game.trace[0].events[0].values, [3])
})

test('malformed warp destinations and unpaid decision deadlocks fail before play', () => {
  assert.throws(() => new BoardGame(loop({
    3: {type: 'event', event: event('warp', {type: 'warp', to: 'missing'})},
  })), /Unknown warp destination/)
  assert.throws(() => new BoardGame(board([space('home', [{to: 'home', cost: 3}])])), /free exit/)
  assert.throws(() => new BoardGame(loop({
    3: {type: 'event', event: event('gate', undefined, [{id: 'pay', label: 'Pay', cost: 1}])},
  })), /free choice/)
})
