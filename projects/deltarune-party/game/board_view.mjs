const WIDTH = 240;
const HEIGHT = 180;
const PAINT = ['#5ca6ff', '#ee677c', '#76cb8e', '#f9ca62'];
const PANELS = ['blue', 'red', 'green', 'yellow'];
const SPACE_COLORS = {blue: '#58a5f0', red: '#e7636b', item: '#bd8cea', event: '#74bd78'};
const assetPath = path => '/assets/' + path.split('/').map(encodeURIComponent).join('/');
const clamp = (value, low, high) => Math.min(high, Math.max(low, value));
const textId = id => String(id);

export const playerName = id => id ? id[0].toUpperCase() + id.slice(1) : '';

function label(ctx, text, x, y, {size = 9, color = '#fff7f5', align = 'left', shade = '#21152c'} = {}) {
  ctx.font = `bold ${size}px monospace`;
  ctx.textBaseline = 'top';
  ctx.textAlign = align;
  if (shade) {
    ctx.fillStyle = shade;
    ctx.fillText(text, Math.round(x + 1), Math.round(y + 1));
  }
  ctx.fillStyle = color;
  ctx.fillText(text, Math.round(x), Math.round(y));
}

function oval(ctx, x, y, rx, ry, color) {
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2);
  ctx.fill();
}

function fit(board, width = WIDTH, height = HEIGHT) {
  return Math.min(width / board.width, height / board.height);
}

function tween(progress) {
  return progress * progress * (3 - 2 * progress);
}

function rankOf(player, state) {
  if (state.standings?.length) return 1 + state.standings.indexOf(player.id);
  return 1 + state.players.filter(other =>
    other.stars > player.stars || (other.stars === player.stars && other.coins > player.coins)).length;
}

export class BoardView {
  constructor(field, overview, onAssets) {
    this.field = field;
    this.overview = overview;
    this.ctx = field.getContext('2d');
    this.mini = overview.getContext('2d');
    this.onAssets = onAssets;
    this.images = new Map();
    this.poses = new Map();
    this.reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.queued = false;
    this.camera = {x: 0, y: 0, zoom: 1};
  }

  picture(path) {
    if (!this.images.has(path)) {
      const image = new Image();
      const record = {image, status: 'pending'};
      this.images.set(path, record);
      const finish = status => {
        record.status = status;
        this.onAssets?.();
        this.repaint();
      };
      image.onload = () => finish('ready');
      image.onerror = () => finish('missing');
      image.src = assetPath(path);
    }
    const record = this.images.get(path);
    return record.status === 'ready' ? record.image : null;
  }

  assetSummary() {
    if (!this.board) return '';
    const regions = this.board.regions ?? [];
    const unavailable = regions.filter(region => !region.asset || this.images.get(region.asset)?.status === 'missing');
    return unavailable.length ? `Map art unavailable in ${unavailable.length} of ${regions.length} regions. Route tiles remain playable.` : '';
  }

  select(board, state) {
    this.board = board;
    this.state = state;
    this.nodes = new Map(board.spaces.map(space => [textId(space.id), space]));
    this.edges = board.spaces.flatMap(from => (from.next ?? []).map(link => {
      const to = this.nodes.get(textId(typeof link === 'object' ? link.to : link));
      return [from, to];
    })).filter(([, to]) => to);
    this.poses.clear();
    this.animation = null;
    this.dice = null;
    this.reward = null;
    this.browsing = !state;
    this.resetCamera();
    this.onAssets?.();
    this.repaint();
  }

  setState(state) {
    this.state = state;
    const scores = state.players.map(player =>
      `${playerName(player.id)} ${player.stars} stars and ${player.coins} coins`).join('. ');
    this.overview.setAttribute('aria-label', `Turn ${state.round} of ${state.rounds}. ${scores}`);
    for (const player of state.players) {
      const space = this.space(player.space);
      const existing = this.poses.get(player.id);
      if (space && (!existing || existing.space !== player.space)) {
        this.poses.set(player.id, {x: space.x, y: space.y, space: player.space, face: existing?.face ?? 'down'});
      }
    }
    this.repaint();
  }

