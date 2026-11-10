// Original party routes set in chapter locations. Coordinates are world pixels.

const colors = { B: 'blue', R: 'red', I: 'item' };
const stop = (id, x, y, label, type = 'blue') => ({ id, x, y, label, type });
const say = (speaker, text) => ({ speaker, text });
const coins = amount => ({ type: 'coins', amount });
const warp = to => ({ type: 'warp', to });
const doubleDice = { type: 'item', item: 'double-dice' };
const choice = (id, label, effect, cost) => ({ id, label, effect, ...(cost ? { cost } : {}) });
const scene = (id, title, lines, effect, choices) => ({
  id, title, lines, effect, ...(choices ? { choices } : {}),
});

function regionTiles(id, width, height, cuts, rooms) {
  const xs = [0, cuts[0], cuts[1], width];
  const ys = [0, cuts[2], height];
  return rooms.map(([key, name], index) => {
    const col = index % 3;
    const row = Math.floor(index / 3);
    return {
      id: key, name, x: xs[col], y: ys[row],
      width: xs[col + 1] - xs[col], height: ys[row + 1] - ys[row],
      asset: `boards/${id}/${key}.png`,
    };
  });
}

function makeBoard(data) {
  const id = `chapter-${data.chapter}`;
  const spaces = new Map();

  function register(value, key, type) {
    if (typeof value === 'string') {
      const existing = spaces.get(value);
      if (!existing) throw new Error(`${id}: unknown route junction ${value}`);
      return existing;
    }
    const entry = Array.isArray(value) ? { id: key, x: value[0], y: value[1], type } : value;
    if (spaces.has(entry.id)) throw new Error(`${id}: duplicate space ${entry.id}`);
    const node = { ...entry, next: [] };
    spaces.set(node.id, node);
    return node;
  }

  function layPath({ name, points, pattern, spacing = data.spacing, label, cost }) {
    let count = 0;
    const nextKey = () => `${name}-${String(count + 1).padStart(3, '0')}`;
    const nextType = () => colors[pattern[count++ % pattern.length]];
    let from = register(points[0], nextKey(), nextType());
    for (const [index, point] of points.slice(1).entries()) {
      const to = register(point, nextKey(), nextType());
      const { x, y } = from;
      const slices = Math.max(1, Math.round(Math.hypot(to.x - x, to.y - y) / spacing));
      for (let part = 1; part <= slices; part++) {
        const ratio = part / slices;
        const step = part === slices ? to : register([
          Math.round(x + (to.x - x) * ratio), Math.round(y + (to.y - y) * ratio),
        ], nextKey(), nextType());
        from.next.push(index === 0 && part === 1 && label
          ? { to: step.id, label, ...(cost ? { cost } : {}) }
          : step.id);
        from = step;
      }
    }
  }

  layPath({ name: 'main', points: data.main, pattern: data.pattern });
  for (const path of data.paths) layPath(path);
  for (const space of spaces.values()) {
    if (space.next.length > 1) {
      space.next = space.next.map(exit => typeof exit === 'string'
        ? { to: exit, label: 'Main route' }
        : exit);
    }
  }
  for (const event of data.events) {
    const node = spaces.get(event.id);
    if (!node) throw new Error(`${id}: event space missing for ${event.id}`);
    node.type = 'event';
    node.event = event;
  }

  return {
    id, chapter: data.chapter, title: data.title,
    width: data.width, height: data.height, start: data.start, starSpots: data.stars,
    spaces: [...spaces.values()],
    regions: regionTiles(id, data.width, data.height, data.cuts, data.rooms),
    palette: data.palette,
  };
}

