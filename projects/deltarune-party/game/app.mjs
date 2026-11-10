import {boards} from './boards.mjs';
import {BoardGame} from './engine.mjs';
import {BoardView, playerName} from './board_view.mjs';

const $ = id => document.getElementById(id);
const field = $('board');
const overview = $('overview');
const menu = $('board-menu');
const actions = $('actions');
const status = $('status');
const prompt = $('prompt');
const mapButton = $('map-button');
const soundButton = $('sound-button');
const boardButton = $('boards-button');
const traceButton = $('trace-button');
const portraitPlayers = new Set(['kris', 'susie', 'ralsei', 'gerson']);
const nativeSounds = {
  confirm: 'mpds-menu.wav',
  roll: 'mpds-die-hit.wav',
  step: 'mpds-board-step.wav',
  coin: 'mpds-coin.wav',
};

let selected = boards[0];
let activeBoard = null;
let game = null;
let state = null;
let setup = null;
let hasTrace = false;
let choosing = true;
let browsing = false;
let busy = false;
let sound = false;
let lineIndex = 0;
let drag = null;
const audio = new Map();
const view = new BoardView(field, overview, showAssetNote);

function showAssetNote() {
  const note = $('asset-note');
  note.textContent = view.assetSummary();
  note.hidden = !note.textContent;
}

function cue(name) {
  if (!sound || !nativeSounds[name]) return;
  if (!audio.has(name)) {
    const sample = new Audio(`/assets/audio/${nativeSounds[name]}`);
    sample.volume = name === 'step' ? .16 : .38;
    audio.set(name, sample);
  }
  const sample = audio.get(name);
  sample.currentTime = 0;
  sample.play().catch(() => {});
}

function pause(ms) {
  return new Promise(resolve => setTimeout(resolve, view.reducedMotion ? 1 : ms));
}

function button(text, action, {primary = false, disabled = false} = {}) {
  const element = document.createElement('button');
  element.type = 'button';
  element.textContent = text;
  element.disabled = disabled;
  if (primary) element.className = 'primary';
  element.addEventListener('click', action);
  actions.append(element);
  return element;
}

function showPrompt(title, body = '', speaker = '') {
  const heading = document.createElement('strong');
  heading.textContent = title;
  prompt.replaceChildren();
  const portraitId = speaker.toLowerCase();
  if (portraitPlayers.has(portraitId)) {
    const face = document.createElement('img');
    face.className = 'speaker-face';
    face.src = `/assets/cast/${portraitId}-face.png`;
    face.alt = '';
    face.addEventListener('error', () => face.remove(), {once: true});
    prompt.append(face);
  }
  const copy = document.createElement('div');
  copy.append(heading);
  if (body) {
    const detail = document.createElement('p');
    detail.textContent = body;
    copy.append(detail);
  }
  prompt.append(copy);
  prompt.hidden = false;
}

function showMapControls() {
  field.classList.toggle('browsing', choosing || browsing);
  field.tabIndex = choosing || browsing ? 0 : -1;
  $('map-tools').hidden = !(choosing || browsing);
  mapButton.setAttribute('aria-pressed', String(browsing));
}

function showControls() {
  actions.replaceChildren();
  prompt.hidden = true;
  menu.hidden = !choosing;
  mapButton.hidden = choosing;
  soundButton.hidden = choosing;
  boardButton.hidden = choosing && !game;
  boardButton.textContent = choosing ? 'Back to game' : 'Boards';
  traceButton.hidden = choosing || !hasTrace;
  showMapControls();
  if (choosing) {
    status.textContent = `${selected.spaces.length} spaces for four local players`;
    button(`Start Chapter ${selected.chapter}`, startGame, {primary: true});
    return;
  }
  if (browsing) {
    status.textContent = 'Zoom in, then drag to explore';
    button('Back to turn', () => setBrowsing(false), {primary: true});
    return;
  }
  const who = playerName(state.active);
  status.textContent = `Turn ${state.round}/${state.rounds}   ${who}`;
  const player = state.players.find(candidate => candidate.id === state.active);
  switch (state.phase) {
    case 'roll':
      button(state.armedItem ? 'Roll two dice' : 'Roll dice', () => dispatch({type: 'roll'}), {primary: true});
      if (player.items.includes('double-dice') && !state.armedItem) {
        button('Use Double Dice', () => dispatch({type: 'use-item', item: 'double-dice'}));
      }
      break;
    case 'branch':
      showPrompt('Choose a route', `${state.remaining} ${state.remaining === 1 ? 'space' : 'spaces'} left`);
      showOptions();
      break;
    case 'star':
      showPrompt('A star!', `${who} can buy it for 20 coins.`);
      showOptions();
      break;
    case 'event': {
      const encounter = state.encounter;
      const line = encounter.lines[lineIndex];
      showPrompt(line ? playerName(line.speaker) : encounter.title, line?.text, line?.speaker);
      if (lineIndex < encounter.lines.length - 1) {
        button('Next', () => {
          lineIndex += 1;
          cue('confirm');
          showControls();
          actions.querySelector('button:not(:disabled)')?.focus({preventScroll: true});
        }, {primary: true});
      } else showOptions();
      break;
    }
    case 'end':
      button('End turn', () => dispatch({type: 'end'}), {primary: true});
      break;
    case 'results': {
      const rankings = state.standings.map((id, i) => `${i + 1}. ${playerName(id)}`).join('   ');
      status.textContent = 'Final standings';
      showPrompt(`${playerName(state.winner)} wins!`, rankings, state.winner);
      button('Choose another board', selectMenu, {primary: true});
      break;
    }
  }
}