  space(id) {
    return this.nodes?.get(textId(id));
  }

  activePose() {
    return this.poses.get(this.state?.active) ?? this.space(this.board?.start);
  }

  resetCamera() {
    const active = this.activePose();
    const {width, height} = this.board;
    this.camera = this.browsing
      ? {x: width / 2, y: height / 2, zoom: fit(this.board, WIDTH - 14, HEIGHT - 16)}
      : {x: active?.x ?? width / 2, y: active?.y ?? height / 2, zoom: 1};
    this.limitCamera();
  }

  browse(on) {
    this.browsing = on;
    this.resetCamera();
    this.repaint();
  }

  limitCamera() {
    const {zoom} = this.camera;
    const halfW = WIDTH / (zoom * 2);
    const halfH = HEIGHT / (zoom * 2);
    this.camera.x = this.board.width <= 2 * halfW ? this.board.width / 2 : clamp(this.camera.x, halfW, this.board.width - halfW);
    this.camera.y = this.board.height <= 2 * halfH ? this.board.height / 2 : clamp(this.camera.y, halfH, this.board.height - halfH);
  }

  pan(dx, dy) {
    this.camera.x += dx / this.camera.zoom;
    this.camera.y += dy / this.camera.zoom;
    this.limitCamera();
    this.repaint();
  }

  zoom(factor) {
    this.camera.zoom = clamp(this.camera.zoom * factor, fit(this.board, WIDTH - 14, HEIGHT - 16), 2);
    this.limitCamera();
    this.repaint();
  }

  animateMove(event) {
    const from = this.space(event.from);
    const to = this.space(event.to);
    if (!from || !to) return Promise.resolve();
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const face = Math.abs(dx) > Math.abs(dy) ? (dx < 0 ? 'left' : 'right') : (dy < 0 ? 'up' : 'down');
    return new Promise(resolve => {
      this.animation = {from, to, face, player: event.player, resolve, begin: performance.now(),
        duration: this.reducedMotion ? 1 : clamp(Math.hypot(dx, dy) * 1.7, 180, 440)};
      this.repaint();
    });
  }

  repaint() {
    if (this.queued) return;
    this.queued = true;
    requestAnimationFrame(time => {
      this.queued = false;
      this.render(time);
    });
  }

  render(time) {
    if (!this.board) return;
    const move = this.animation;
    if (move) {
      const progress = clamp((time - move.begin) / move.duration, 0, 1);
      const u = tween(progress);
      this.poses.set(move.player, {
        x: move.from.x + (move.to.x - move.from.x) * u,
        y: move.from.y + (move.to.y - move.from.y) * u,
        space: progress < 1 ? move.from.id : move.to.id,
        face: move.face, stride: progress < 1 ? 1 + Math.floor(progress * 9) % 3 : 0,
        lift: Math.sin(progress * Math.PI) * 6,
      });
      if (progress === 1) {
        this.animation = null;
        move.resolve();
      }
    }
    let cameraMoving = false;
    if (!this.browsing && this.state) {
      const target = this.activePose();
      const targetX = clamp(target.x, WIDTH / 2, this.board.width - WIDTH / 2);
      const targetY = clamp(target.y, HEIGHT / 2, this.board.height - HEIGHT / 2);
      const distance = Math.hypot(targetX - this.camera.x, targetY - this.camera.y);
      cameraMoving = distance > .65;
      const factor = this.reducedMotion || !cameraMoving ? 1 : .25;
      this.camera.x += (targetX - this.camera.x) * factor;
      this.camera.y += (targetY - this.camera.y) * factor;
      this.limitCamera();
    }
    this.drawField();
    if (this.state) this.drawOverview();
    if (this.animation || cameraMoving) this.repaint();
  }