const cardKingdom = {
  chapter: 1, title: 'Card Kingdom', width: 3480, height: 1680, cuts: [1170, 2370, 850],
  palette: { ground: '#242447', route: '#cab7e6', shadow: '#34243d', accent: '#d69bfd' },
  rooms: [
    ['field', 'Field of Hopes and Dreams'], ['great-board', 'Great Board'], ['card-castle', 'Card Castle'],
    ['forest', 'Forest'], ['bake-sale', 'Bake Sale'], ['prison', 'Castle Dungeon'],
  ],
  start: 'field-gate', spacing: 64, pattern: 'BBBBRBBBBIBBBRBB',
  stars: ['lancer-bend', 'card-approach', 'bake-turn', 'forest-dip'],
  main: [
    stop('field-gate', 440, 455, 'Field Gate'), [158, 475], [218, 280], [410, 205],
    [620, 250], [810, 205], [1040, 285], stop('lancer-bend', 1190, 375, 'Lancer’s Bend'),
    [1370, 382], [1540, 275], stop('checker-gate', 1740, 262, 'Great Board Gate'),
    [1950, 305], [2120, 245], [2320, 280], [2560, 265],
    stop('card-approach', 2740, 368, 'Castle Approach'), [3000, 320], [3200, 458],
    [3270, 680], [3180, 885], [3190, 1100], stop('prison-gate', 3030, 1370, 'Dungeon Gate'),
    [2820, 1510], [2590, 1430], [2370, 1515], stop('bake-turn', 2180, 1380, 'Bake Sale Turn'),
    [1970, 1445], [1760, 1390], [1550, 1480], [1340, 1380],
    stop('forest-dip', 1130, 1240, 'Forest Dip'), [920, 1390], [700, 1490], [430, 1460],
    [240, 1300], [150, 1070], [220, 870], 'field-gate',
  ],
  paths: [
    { name: 'jigsaw', label: 'Jigsaw Camp', pattern: 'BBIRBB',
      points: ['field-gate', [475, 685], [700, 575], stop('jigsaw-camp', 915, 600, 'Jigsaw Camp'), 'lancer-bend'] },
    { name: 'oven', label: 'Bake Sale Shortcut', pattern: 'BBBRBI',
      points: ['bake-turn', [1840, 1140], stop('seam-stand', 1600, 1020, 'Bake Sale Stand'), [1330, 1070], 'forest-dip'] },
    { name: 'checkers', label: 'Checkered Hall', pattern: 'BBRIBB',
      points: ['checker-gate', [1810, 575], stop('rules-gate', 2070, 690, 'Checkered Hall'), [2350, 670], [2550, 555], 'card-approach'] },
    { name: 'cells', label: 'Dungeon Arcade', pattern: 'BRBBIB',
      points: ['prison-gate', [2830, 1120], stop('paper-run', 2720, 1000, 'Dungeon Arcade'), [2510, 1170], 'bake-turn'] },
  ],
  events: [
    scene('jigsaw-camp', 'A Piece of the Team', [
      say('Jigsaw Joe', 'Our team was one piece short. You can have the prize for showing up.'),
    ], coins(5)),
    scene('seam-stand', 'Bake Sale Leftovers', [
      say('Hathy', 'A cookie for now, or a bag for the road? I packed extra.'),
    ], coins(4), [choice('cookie', 'Take a cookie', coins(4)), choice('bag', 'Pack a Dice Set', doubleDice, 2)]),
    scene('rules-gate', 'Rouxls at the Gate', [
      say('Rouxls Kaard', 'A fee of three coineth opens the east gate. The long way has no ruleth at all.'),
    ], coins(0), [choice('gate', 'Pay 3 for the east gate', warp('card-approach'), 3), choice('hall', 'Walk the hall', coins(0))]),
    scene('paper-run', 'Lancer’s Spare Track', [
      say('Lancer', 'I made two tracks! You can ride mine, or keep what fell out of my pockets.'),
    ], coins(3), [choice('ride', 'Ride to the forest', warp('forest-dip')), choice('pockets', 'Pick up the coins', coins(3))]),
  ],
};