function showOptions() {
  state.options.forEach((option, index) => {
    const name = option.cost ? `${option.label} (${option.cost} coins)` : option.label;
    button(name, () => dispatch({type: 'choose', option: option.id}),
      {primary: index === 0 && option.enabled, disabled: !option.enabled});
  });
}

function selectMenu() {
  if (busy) return;
  choosing = true;
  browsing = false;
  selected = activeBoard ?? selected;
  markChapter();
  view.select(selected, null);
  showControls();
}

function markChapter() {
  for (const choice of $('chapters').children) {
    choice.setAttribute('aria-pressed', String(choice.dataset.id === selected.id));
  }
}

function startGame() {
  const requestedSeed = new URLSearchParams(window.location.search).get('seed');
  const seed = requestedSeed !== null && Number.isSafeInteger(Number(requestedSeed))
    ? Number(requestedSeed) : Math.floor(Math.random() * 2 ** 32);
  const settings = {rounds: Number($('rounds').value), seed};
  try {
    game = new BoardGame(selected, settings);
  } catch (error) {
    status.textContent = error.message;
    return;
  }
  setup = settings;
  hasTrace = false;
  activeBoard = selected;
  state = game.state;
  choosing = false;
  browsing = false;
  lineIndex = 0;
  view.select(activeBoard, state);
  view.setState(state);
  cue('confirm');
  showControls();
  actions.querySelector('button')?.focus({preventScroll: true});
}

function resumeGame() {
  choosing = false;
  browsing = false;
  view.select(activeBoard, state);
  view.setState(state);
  showControls();
}

function setBrowsing(on) {
  if (busy || choosing) return;
  browsing = on;
  view.browse(on);
  showControls();
}

function saveReplay() {
  if (busy || !hasTrace) return;
  const data = {board: activeBoard.id, boardDefinition: activeBoard, setup, trace: game.trace};
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2) + '\n'], {type: 'application/json'}));
  const link = document.createElement('a');
  link.href = url;
  link.download = `deltarune-party-${activeBoard.id}-replay.json`;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function updatePlayer(shown, id, update) {
  const player = shown.players.find(candidate => candidate.id === id);
  if (player) Object.assign(player, update);
  view.setState(shown);
}

async function animateRoll(event) {
  status.textContent = `${playerName(event.player)} rolls…`;
  const count = event.values.length;
  for (let frame = 0; frame < 5; frame++) {
    view.dice = {spinning: true, values: Array.from({length: count}, (_, i) => 1 + (frame * 7 + i * 3) % 10)};
    view.repaint();
    await pause(55);
  }
  view.dice = {spinning: false, values: event.values};
  view.repaint();
  cue('roll');
  status.textContent = `${playerName(event.player)} rolled ${event.values.join(' + ')}`;
  await pause(385);
  view.dice = null;
  view.repaint();
}

async function playEvents(events, shown) {
  for (const event of events) {
    switch (event.type) {
      case 'roll':
        await animateRoll(event);
        break;
      case 'move':
      case 'warp':
        status.textContent = event.remaining > 0 ? `${event.remaining} spaces left` : `${playerName(event.player)} moves`;
        cue(event.type === 'warp' ? 'confirm' : 'step');
        await view.animateMove(event);
        updatePlayer(shown, event.player, {space: event.to});
        break;
      case 'coins':
        updatePlayer(shown, event.player, {coins: event.balance});
        if (event.amount === 0) break;
        view.reward = `${event.amount > 0 ? '+' : ''}${event.amount} coins`;
        status.textContent = `${playerName(event.player)} ${view.reward}`;
        view.repaint();
        cue(event.amount > 0 ? 'coin' : 'confirm');
        await pause(410);
        view.reward = null;
        break;
      case 'star':
        updatePlayer(shown, event.player, {stars: event.stars});
        shown.star = event.next;
        view.reward = '+1 Star';
        view.repaint();
        cue('coin');
        await pause(490);
        view.reward = null;
        break;
      case 'item':
        view.reward = event.action === 'use' ? 'Double Dice ready' : 'Double Dice Set';
        view.repaint();
        cue('confirm');
        await pause(480);
        view.reward = null;
        break;
      case 'handoff':
        shown.active = event.to;
        shown.round = event.round;
        view.setState(shown);
        status.textContent = `${playerName(event.to)} goes next`;
        await pause(420);
        break;
    }
  }
}