  drawField() {
    const ctx = this.ctx;
    const board = this.board;
    const {x, y, zoom} = this.camera;
    const offsetX = WIDTH / 2 - Math.round(x * zoom);
    const offsetY = HEIGHT / 2 - Math.round(y * zoom);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = board.palette?.shadow ?? '#19162c';
    ctx.fillRect(0, 0, WIDTH, HEIGHT);
    ctx.setTransform(zoom, 0, 0, zoom, offsetX, offsetY);
    ctx.fillStyle = board.palette?.ground ?? '#262443';
    ctx.fillRect(0, 0, board.width, board.height);
    for (const region of board.regions ?? []) {
      const {x: rx, y: ry, width, height} = region;
      if (rx + width < -offsetX / zoom || ry + height < -offsetY / zoom ||
          rx > (WIDTH - offsetX) / zoom || ry > (HEIGHT - offsetY) / zoom) continue;
      const art = region.asset && this.picture(region.asset);
      if (art) ctx.drawImage(art, rx, ry, width, height);
      else {
        ctx.fillStyle = board.palette?.shadow ?? '#302a4b';
        ctx.fillRect(rx, ry, width, height);
        ctx.strokeStyle = board.palette?.accent ?? '#8178a3';
        ctx.lineWidth = 2 / zoom;
        ctx.strokeRect(rx, ry, width, height);
        if (zoom > .45) label(ctx, region.name, rx + 6, ry + 6, {size: 9});
      }
    }
    const atlas = zoom < .30;
    const tileRadius = atlas ? 2.25 / zoom : 11;
    const star = this.state?.star ?? board.starSpots?.[0];
    const selected = new Set(this.state?.phase === 'branch' ? this.state.options.map(option => textId(option.id)) : []);
    this.drawRoutes(ctx, atlas ? 2.6 / zoom : 8, board.palette?.route ?? '#d0bad6');
    for (const space of board.spaces) {
      const {x, y} = space;
      if (textId(space.id) === textId(star)) {
        oval(ctx, x, y, tileRadius + 3 / zoom, tileRadius * .63 + 3 / zoom, '#f8cd6a');
      } else if (selected.has(textId(space.id))) {
        oval(ctx, x, y, tileRadius + 4 / zoom, tileRadius * .63 + 4 / zoom, '#f7f4ff');
      }
      oval(ctx, x, y + 1 / zoom, tileRadius, tileRadius * .64, '#2b1e36');
      oval(ctx, x, y - 1 / zoom, tileRadius * .88, tileRadius * .47, SPACE_COLORS[space.type] ?? '#a8a0d8');
      if (!atlas && (space.type === 'event' || space.type === 'item')) {
        label(ctx, space.type === 'event' ? '?' : '!', x, y - 7, {size: 11, align: 'center'});
      }
      if (textId(space.id) === textId(star)) {
        const icon = this.picture('mpds/board-star.png');
        if (icon) ctx.drawImage(icon, x - 7 / zoom, y - 16 / zoom, 14 / zoom, 14 / zoom);
        else label(ctx, '*', x, y - 13 / zoom, {size: 12 / zoom, align: 'center', color: '#ffe38a'});
      }
    }
    if (this.state) this.drawPlayers(ctx, atlas);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.lineWidth = 1;
    const current = this.state?.players.find(player => player.id === this.state.active);
    const region = current && this.board.regions?.find(({x, y, width, height}) => {
      const position = this.activePose();
      return position.x >= x && position.y >= y && position.x < x + width && position.y < y + height;
    });
    const heading = this.browsing ? board.title : (region?.name ?? board.title);
    ctx.fillStyle = '#151126';
    ctx.fillRect(0, 0, WIDTH, 15);
    label(ctx, heading, 5, 3, {color: '#eee8f7', shade: null});
    if (this.browsing) label(ctx, `${Math.round(zoom * 100)}%`, WIDTH - 5, 3, {align: 'right', color: '#dfbd6b', shade: null});
    if (!this.browsing && this.dice) this.drawDice(ctx);
    if (!this.browsing && this.reward) {
      label(ctx, this.reward, WIDTH / 2, 117, {size: 14, align: 'center', color: '#ffdb75'});
    }
  }