const cyberWorld = {
  chapter: 2, title: 'Cyber World', width: 3720, height: 1840, cuts: [1210, 2510, 920],
  palette: { ground: '#101933', route: '#74dbe2', shadow: '#183d63', accent: '#51fff4' },
  rooms: [
    ['cyber-field', 'Cyber Field'], ['coaster', 'Cyber Coaster'], ['mansion', 'Queen’s Mansion'],
    ['trash-zone', 'Trash Zone'], ['cyber-city', 'Cyber City'], ['acid-tunnel', 'Acid Tunnel'],
  ],
  start: 'field-terminal', spacing: 67, pattern: 'BBBBIBBRBBBRBBBBB',
  stars: ['wire-junction', 'city-ramp', 'queen-approach', 'canal-dock'],
  main: [
    stop('field-terminal', 245, 390, 'Field Terminal'), stop('field-stage', 495, 275, 'Field Stage'), [730, 342],
    stop('wire-junction', 975, 450, 'Cable Crossing'), [1210, 560], [1470, 495], [1710, 580],
    stop('coaster-dip', 1925, 745, 'Coaster Dip'), [2130, 845], [2380, 730],
    stop('queen-approach', 2630, 610, 'Mansion Approach'), [2770, 365], [3010, 250],
    [3250, 310], stop('mansion-exit', 3500, 505, 'East Mansion Lift'), [3550, 775],
    [3440, 1050], stop('canal-dock', 3470, 1320, 'Canal Dock'), [3275, 1570],
    [2970, 1600], [2690, 1500], [2460, 1660], [2150, 1700],
    stop('city-ramp', 1940, 1510, 'City Ramp'), [1750, 1270], [1470, 1370],
    [1190, 1510], stop('scrap-crossing', 900, 1585, 'Scrap Crossing'), [580, 1550],
    [330, 1355], [185, 1130], [265, 875], [160, 610], 'field-terminal',
  ],
  paths: [
    { name: 'skyway', label: 'High-Speed Coaster', pattern: 'BRRBBI', spacing: 71,
      points: ['wire-junction', [1190, 205], [1460, 190], stop('wire-terminal', 1710, 270, 'Coaster Service Box'), [2040, 185], [2390, 220], 'queen-approach'] },
    { name: 'traffic', label: 'City Service Ramp', pattern: 'BBIRRB',
      points: ['coaster-dip', [2030, 1050], stop('car-stand', 2175, 1220, 'Traffic Stand'), [2060, 1360], 'city-ramp'] },
    { name: 'mansion', label: 'Mansion Lobby', pattern: 'BBIBB',
      points: ['queen-approach', [2840, 730], stop('potassium-lab', 3070, 800, 'Queen’s Test Room'), [3330, 710], 'mansion-exit'] },
    { name: 'acid', label: 'Acid Canal Ferry', pattern: 'BRBBI',
      points: ['canal-dock', [3200, 1295], [2980, 1170], stop('acid-ferry', 2710, 1230, 'Ferry Depot'), [2450, 1390], 'city-ramp'] },
    { name: 'alley', label: 'Trash Zone Alley', pattern: 'BRRIBB',
      points: ['scrap-crossing', [825, 1380], stop('coupon-lane', 710, 1115, 'Coupon Alley'), [580, 860], [525, 640], 'field-terminal'] },
    { name: 'maintenance', label: 'Maintenance Lift', pattern: 'BRBIB',
      points: ['potassium-lab', [3090, 1010], [2880, 1060], 'acid-ferry'] },
  ],
  events: [
    scene('field-stage', 'The Opening Beat', [
      say('Sweet', 'You got here before sound check. We can split the change from the meter.'),
    ], coins(4)),
    scene('wire-terminal', 'A Spare Charge', [
      say('Plugboy', 'The meter says you have credit left. Want it in coins or a ride downtown?'),
    ], coins(5), [choice('credit', 'Collect 5 coins', coins(5)), choice('service', 'Take the city service ramp', warp('city-ramp'))]),
    scene('car-stand', 'Crossing Shift', [
      say('Noelle', 'I cleared a lane for you. These two dice were left in the glove box, if you want them.'),
    ], doubleDice),
    scene('potassium-lab', 'Queen’s Button Test', [
      say('Queen', 'There Are Two Buttons. The Quiet One Is Worth Six Coins. The Other Is A Ferry.'),
    ], coins(6), [choice('quiet', 'Press the quiet button', coins(6)), choice('ferry', 'Press the ferry button', warp('canal-dock'))]),
    scene('acid-ferry', 'Ferry Change', [
      say('Swatch', 'There is no ticket charge today. Someone did leave this change on the seat.'),
    ], coins(4)),
    scene('coupon-lane', 'Coupon Alley Deal', [
      say('Spamton', 'I CAN GET YOU TO THE [Mansion] FOR THREE COINS. OR TAKE TWO BACK AND WALK!'),
    ], coins(2), [choice('ride', 'Pay 3 for a mansion ride', warp('queen-approach'), 3), choice('cash', 'Take 2 coins', coins(2))]),
  ],
};

