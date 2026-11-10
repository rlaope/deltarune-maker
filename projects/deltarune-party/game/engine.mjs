/** Deterministic hot-seat rules for a data-driven Deltarune Party board. */

const DEFAULT_PLAYERS = ['kris', 'susie', 'ralsei', 'gerson']
const STARTING_COINS = 10
const STAR_PRICE = 20
const DOUBLE_DICE = 'double-dice'

function requireRule(condition, message) {
  if (!condition) throw new Error(message)
}

function isId(value) {
  return typeof value === 'string' && value.length > 0
}

function nonnegativeInteger(value) {
  return Number.isSafeInteger(value) && value >= 0
}

function effectList(effect) {
  if (effect === undefined) return []
  return Array.isArray(effect) ? effect : [effect]
}

function validateEffects(effect, spaces) {
  for (const entry of effectList(effect)) {
    requireRule(entry && typeof entry === 'object', 'Board effects must be objects')
    switch (entry.type) {
      case 'coins':
        requireRule(Number.isSafeInteger(entry.amount), 'A coin effect needs an integer amount')
        break
      case 'toll':
        requireRule(nonnegativeInteger(entry.amount), 'A toll needs a nonnegative integer amount')
        break
      case 'item':
        requireRule((entry.item ?? DOUBLE_DICE) === DOUBLE_DICE, 'Unknown board item')
        break
      case 'warp':
        requireRule(spaces.has(entry.to), `Unknown warp destination: ${entry.to}`)
        break
      default:
        throw new Error(`Unknown board effect: ${entry.type}`)
    }
  }
}

function validateEncounter(event, spaces) {
  requireRule(event && isId(event.id) && isId(event.title), 'An encounter needs an ID and title')
  requireRule(Array.isArray(event.lines) && event.lines.every(line =>
    line && isId(line.speaker) && typeof line.text === 'string'), 'An encounter needs dialogue lines')
  validateEffects(event.effect, spaces)
  if (event.choices === undefined) return
  requireRule(Array.isArray(event.choices) && event.choices.length > 0, 'Encounter choices must be nonempty')
  const ids = new Set()
  for (const choice of event.choices) {
    requireRule(choice && isId(choice.id) && isId(choice.label), 'A choice needs an ID and label')
    requireRule(!ids.has(choice.id), `Duplicate encounter choice: ${choice.id}`)
    requireRule(nonnegativeInteger(choice.cost ?? 0), 'An encounter choice needs a nonnegative cost')
    validateEffects(choice.effect, spaces)
    ids.add(choice.id)
  }
  requireRule(event.choices.some(choice => (choice.cost ?? 0) === 0),
    `Encounter ${event.id} needs a free choice`)
}

function readBoard(board) {
  requireRule(board && Array.isArray(board.spaces), 'A board needs spaces')
  const spaces = new Map()
  for (const space of board.spaces) {
    requireRule(space && isId(space.id), 'Each space needs an ID')
    requireRule(!spaces.has(space.id), `Duplicate space: ${space.id}`)
    requireRule(isId(space.type) && Number.isFinite(space.x) && Number.isFinite(space.y),
      `Invalid coordinates or type for space ${space.id}`)
    spaces.set(space.id, space)
  }
  requireRule(spaces.has(board.start), 'The board needs a valid start space')
  requireRule(Array.isArray(board.starSpots) && board.starSpots.every(id => spaces.has(id)),
    'The board has an invalid star spot')
  requireRule(new Set(board.starSpots).size === board.starSpots.length, 'Duplicate star spot')
  for (const space of spaces.values()) {
    requireRule(Array.isArray(space.next) && space.next.length > 0, `No exit from space ${space.id}`)
    const exits = new Set()
    space.next = space.next.map(value => {
      const edge = typeof value === 'string' ? {to: value} : value
      requireRule(edge && spaces.has(edge.to), `Invalid exit from space ${space.id}`)
      requireRule(!exits.has(edge.to), `Duplicate exit from ${space.id} to ${edge.to}`)
      requireRule(nonnegativeInteger(edge.cost ?? 0), 'A branch cost must be a nonnegative integer')
      const label = edge.label ?? spaces.get(edge.to).label ?? edge.to
      requireRule(isId(label), 'A branch label must be a nonempty string')
      exits.add(edge.to)
      return {to: edge.to, label, cost: edge.cost ?? 0}
    })
    requireRule(space.next.some(edge => edge.cost === 0), `Space ${space.id} needs a free exit`)
    if (space.event !== undefined) validateEncounter(space.event, spaces)
  }
  return spaces
}