  drawRoutes(ctx, width, color) {
    const stroke = (lineWidth, strokeStyle) => {
      ctx.lineWidth = lineWidth;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.strokeStyle = strokeStyle;
      ctx.beginPath();
      for (const [from, to] of this.edges) {
        ctx.moveTo(from.x, from.y);
        ctx.lineTo(to.x, to.y);
      }
      ctx.stroke();
    };
    stroke(width, '#3b2c50');
    stroke(width * .47, color);
  }

  drawPlayers(ctx, atlas) {
    const ordered = this.state.players.map((player, index) => ({player, index, pose: this.poses.get(player.id) ?? this.space(player.space)}))
      .filter(({pose}) => pose).sort((a, b) => a.pose.y - b.pose.y);
    for (const {player, index, pose} of ordered) {
      const sharing = this.state.players.filter(candidate => candidate.space === player.space);
      const slot = sharing.findIndex(candidate => candidate.id === player.id);
      const x = pose.x + (atlas ? 0 : (slot - (sharing.length - 1) / 2) * 21);
      const y = pose.y + (!atlas && sharing.length > 1 ? (slot % 2 ? 4 : -4) : 0);
      if (atlas) {
        const radius = (this.state.active === player.id ? 4.5 : 3.2) / this.camera.zoom;
        oval(ctx, x, y, radius, radius, '#1a152d');
        oval(ctx, x, y, radius - 1 / this.camera.zoom, radius - 1 / this.camera.zoom, PAINT[index]);
        continue;
      }
      oval(ctx, x, y + 1, 9, 3, '#281e35');
      if (this.state.active === player.id) oval(ctx, x, y, 9, 3, '#f5c869');
      const face = pose.face ?? 'down';
      const stride = pose.stride ?? 0;
      const image = this.picture(`cast/${player.id}-${face}-${stride}.png`);
      if (image) {
        const h = Math.min(37, image.height);
        const w = Math.round(image.width * h / image.height);
        ctx.drawImage(image, Math.round(x - w / 2), Math.round(y - h - (pose.lift ?? 0)), w, h);
      } else {
        ctx.fillStyle = PAINT[index];
        ctx.fillRect(Math.round(x - 5), Math.round(y - 14), 10, 13);
        label(ctx, player.id[0].toUpperCase(), x, y - 13, {align: 'center'});
      }
    }
  }

  drawDice(ctx) {
    const {values, spinning} = this.dice;
    for (let index = 0; index < values.length; index++) {
      const face = values[index];
      const x = WIDTH / 2 + (index - (values.length - 1) / 2) * 38;
      const texture = values.length > 1 && spinning && this.picture(`mpds/double-dice-roll/${String(face).padStart(2, '0')}.png`);
      if (texture) ctx.drawImage(texture, x - 14, 36, 28, 35);
      else {
        ctx.fillStyle = spinning ? '#695694' : '#233d64';
        ctx.fillRect(x - 15, 38, 30, 29);
        ctx.strokeStyle = '#f9d479';
        ctx.strokeRect(x - 15.5, 37.5, 31, 30);
        const icon = face < 10 && this.picture(`mpds/dice-${face}.png`);
        if (icon) ctx.drawImage(icon, x - 10, 43, 20, 20);
        else label(ctx, String(face), x, 43, {size: 18, align: 'center'});
      }
    }
    if (values.length > 1 && !spinning) {
      label(ctx, values.join(' + ') + ' = ' + values.reduce((sum, n) => sum + n, 0), WIDTH / 2, 75, {size: 12, align: 'center', color: '#ffe18a'});
    }
  }