const tvWorld = {
  chapter: 3, title: 'TV World', width: 3360, height: 1680, cuts: [1080, 2220, 830],
  palette: { ground: '#28213f', route: '#f1bc81', shadow: '#4c284f', accent: '#ffac66' },
  rooms: [
    ['green-room', 'Green Room'], ['desert-board', 'Desert Board'], ['island-board', 'Island Board'],
    ['cold-place', 'Cold Place'], ['couch-cliffs', 'Couch Cliffs'], ['tv-studio', 'TV Studio'],
  ],
  start: 'green-door', spacing: 61, pattern: 'BBIBBBRBBBBIBBBR',
  stars: ['desert-entry', 'desert-exit', 'island-signal', 'stage-door', 'couch-junction'],
  main: [
    stop('green-door', 220, 515, 'Green Room Door'), [395, 315], [640, 235], [900, 300],
    stop('desert-entry', 1110, 360, 'Desert Entrance'), [1350, 205], [1540, 315], [1770, 220],
    stop('desert-exit', 1990, 385, 'Desert Exit'), [2250, 315], [2450, 205], [2680, 305],
    stop('island-signal', 2950, 270, 'Island Signal'), [3150, 420], [3215, 650], [3040, 820],
    stop('stage-door', 2890, 1060, 'Stage Door'), [3150, 1220], [3130, 1450], [2890, 1510],
    [2670, 1370], [2450, 1530], [2190, 1465], stop('couch-junction', 1920, 1330, 'Couch Junction'),
    [1690, 1480], [1400, 1380], [1160, 1510], [860, 1500], stop('cold-bridge', 615, 1370, 'Cold Bridge'),
    [330, 1445], [160, 1250], [255, 1040], [135, 830], 'green-door',
  ],
  paths: [
    { name: 'greenroom', label: 'Green Room Rehearsal', pattern: 'BBIBBB',
      points: ['green-door', [490, 610], stop('cue-table', 760, 600, 'Cue Table'), [985, 650], 'desert-entry'] },
    { name: 'desert', label: 'Desert Oasis', pattern: 'BBRIBB',
      points: ['desert-entry', [1280, 680], [1490, 575], stop('oasis-prop', 1645, 730, 'Oasis Prop'), [1860, 625], 'desert-exit'] },
    { name: 'island', label: 'Island Pier', pattern: 'BRBBI',
      points: ['island-signal', [2770, 510], stop('island-pier', 2650, 670, 'Island Pier'), [2700, 910], 'stage-door'] },
    { name: 'studio', label: 'Studio Backstage', pattern: 'BBIBBR',
      points: ['stage-door', [2665, 1120], stop('tape-door', 2430, 1125, 'Tape Door'), [2170, 1170], 'couch-junction'] },
    { name: 'weather', label: 'Weather Channel', pattern: 'BBRIBB',
      points: ['couch-junction', [1700, 1110], [1410, 1050], [1090, 1100], stop('cold-signal', 835, 990, 'Weather Tower'), [710, 1150], 'cold-bridge'] },
    { name: 'channel-switch', label: 'Switch to Weather', pattern: 'BBIBR',
      points: ['cue-table', [760, 750], [920, 840], 'cold-signal'] },
    { name: 'retake', label: 'Replay the Desert', pattern: 'BRIBB', cost: 2,
      points: ['island-pier', [2470, 820], [2220, 830], [1950, 765], 'oasis-prop'] },
  ],
  events: [
    scene('cue-table', 'Two-Handed Rehearsal', [
      say('Tenna', 'Today’s contestant can use both hands. Take an extra block before we go live!'),
    ], doubleDice),
    scene('oasis-prop', 'Change of Scenery', [
      say('Ralsei', 'The oasis is real enough to have a tip jar. Should we help move the set?'),
    ], coins(4), [choice('tips', 'Keep the tip', coins(4)), choice('scene', 'Switch to the Island Board', warp('island-signal'))]),
    scene('island-pier', 'A Studio Snack', [
      say('Pippins', 'I counted the snacks wrong. Take these before the prop department counts them too.'),
    ], coins(5)),
    scene('tape-door', 'Fast Forward', [
      say('Ramb', 'Fancy skipping the adverts? I can get you back to the Green Room.'),
    ], coins(3), [choice('skip', 'Fast-forward to the Green Room', warp('green-door')), choice('stay', 'Stay for the adverts', coins(3))]),
    scene('cold-signal', 'The Weather Channel', [
      say('Lanino', 'Clear skies across the studio. The only thing falling today should be these coins.'),
      say('Elnina', 'Keep three for an umbrella, just in case.'),
    ], coins(3)),
  ],
};