async function dispatch(action) {
  if (busy || choosing || browsing) return;
  const focusedAction = actions.contains(document.activeElement);
  let events;
  try {
    events = game.dispatch(action);
  } catch (error) {
    status.textContent = error.message;
    return;
  }
  busy = true;
  hasTrace = true;
  for (const control of actions.querySelectorAll('button')) control.disabled = true;
  mapButton.disabled = true;
  boardButton.disabled = true;
  traceButton.disabled = true;
  prompt.hidden = true;
  const shown = {...structuredClone(state), phase: 'animating', options: []};
  view.setState(shown);
  cue('confirm');
  try {
    await playEvents(events, shown);
  } finally {
    state = game.state;
    view.setState(state);
    lineIndex = 0;
    busy = false;
    mapButton.disabled = false;
    boardButton.disabled = false;
    traceButton.disabled = false;
    showControls();
    if (focusedAction) actions.querySelector('button:not(:disabled)')?.focus({preventScroll: true});
  }
}

for (const board of boards) {
  const choice = document.createElement('button');
  choice.type = 'button';
  choice.className = 'chapter';
  choice.dataset.id = board.id;
  const chapter = document.createElement('span');
  chapter.textContent = String(board.chapter).padStart(2, '0');
  choice.append(chapter, document.createTextNode(board.title));
  choice.addEventListener('click', () => {
    selected = board;
    markChapter();
    view.select(board, null);
    showControls();
  });
  $('chapters').append(choice);
}

mapButton.addEventListener('click', () => setBrowsing(!browsing));
boardButton.addEventListener('click', () => choosing ? resumeGame() : selectMenu());
traceButton.addEventListener('click', saveReplay);
soundButton.addEventListener('click', () => {
  sound = !sound;
  soundButton.setAttribute('aria-pressed', String(sound));
  soundButton.textContent = sound ? 'Sound on' : 'Sound off';
  cue('confirm');
});
$('zoom-in').addEventListener('click', () => view.zoom(1.75));
$('zoom-out').addEventListener('click', () => view.zoom(1 / 1.75));
field.addEventListener('wheel', event => {
  if (!choosing && !browsing) return;
  event.preventDefault();
  view.zoom(event.deltaY < 0 ? 1.16 : 1 / 1.16);
}, {passive: false});
field.addEventListener('pointerdown', event => {
  if (!choosing && !browsing) return;
  drag = {x: event.clientX, y: event.clientY, id: event.pointerId};
  field.setPointerCapture(event.pointerId);
});
field.addEventListener('pointermove', event => {
  if (!drag || drag.id !== event.pointerId) return;
  const ratio = field.width / field.getBoundingClientRect().width;
  view.pan((drag.x - event.clientX) * ratio, (drag.y - event.clientY) * ratio);
  drag.x = event.clientX;
  drag.y = event.clientY;
});
for (const name of ['pointerup', 'pointercancel', 'lostpointercapture']) {
  field.addEventListener(name, () => { drag = null; });
}
document.addEventListener('keydown', event => {
  if (busy || ['INPUT', 'SELECT', 'TEXTAREA'].includes(event.target.tagName)) return;
  if (event.key === 'Escape') {
    if (browsing) setBrowsing(false);
    else if (choosing && game) resumeGame();
  } else if (event.key.toLowerCase() === 'y' && !choosing) {
    setBrowsing(!browsing);
  } else if (choosing || browsing) {
    const pan = {ArrowLeft: [-18, 0], ArrowRight: [18, 0], ArrowUp: [0, -18], ArrowDown: [0, 18]}[event.key];
    if (pan && event.target === field) {
      event.preventDefault();
      view.pan(...pan);
    }
  } else if (event.key === ' ' && event.target.tagName !== 'BUTTON' && state.phase === 'roll') {
    event.preventDefault();
    dispatch({type: 'roll'});
  }
});

markChapter();
view.select(selected, null);
showControls();