  drawOverview() {
    const ctx = this.mini;
    const board = this.board;
    const state = this.state;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = '#d8cbea';
    ctx.fillRect(0, 0, WIDTH, HEIGHT);
    for (let y = 0; y < HEIGHT; y += 12) for (let x = y % 24; x < WIDTH; x += 24) {
      ctx.fillStyle = '#e9def2';
      ctx.fillRect(x, y, 12, 12);
    }
    const scale = fit(board, 143, 126);
    const ox = (WIDTH - board.width * scale) / 2;
    const oy = (HEIGHT - board.height * scale) / 2;
    ctx.setTransform(scale, 0, 0, scale, ox, oy);
    for (const region of board.regions ?? []) {
      ctx.fillStyle = '#b4a5cc';
      ctx.fillRect(region.x, region.y, region.width, region.height);
    }
    this.drawRoutes(ctx, 2.4 / scale, '#fcf2fa');
    for (const space of board.spaces) {
      oval(ctx, space.x, space.y, 1.1 / scale, 1.1 / scale, SPACE_COLORS[space.type] ?? '#927bbc');
    }
    const star = this.space(state.star);
    if (star) oval(ctx, star.x, star.y, 2.8 / scale, 2.8 / scale, '#d38b37');
    if (!this.browsing) {
      ctx.lineWidth = 1 / scale;
      ctx.strokeStyle = '#71528c';
      ctx.strokeRect(this.camera.x - WIDTH / 2, this.camera.y - HEIGHT / 2, WIDTH, HEIGHT);
    }
    state.players.forEach((player, index) => {
      const pose = this.poses.get(player.id) ?? this.space(player.space);
      if (!pose) return;
      const r = (player.id === state.active ? 3.3 : 2.3) / scale;
      oval(ctx, pose.x, pose.y, r + 1 / scale, r + 1 / scale, '#302242');
      oval(ctx, pose.x, pose.y, r, r, PAINT[index]);
    });
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.lineWidth = 1;
    label(ctx, board.title, WIDTH / 2, 7, {size: 10, align: 'center', color: '#402958', shade: null});
    state.players.forEach((player, index) => this.drawPanel(ctx, player, index, rankOf(player, state)));
    const strip = this.picture('mpds/board-turn.png');
    if (strip) {
      ctx.drawImage(strip, 71, 164);
      label(ctx, String(state.round), 119, 165);
      label(ctx, String(state.rounds), 148, 165);
    } else {
      ctx.fillStyle = '#523e6b';
      ctx.fillRect(75, 163, 90, 15);
      label(ctx, `Turn ${state.round}/${state.rounds}`, 120, 166, {align: 'center'});
    }
  }

  drawPanel(ctx, player, index, rank) {
    const x = index % 2 ? 182 : 4;
    const y = index < 2 ? 19 : 108;
    const panel = this.picture(`mpds/board-panel-${PANELS[index]}-blue.png`);
    ctx.globalAlpha = .72;
    if (panel) ctx.drawImage(panel, x, y, 54, 61);
    else {
      ctx.fillStyle = PAINT[index];
      ctx.fillRect(x, y, 54, 61);
    }
    ctx.globalAlpha = 1;
    const counter = this.picture('mpds/board-counter.png');
    if (counter) ctx.drawImage(counter, x + 20, y + 22, 34, 23);
    const portrait = this.picture(`cast/${player.id}-face.png`);
    if (portrait) {
      const w = Math.min(20, Math.round(24 * portrait.width / portrait.height));
      ctx.drawImage(portrait, x + 12 - w / 2, y + 12, w, 24);
    }
    if (player.id === this.state.active) {
      const marker = this.picture('mpds/board-arrow-active.png');
      if (marker) ctx.drawImage(marker, x + 22, y + 53, 9, 8);
      else label(ctx, '>', x + 23, y + 51, {color: '#ffe195'});
    }
    const rankArt = rank > 0 && this.picture(`mpds/board-rank-${rank}.png`);
    if (rankArt) ctx.drawImage(rankArt, x + 26, y + 4, 21, 13);
    label(ctx, playerName(player.id), x + 26, y + 46, {align: 'center', size: 8});
    if (!counter) {
      label(ctx, '*', x + 23, y + 22);
      label(ctx, '$', x + 23, y + 34);
    }
    label(ctx, String(player.stars), x + 49, y + 22, {align: 'right'});
    label(ctx, String(player.coins), x + 49, y + 34, {align: 'right'});
  }
}