const sanctuary = {
  chapter: 4, title: 'The Sanctuaries', width: 3600, height: 2000, cuts: [1180, 2400, 1000],
  palette: { ground: '#212238', route: '#c2cced', shadow: '#313552', accent: '#d5c289' },
  rooms: [
    ['dark-sanctuary', 'Dark Sanctuary'], ['gold-piano', 'Gold Piano'], ['second-sanctuary', 'Second Sanctuary'],
    ['library', 'Old Man’s Study'], ['bell-hall', 'Bell Hall'], ['third-sanctuary', 'Third Sanctuary'],
  ],
  start: 'sanctuary-entry', spacing: 68, pattern: 'BBBRBBBIBBBRBB',
  stars: ['vestry-arch', 'piano-landing', 'second-gate', 'third-candle'],
  main: [
    stop('sanctuary-entry', 620, 620, 'Sanctuary Entrance'), stop('foyer-note', 325, 550, 'Offering Foyer'), [185, 300], [390, 175],
    [620, 300], stop('vestry-arch', 870, 275, 'Vestry Arch'), [1110, 370], [1280, 560],
    [1550, 580], stop('piano-landing', 1780, 420, 'Piano Landing'), [2050, 440], [2250, 615],
    [2500, 580], [2700, 395], stop('second-gate', 2950, 425, 'Second Sanctuary Gate'),
    [3220, 480], [3370, 720], [3300, 1020], [3425, 1290], [3260, 1530],
    stop('third-candle', 3020, 1640, 'Third Sanctuary Candle'), [2750, 1720], [2510, 1580],
    [2260, 1780], [2010, 1820], stop('bell-crossing', 1780, 1650, 'Bell Crossing'), [1570, 1400],
    [1310, 1450], [1100, 1680], [840, 1810], stop('study-landing', 560, 1700, 'Study Landing'),
    [310, 1630], [160, 1410], [350, 1170], [200, 1030], 'sanctuary-entry',
  ],
  paths: [
    { name: 'vestry', label: 'Vestry Stairs', pattern: 'BBIRB',
      points: ['sanctuary-entry', [805, 710], [925, 550], 'vestry-arch'] },
    { name: 'organ', label: 'High Organ Walk', pattern: 'BBIBRB',
      points: ['vestry-arch', [1110, 165], [1390, 170], stop('organ-prompt', 1610, 240, 'Organ Loft'), 'piano-landing'] },
    { name: 'ledge', label: 'Mask Ledge', pattern: 'BRRBBB',
      points: ['second-gate', [2970, 720], stop('mask-ledge', 2840, 965, 'Mask Ledge'), [2690, 1180], [2770, 1450], 'third-candle'] },
    { name: 'bell', label: 'Bell Tower Walk', pattern: 'BBIBRB',
      points: ['piano-landing', [1850, 720], [2100, 935], stop('bell-rope', 2260, 1195, 'Bell Tower Rope'), [2050, 1450], 'bell-crossing'] },
    { name: 'study', label: 'The Old Study', pattern: 'BIBBRB',
      points: ['bell-crossing', [1755, 1250], [1250, 1030], stop('study-desk', 990, 1160, 'Study Desk'), [765, 1400], 'study-landing'] },
    { name: 'candles', label: 'Candle Gallery', pattern: 'IBBBRB',
      points: ['study-landing', [540, 1340], stop('final-candle', 650, 1060, 'Candle Gallery'), [575, 820], 'sanctuary-entry'] },
    { name: 'cloister', label: 'Cross the Cloister', pattern: 'BBIBR',
      points: ['bell-rope', [2440, 1080], [2580, 930], 'mask-ledge'] },
  ],
  events: [
    scene('foyer-note', 'Change at the Door', [
      say('Ralsei', 'The plate has a little slot. Someone left some change in it for the next traveler.'),
    ], coins(3)),
    scene('organ-prompt', 'Two Chords', [
      say('Gerson', 'One chord shakes loose the offering. The other will open that door over there.'),
    ], coins(4), [choice('offering', 'Play the first chord', coins(4)), choice('door', 'Play the second chord', warp('second-gate'))]),
    scene('mask-ledge', 'A Very Fine Mask', [
      say('Jackenstein', 'YOUR HAT LOOKS COLD. HERE. THE SILVER LINING IS REAL.'),
    ], coins(5)),
    scene('bell-rope', 'The Bell Rope', [
      say('Susie', 'Bet I can ring it from here. Wait. That rope leads straight to the last hall.'),
    ], coins(2), [choice('ring', 'Ring the bell', coins(2)), choice('rope', 'Take the rope to the last hall', warp('third-candle'))]),
    scene('study-desk', 'Two Marginal Notes', [
      say('Gerson', 'I used one block as a paperweight. Now there are two. That’s how you know I’m old.'),
    ], doubleDice),
    scene('final-candle', 'Candles in the Gallery', [
      say('Ralsei', 'These are for everyone coming after us. I can pay for this one.'),
    ], coins(4)),
  ],
};