export class BoardGame {
  #spaces
  #starSpots
  #players
  #rounds
  #seed
  #round = 1
  #activeIndex = 0
  #phase = 'roll'
  #remaining = 0
  #star
  #encounter = null
  #armedItem = null
  #dice = []
  #standings = []
  #trace = []

  constructor(board, {seed = 1, rounds = 10, players = DEFAULT_PLAYERS, start} = {}) {
    requireRule(Number.isSafeInteger(seed), 'The seed must be an integer')
    requireRule(Number.isSafeInteger(rounds) && rounds > 0, 'Round count must be a positive integer')
    requireRule(Array.isArray(players) && players.length > 0 && players.every(isId) &&
      new Set(players).size === players.length, 'Players need distinct IDs')
    const source = structuredClone(board)
    this.#spaces = readBoard(source)
    this.#starSpots = source.starSpots
    this.#star = this.#starSpots[0] ?? null
    const startingSpace = start === undefined ? source.start : start
    requireRule(this.#spaces.has(startingSpace), `Unknown starting space: ${startingSpace}`)
    this.#players = players.map(id => ({id, space: startingSpace, coins: STARTING_COINS, stars: 0, items: []}))
    this.#rounds = rounds
    this.#seed = seed >>> 0
  }

  get #player() {
    return this.#players[this.#activeIndex]
  }

  get state() {
    const encounter = this.#encounter
    return structuredClone({
      phase: this.#phase,
      round: this.#round,
      rounds: this.#rounds,
      active: this.#player.id,
      players: this.#players,
      remaining: this.#remaining,
      star: this.#star,
      options: this.#options().map(({id, label, enabled, cost}) =>
        cost ? {id, label, enabled, cost} : {id, label, enabled}),
      encounter: encounter ? {id: encounter.id, title: encounter.title, lines: encounter.lines,
        space: this.#player.space} : null,
      dice: this.#dice,
      armedItem: this.#armedItem,
      winner: this.#standings[0] ?? null,
      standings: this.#standings,
    })
  }