const flowerKingdom = {
  chapter: 5, title: 'Flower Kingdom', width: 3840, height: 1920, cuts: [1280, 2560, 980],
  palette: { ground: '#392341', route: '#efc28a', shadow: '#59334c', accent: '#f89f7c' },
  rooms: [
    ['garden', 'Garden'], ['cliffs', 'Cliffs'], ['floral-castle', 'Flower Castle'],
    ['shrine', 'Garden Shrine'], ['second-diner', 'Second Diner'], ['castle-roof', 'Castle Rooftop'],
  ],
  start: 'garden-gate', spacing: 70, pattern: 'BBIBBBRBBIBBBRBB',
  stars: ['petal-arch', 'cliff-stairs', 'diner-fork', 'roof-parapet', 'shrine-turn'],
  main: [
    stop('garden-gate', 220, 580, 'Garden Gate'), [365, 355], [620, 230], [870, 370],
    stop('petal-arch', 1120, 455, 'Petal Arch'), [1330, 330], [1540, 460], [1740, 295],
    [1980, 245], stop('cliff-stairs', 2220, 390, 'Cliff Stairs'), [2440, 510], [2680, 365],
    [2940, 275], [3240, 385], stop('castle-porch', 3480, 580, 'Castle Porch'), [3670, 805],
    [3550, 1020], [3670, 1260], stop('roof-parapet', 3460, 1490, 'Roof Parapet'), [3180, 1610],
    [2920, 1745], [2650, 1590], [2380, 1740], stop('diner-fork', 2120, 1610, 'Diner Fork'),
    [1850, 1710], [1580, 1510], [1300, 1690], [1000, 1760], stop('shrine-turn', 745, 1550, 'Shrine Turn'),
    [480, 1660], [255, 1520], [175, 1240], [360, 1005], [230, 820], 'garden-gate',
  ],
  paths: [
    { name: 'petals', label: 'Garden Market', pattern: 'BBIBBB',
      points: ['garden-gate', [505, 640], stop('petal-booth', 750, 655, 'Garden Market'), [940, 720], 'petal-arch'] },
    { name: 'cliffs', label: 'Echo Cliff Traverse', pattern: 'BRRBBI',
      points: ['petal-arch', [1400, 760], [1675, 730], stop('echo-cliff', 1900, 690, 'Echo Cliff'), [2130, 630], 'cliff-stairs'] },
    { name: 'bridges', label: 'Cross the Castle Terrace', pattern: 'BRBBIB',
      points: ['cliff-stairs', [2400, 755], [2650, 820], stop('terrace-sign', 2920, 850, 'Castle Terrace Sign'), [3215, 840], 'castle-porch'] },
    { name: 'roof', label: 'Diner Roof Walk', pattern: 'BBBRIB',
      points: ['roof-parapet', [3220, 1320], stop('roof-sign', 2900, 1250, 'Rooftop Sign'), [2630, 1330], [2340, 1380], 'diner-fork'] },
    { name: 'diner', label: 'Diner and Shrine', pattern: 'BBIBRB',
      points: ['diner-fork', [1950, 1290], stop('diner-counter', 1670, 1185, 'Diner Counter'), [1375, 1290], [1090, 1370], 'shrine-turn'] },
    { name: 'irrigation', label: 'Shrine Water Walk', pattern: 'BRBBIB',
      points: ['shrine-turn', [690, 1280], stop('water-gauge', 800, 1080, 'Shrine Water Gauge'), [580, 910], 'garden-gate'] },
    { name: 'terrace-stairs', label: 'Take the Diner Steps', pattern: 'BBBRI',
      points: ['terrace-sign', [2580, 1015], [2250, 1040], [1910, 1105], 'diner-counter'] },
  ],
  events: [
    scene('petal-booth', 'Garden Market', [
      say('Green', 'Help me carry the flowers? The market has a little money left for hands that help.'),
    ], coins(5)),
    scene('echo-cliff', 'Call Across the Cliffs', [
      say('Seth', 'You can hear the roof from here if you know which ledge to call from.'),
    ], coins(3), [choice('climb', 'Take the stair to the roof', warp('roof-parapet')), choice('stay', 'Collect 3 coins', coins(3))]),
    scene('terrace-sign', 'A Terrace Detour', [
      say('Blue', 'I put the sign back the right way up. The long road is yours, unless you’d rather take the diner steps.'),
    ], coins(4), [choice('steps', 'Head to the diner', warp('diner-fork')), choice('walk', 'Stay on the terrace', coins(4))]),
    scene('diner-counter', 'Second Diner Special', [
      say('Yellow', 'You’ve got a table for two dice. Want the set, or the cash left under the plate?'),
    ], coins(4), [choice('dice', 'Order the Dice Set', doubleDice, 2), choice('change', 'Keep the change', coins(4))]),
    scene('water-gauge', 'Water for the Garden', [
      say('Aqua', 'This valve fills the garden beds. Try it while I watch the gauge.'),
    ], coins(6)),
    scene('roof-sign', 'A Rooftop Welcome', [
      say('Flowery', 'What a climb! Take these while you can still see where they fall.'),
    ], coins(5)),
  ],
};

export const boards = [cardKingdom, cyberWorld, tvWorld, sanctuary, flowerKingdom].map(makeBoard);