  /** Replay on a game constructed with the same board and setup by dispatching each entry's action. */
  get trace() {
    return structuredClone(this.#trace)
  }

  dispatch(action) {
    requireRule(action && typeof action === 'object', 'Provide a board action')
    const events = []
    let accepted
    switch (action.type) {
      case 'roll':
        requireRule(this.#phase === 'roll', 'You can only roll on your roll phase')
        accepted = {type: 'roll'}
        this.#roll(events)
        break
      case 'use-item': {
        const item = action.item ?? action.option ?? DOUBLE_DICE
        requireRule(this.#phase === 'roll' && this.#armedItem === null, 'You cannot use an item now')
        requireRule(item === DOUBLE_DICE && this.#player.items.includes(item), 'Item is not available')
        accepted = {type: 'use-item', item}
        this.#player.items.splice(this.#player.items.indexOf(item), 1)
        this.#armedItem = item
        events.push({type: 'item', player: this.#player.id, item, action: 'use'})
        break
      }
      case 'choose': {
        const option = this.#options().find(candidate => candidate.id === action.option)
        requireRule(option && option.enabled, 'Choice is unavailable')
        accepted = {type: 'choose', option: option.id}
        this.#choose(option, events)
        break
      }
      case 'end':
        requireRule(this.#phase === 'end', 'You can only end a completed turn')
        accepted = {type: 'end'}
        this.#end(events)
        break
      default:
        throw new Error(`Unknown board action: ${action.type}`)
    }
    this.#trace.push({action: accepted, events: structuredClone(events)})
    return events
  }

  #randomInt(limit) {
    this.#seed = (Math.imul(this.#seed, 1664525) + 1013904223) >>> 0
    return Math.floor((this.#seed / 2 ** 32) * limit)
  }

  #roll(events) {
    const count = this.#armedItem === DOUBLE_DICE ? 2 : 1
    this.#armedItem = null
    this.#dice = Array.from({length: count}, () => 1 + this.#randomInt(10))
    this.#remaining = this.#dice.reduce((sum, value) => sum + value, 0)
    events.push({type: 'roll', player: this.#player.id, values: [...this.#dice]})
    this.#advance(events)
  }

  #options() {
    const coins = this.#player.coins
    if (this.#phase === 'branch') {
      return this.#spaces.get(this.#player.space).next.map(edge => ({
        id: edge.to, label: edge.label, cost: edge.cost, enabled: edge.cost <= coins, edge,
      }))
    }
    if (this.#phase === 'star') {
      return [
        {id: 'buy', label: 'Buy star', cost: STAR_PRICE, enabled: coins >= STAR_PRICE},
        {id: 'skip', label: 'Skip star', enabled: true},
      ]
    }
    if (this.#phase === 'event') {
      const choices = this.#encounter.choices ?? [
        {id: 'continue', label: 'Continue', effect: this.#encounter.effect},
      ]
      return choices.map(choice => ({...choice, enabled: (choice.cost ?? 0) <= coins}))
    }
    return []
  }

  #choose(option, events) {
    if (this.#phase === 'branch') {
      this.#takeEdge(option.edge, events)
      if (!this.#offerStar(events)) this.#advance(events)
      return
    }
    if (this.#phase === 'star') {
      if (option.id === 'buy') this.#buyStar(events)
      this.#advance(events)
      return
    }
    const encounter = this.#encounter
    this.#encounter = null
    this.#phase = 'end'
    if (option.cost) this.#changeCoins(-option.cost, 'choice', events)
    this.#applyEffects(option.effect, events)
    events.push({type: 'event-resolved', player: this.#player.id, id: encounter.id, option: option.id})
  }

  #advance(events) {
    while (this.#remaining > 0) {
      const space = this.#spaces.get(this.#player.space)
      if (space.next.length > 1) {
        this.#phase = 'branch'
        events.push({type: 'branch', player: this.#player.id, space: space.id})
        return
      }
      this.#takeEdge(space.next[0], events)
      if (this.#offerStar(events)) return
    }
    this.#land(events)
  }

  #takeEdge(edge, events) {
    const from = this.#player.space
    if (edge.cost) this.#changeCoins(-edge.cost, 'branch', events)
    this.#player.space = edge.to
    this.#remaining -= 1
    events.push({type: 'move', player: this.#player.id, from, to: edge.to, remaining: this.#remaining})
  }

  #offerStar(events) {
    if (this.#player.space !== this.#star) return false
    this.#phase = 'star'
    events.push({type: 'star-offer', player: this.#player.id, space: this.#star, cost: STAR_PRICE})
    return true
  }

  #buyStar(events) {
    const space = this.#star
    this.#changeCoins(-STAR_PRICE, 'star', events)
    this.#player.stars += 1
    const candidates = this.#starSpots.filter(spot => spot !== space)
    if (candidates.length) this.#star = candidates[this.#randomInt(candidates.length)]
    events.push({type: 'star', player: this.#player.id, space, stars: this.#player.stars, next: this.#star})
  }

  #land(events) {
    const space = this.#spaces.get(this.#player.space)
    this.#phase = 'end'
    events.push({type: 'land', player: this.#player.id, space: space.id, kind: space.type})
    if (space.type === 'blue') this.#changeCoins(3, 'blue', events)
    if (space.type === 'red') this.#changeCoins(-3, 'red', events)
    if (space.type === 'item') this.#giveItem(DOUBLE_DICE, events)
    if (space.event) {
      this.#phase = 'event'
      this.#encounter = space.event
      events.push({type: 'encounter', player: this.#player.id, id: space.event.id,
        title: space.event.title, lines: structuredClone(space.event.lines), space: space.id})
    }
  }

  #changeCoins(amount, reason, events) {
    const balance = Math.min(Number.MAX_SAFE_INTEGER, Math.max(0, this.#player.coins + amount))
    const change = balance - this.#player.coins
    this.#player.coins = balance
    if (change) events.push({type: 'coins', player: this.#player.id, amount: change, balance, reason})
  }

  #giveItem(item, events) {
    this.#player.items.push(item)
    events.push({type: 'item', player: this.#player.id, item, action: 'get'})
  }

  #applyEffects(effect, events) {
    for (const entry of effectList(effect)) {
      switch (entry.type) {
        case 'coins':
          this.#changeCoins(entry.amount, 'event', events)
          break
        case 'toll':
          this.#changeCoins(-entry.amount, 'toll', events)
          break
        case 'item':
          this.#giveItem(entry.item ?? DOUBLE_DICE, events)
          break
        case 'warp': {
          const from = this.#player.space
          this.#player.space = entry.to
          events.push({type: 'warp', player: this.#player.id, from, to: entry.to})
          break
        }
      }
    }
  }

  #end(events) {
    if (this.#activeIndex === this.#players.length - 1 && this.#round === this.#rounds) {
      const ranking = [...this.#players].sort((a, b) => b.stars - a.stars || b.coins - a.coins)
      this.#standings = ranking.map(player => player.id)
      this.#phase = 'results'
      events.push({type: 'results', winner: this.#standings[0], standings: [...this.#standings]})
      return
    }
    const from = this.#player.id
    this.#activeIndex = (this.#activeIndex + 1) % this.#players.length
    if (this.#activeIndex === 0) this.#round += 1
    this.#phase = 'roll'
    this.#dice = []
    events.push({type: 'handoff', from, to: this.#player.id, round: this.#round})
  }
}
