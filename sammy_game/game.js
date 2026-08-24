// Sammy's Adventure — Mario-style platformer
const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');

const W = canvas.width;
const H = canvas.height;

const TILE = 32;
const GRAVITY = 0.55;
const JUMP_FORCE = -13;
const MOVE_SPEED = 4;

// ── Palette ──────────────────────────────────────────────────────────────────
const PAL = {
  sky:      '#5c94fc',
  ground:   '#c84b0a',
  groundTop:'#5ba93a',
  brick:    '#c84b0a',
  brickLine:'#a03000',
  coin:     '#f7c948',
  coinShine:'#fff8a0',
  mushroom: '#e8502a',
  mushroomDot:'#fff',
  goomba:   '#a05020',
  goombaDark:'#6a3010',
  sammy:    '#f4a832',
  sammyShoe:'#5b3310',
  sammyHat: '#e03030',
  sammyEye: '#fff',
  sammyPupil:'#222',
  pipe:     '#2e8b2e',
  pipeDark: '#1a5c1a',
  flag:     '#fff',
  pole:     '#888',
  star:     '#f7c948',
  bg1:      '#70a8ff',
  bg2:      '#4080ff',
  cloud:    '#fff',
};

// ── Input ─────────────────────────────────────────────────────────────────────
const keys = {};
window.addEventListener('keydown', e => { keys[e.key] = true; });
window.addEventListener('keyup',   e => { keys[e.key] = false; });

function isLeft()  { return keys['ArrowLeft']  || keys['a'] || keys['A']; }
function isRight() { return keys['ArrowRight'] || keys['d'] || keys['D']; }
function isJump()  { return keys['ArrowUp'] || keys['w'] || keys['W'] || keys[' ']; }

// ── Level map ─────────────────────────────────────────────────────────────────
// Each character: ' '=air, 'G'=ground, 'B'=brick, '?'=question, 'P'=pipe,
//                 'C'=coin, 'E'=goomba, 'F'=flagpole, 'M'=mushroom block
const LEVEL_ROWS = [
  '                                                                                                        ',
  '                                                                                                        ',
  '                                                                                                        ',
  '                                                                                                        ',
  '                                    B B?B                          B  B?B                              ',
  '                                                                                                        ',
  '              ?           B B B              ?         B  B  B          ?                    ?         ',
  '                                                                                                        ',
  '                    P P                 P P P                    P P             B B B B B             ',
  '  C C C    C C C    P P   C C C   C     P P P   C C C C         P P   C C C C                    F    ',
  'GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG',
  'GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG',
];

const MAP_ROWS = LEVEL_ROWS.length;
const MAP_COLS = LEVEL_ROWS[0].length;
const LEVEL_W  = MAP_COLS * TILE;
const LEVEL_H  = MAP_ROWS * TILE;

// ── Game state ────────────────────────────────────────────────────────────────
let score, lives, coinsCollected, level, gameState;
let sammy, camera;
let tiles, enemies, coins, particles, questionStates;
let jumpPressed = false;

function initGame() {
  score = 0;
  lives = 3;
  coinsCollected = 0;
  level = 1;
  gameState = 'playing'; // 'playing' | 'dead' | 'win' | 'gameover'
  loadLevel();
  updateHUD();
}

function loadLevel() {
  tiles = [];
  enemies = [];
  coins = [];
  particles = [];
  questionStates = {};

  for (let row = 0; row < MAP_ROWS; row++) {
    for (let col = 0; col < MAP_COLS; col++) {
      const ch = LEVEL_ROWS[row][col];
      const x = col * TILE;
      const y = row * TILE;
      if (ch === 'G') tiles.push({ x, y, type: 'ground' });
      else if (ch === 'B') tiles.push({ x, y, type: 'brick' });
      else if (ch === '?') {
        tiles.push({ x, y, type: 'question' });
        questionStates[`${col},${row}`] = 'active'; // active | used
      } else if (ch === 'P') tiles.push({ x, y, type: 'pipe' });
      else if (ch === 'M') tiles.push({ x, y, type: 'brick' });
      else if (ch === 'C') coins.push(new Coin(x + TILE/2, y + TILE/2));
      else if (ch === 'E') enemies.push(new Goomba(x, y));
      else if (ch === 'F') tiles.push({ x, y, type: 'flag' });
    }
  }

  sammy = new Sammy(TILE * 2, (MAP_ROWS - 3) * TILE);
  camera = { x: 0 };
}

function updateHUD() {
  document.getElementById('scoreVal').textContent  = score;
  document.getElementById('livesVal').textContent  = lives;
  document.getElementById('coinsVal').textContent  = coinsCollected;
  document.getElementById('levelVal').textContent  = level;
}

// ── Sammy (player) ────────────────────────────────────────────────────────────
class Sammy {
  constructor(x, y) {
    this.x = x; this.y = y;
    this.w = 28; this.h = 32;
    this.vx = 0; this.vy = 0;
    this.onGround = false;
    this.facing = 1; // 1=right, -1=left
    this.animFrame = 0;
    this.animTimer = 0;
    this.dead = false;
    this.invincible = 0; // frames of invincibility after being hit
  }

  update() {
    if (this.dead) {
      this.vy += GRAVITY;
      this.y += this.vy;
      return;
    }

    // Horizontal movement
    if (isLeft())  { this.vx = -MOVE_SPEED; this.facing = -1; }
    else if (isRight()) { this.vx = MOVE_SPEED; this.facing = 1; }
    else { this.vx *= 0.8; if (Math.abs(this.vx) < 0.2) this.vx = 0; }

    // Jump
    if (isJump() && !jumpPressed && this.onGround) {
      this.vy = JUMP_FORCE;
      this.onGround = false;
      jumpPressed = true;
      spawnParticles(this.x + this.w/2, this.y + this.h, '#fff', 4);
    }
    if (!isJump()) jumpPressed = false;

    // Gravity
    this.vy += GRAVITY;
    if (this.vy > 18) this.vy = 18;

    // Apply velocity
    this.x += this.vx;
    this.collideX();
    this.y += this.vy;
    this.onGround = false;
    this.collideY();

    // Clamp to level
    if (this.x < 0) this.x = 0;
    if (this.x + this.w > LEVEL_W) this.x = LEVEL_W - this.w;

    // Fall off screen → die
    if (this.y > LEVEL_H + 100) {
      this.die();
      return;
    }

    // Animation
    if (Math.abs(this.vx) > 0.5) {
      this.animTimer++;
      if (this.animTimer > 8) { this.animFrame = (this.animFrame + 1) % 4; this.animTimer = 0; }
    } else {
      this.animFrame = 0;
    }

    if (this.invincible > 0) this.invincible--;
  }

  collideX() {
    for (const t of tiles) {
      if (t.type === 'flag') continue;
      if (overlap(this, t)) {
        if (this.vx > 0) this.x = t.x - this.w;
        else if (this.vx < 0) this.x = t.x + TILE;
        this.vx = 0;
      }
    }
  }

  collideY() {
    for (const t of tiles) {
      if (t.type === 'flag') continue;
      if (overlap(this, t)) {
        if (this.vy > 0) {
          this.y = t.y - this.h;
          this.vy = 0;
          this.onGround = true;
        } else if (this.vy < 0) {
          this.y = t.y + TILE;
          this.vy = 0;
          // Hit question block from below
          const col = Math.floor(t.x / TILE);
          const row = Math.floor(t.y / TILE);
          const key = `${col},${row}`;
          if (t.type === 'question' && questionStates[key] === 'active') {
            questionStates[key] = 'used';
            spawnCoinBurst(t.x + TILE/2, t.y);
            score += 100;
            updateHUD();
          }
        }
      }
    }
  }

  hit() {
    if (this.invincible > 0 || this.dead) return;
    lives--;
    updateHUD();
    if (lives <= 0) {
      this.die();
      gameState = 'gameover';
    } else {
      this.invincible = 90;
      spawnParticles(this.x + this.w/2, this.y + this.h/2, '#e03030', 10);
    }
  }

  die() {
    this.dead = true;
    this.vy = -12;
    gameState = 'dead';
  }

  draw(cx) {
    const sx = this.x - cx;
    const sy = this.y;

    if (this.dead) {
      drawSammySprite(ctx, sx, sy, this.facing, this.animFrame, true);
      return;
    }
    // Blink when invincible
    if (this.invincible > 0 && Math.floor(this.invincible / 6) % 2 === 0) return;

    drawSammySprite(ctx, sx, sy, this.facing, this.animFrame, false);
  }
}

// ── Pixel-art Sammy sprite ────────────────────────────────────────────────────
function drawSammySprite(ctx, x, y, facing, frame, dead) {
  ctx.save();
  ctx.translate(x + 14, y + 16);
  if (facing === -1) ctx.scale(-1, 1);
  if (dead) ctx.rotate(Math.PI);

  // Legs (animated)
  const legOff = [0, 4, 0, -4][frame];
  ctx.fillStyle = PAL.sammyShoe;
  ctx.fillRect(-10, 14 + legOff,     9, 6);  // left leg
  ctx.fillRect(  1, 14 - legOff,     9, 6);  // right leg

  // Body
  ctx.fillStyle = PAL.sammy;
  ctx.fillRect(-12, 2, 24, 14);

  // Overalls stripe
  ctx.fillStyle = '#4444cc';
  ctx.fillRect(-7, 4, 14, 10);

  // Head
  ctx.fillStyle = PAL.sammy;
  ctx.fillRect(-10, -14, 20, 16);

  // Hat
  ctx.fillStyle = PAL.sammyHat;
  ctx.fillRect(-12, -18, 24, 6);
  ctx.fillRect(-8, -22, 20, 6);

  // Eyes
  ctx.fillStyle = PAL.sammyEye;
  ctx.fillRect(2, -12, 7, 5);
  ctx.fillStyle = PAL.sammyPupil;
  ctx.fillRect(5, -11, 3, 3);

  // Nose
  ctx.fillStyle = '#c8703a';
  ctx.fillRect(-1, -8, 4, 3);

  // Mustache
  ctx.fillStyle = '#5c2a00';
  ctx.fillRect(-8, -5, 18, 3);

  ctx.restore();
}

// ── Goomba enemy ─────────────────────────────────────────────────────────────
class Goomba {
  constructor(x, y) {
    this.x = x; this.y = y;
    this.w = TILE - 4; this.h = TILE - 4;
    this.vx = -1.5; this.vy = 0;
    this.alive = true;
    this.squished = false;
    this.squishTimer = 0;
    this.animFrame = 0;
    this.animTimer = 0;
  }

  update() {
    if (!this.alive) return;
    if (this.squished) {
      this.squishTimer++;
      if (this.squishTimer > 30) this.alive = false;
      return;
    }

    this.vy += GRAVITY;
    this.x += this.vx;
    this.y += this.vy;

    // Tile collisions
    for (const t of tiles) {
      if (t.type === 'flag') continue;
      if (overlapRect(this.x, this.y, this.w, this.h, t.x, t.y, TILE, TILE)) {
        // Check from above
        if (this.vy > 0 && this.y + this.h - this.vy <= t.y + 2) {
          this.y = t.y - this.h;
          this.vy = 0;
        } else if (this.vy < 0 && this.y - this.vy >= t.y + TILE - 2) {
          this.y = t.y + TILE;
          this.vy = 0;
        } else {
          this.vx *= -1;
          this.x += this.vx * 2;
        }
      }
    }

    // Reverse at edges
    if (this.x < 0 || this.x + this.w > LEVEL_W) this.vx *= -1;

    this.animTimer++;
    if (this.animTimer > 12) { this.animFrame ^= 1; this.animTimer = 0; }
  }

  squish() {
    this.squished = true;
    this.vy = 0;
    score += 200;
    updateHUD();
    spawnParticles(this.x + this.w/2, this.y, '#a05020', 6);
  }

  draw(cx) {
    if (!this.alive) return;
    const sx = this.x - cx;
    const sy = this.y;

    if (this.squished) {
      ctx.fillStyle = PAL.goomba;
      ctx.fillRect(sx, sy + this.h - 10, this.w, 10);
      return;
    }

    // Body
    ctx.fillStyle = PAL.goomba;
    ctx.fillRect(sx, sy + 8, this.w, this.h - 8);

    // Head
    ctx.fillStyle = PAL.goomba;
    ctx.fillRect(sx + 2, sy, this.w - 4, 16);

    // Brow
    ctx.fillStyle = PAL.goombaDark;
    ctx.fillRect(sx + 2, sy + 4, 10, 4);
    ctx.fillRect(sx + this.w - 12, sy + 4, 10, 4);

    // Eyes
    ctx.fillStyle = '#fff';
    ctx.fillRect(sx + 4,  sy + 6, 7, 5);
    ctx.fillRect(sx + this.w - 11, sy + 6, 7, 5);
    ctx.fillStyle = '#222';
    ctx.fillRect(sx + 7,  sy + 7, 3, 3);
    ctx.fillRect(sx + this.w - 8, sy + 7, 3, 3);

    // Feet
    ctx.fillStyle = PAL.goombaDark;
    const fOff = this.animFrame === 0 ? 0 : 3;
    ctx.fillRect(sx + 2,     sy + this.h - 8, 10, 8);
    ctx.fillRect(sx + this.w - 12, sy + this.h - 8, 10, 8);
  }
}

// ── Coin ──────────────────────────────────────────────────────────────────────
class Coin {
  constructor(x, y) {
    this.x = x; this.y = y;
    this.r = 8;
    this.collected = false;
    this.animTimer = Math.random() * Math.PI * 2;
  }

  update() { this.animTimer += 0.08; }

  draw(cx) {
    if (this.collected) return;
    const sx = this.x - cx;
    const scale = Math.abs(Math.cos(this.animTimer));
    ctx.save();
    ctx.translate(sx, this.y);
    ctx.scale(scale, 1);
    ctx.beginPath();
    ctx.arc(0, 0, this.r, 0, Math.PI * 2);
    ctx.fillStyle = PAL.coin;
    ctx.fill();
    ctx.beginPath();
    ctx.arc(-2, -2, 4, 0, Math.PI * 2);
    ctx.fillStyle = PAL.coinShine;
    ctx.fill();
    ctx.restore();
  }
}

// ── Particles ─────────────────────────────────────────────────────────────────
function spawnParticles(x, y, color, count) {
  for (let i = 0; i < count; i++) {
    const angle = (Math.PI * 2 * i) / count + Math.random() * 0.5;
    const speed = 2 + Math.random() * 3;
    particles.push({
      x, y,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed - 2,
      life: 30 + Math.random() * 20,
      maxLife: 50,
      color,
      r: 3 + Math.random() * 3,
    });
  }
}

function spawnCoinBurst(x, y) {
  for (let i = 0; i < 5; i++) {
    particles.push({
      x, y,
      vx: (Math.random() - 0.5) * 4,
      vy: -6 - Math.random() * 4,
      life: 40,
      maxLife: 40,
      color: PAL.coin,
      r: 6,
      coin: true,
    });
  }
  coinsCollected++;
  score += 50;
  updateHUD();
}

function updateParticles() {
  for (const p of particles) {
    p.x += p.vx;
    p.y += p.vy;
    p.vy += 0.3;
    p.life--;
  }
  for (let i = particles.length - 1; i >= 0; i--) {
    if (particles[i].life <= 0) particles.splice(i, 1);
  }
}

function drawParticles(cx) {
  for (const p of particles) {
    const alpha = p.life / p.maxLife;
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.fillStyle = p.color;
    if (p.coin) {
      ctx.beginPath();
      ctx.arc(p.x - cx, p.y, p.r, 0, Math.PI * 2);
      ctx.fill();
    } else {
      ctx.fillRect(p.x - cx - p.r/2, p.y - p.r/2, p.r, p.r);
    }
    ctx.restore();
  }
}

// ── Collision helpers ─────────────────────────────────────────────────────────
function overlap(a, b) {
  return overlapRect(a.x, a.y, a.w, a.h, b.x, b.y, TILE, TILE);
}

function overlapRect(ax, ay, aw, ah, bx, by, bw, bh) {
  return ax < bx + bw && ax + aw > bx && ay < by + bh && ay + ah > by;
}

// ── Drawing helpers ───────────────────────────────────────────────────────────
function drawTile(t, cx) {
  const x = t.x - cx;
  const y = t.y;
  switch (t.type) {
    case 'ground':
      ctx.fillStyle = PAL.groundTop;
      ctx.fillRect(x, y, TILE, TILE / 4);
      ctx.fillStyle = PAL.ground;
      ctx.fillRect(x, y + TILE/4, TILE, TILE * 3/4);
      // grid lines
      ctx.strokeStyle = PAL.brickLine;
      ctx.lineWidth = 1;
      ctx.strokeRect(x + 0.5, y + 0.5, TILE - 1, TILE - 1);
      break;

    case 'brick':
      ctx.fillStyle = PAL.brick;
      ctx.fillRect(x, y, TILE, TILE);
      ctx.strokeStyle = PAL.brickLine;
      ctx.lineWidth = 1;
      ctx.strokeRect(x + 0.5, y + 0.5, TILE - 1, TILE - 1);
      ctx.strokeRect(x + TILE/2 + 0.5, y + 2, 0, TILE/2 - 2);
      ctx.strokeRect(x + 0.5, y + TILE/2 + 0.5, TILE - 1, 0);
      ctx.strokeRect(x + 2, y + TILE/2 + 2, TILE/2 - 2, 0);
      break;

    case 'question': {
      const key = `${Math.floor(t.x/TILE)},${Math.floor(t.y/TILE)}`;
      const active = questionStates[key] === 'active';
      ctx.fillStyle = active ? '#f7c948' : '#888';
      ctx.fillRect(x, y, TILE, TILE);
      ctx.strokeStyle = active ? '#c8a020' : '#555';
      ctx.lineWidth = 2;
      ctx.strokeRect(x + 1, y + 1, TILE - 2, TILE - 2);
      ctx.fillStyle = active ? '#fff' : '#555';
      ctx.font = 'bold 20px monospace';
      ctx.textAlign = 'center';
      ctx.fillText(active ? '?' : '!', x + TILE/2, y + TILE - 8);
      break;
    }

    case 'pipe':
      ctx.fillStyle = PAL.pipe;
      ctx.fillRect(x + 2, y, TILE - 4, TILE);
      ctx.fillStyle = PAL.pipeDark;
      ctx.fillRect(x + 2, y, 6, TILE);
      // Check if this is the top of a pipe (no pipe above)
      {
        const colP = Math.floor(t.x / TILE);
        const rowP = Math.floor(t.y / TILE);
        const above = LEVEL_ROWS[rowP - 1] && LEVEL_ROWS[rowP - 1][colP];
        if (above !== 'P') {
          ctx.fillStyle = PAL.pipe;
          ctx.fillRect(x - 2, y, TILE + 4, TILE/2);
          ctx.fillStyle = PAL.pipeDark;
          ctx.fillRect(x - 2, y, 8, TILE/2);
          ctx.strokeStyle = PAL.pipeDark;
          ctx.lineWidth = 2;
          ctx.strokeRect(x - 1, y + 1, TILE + 2, TILE/2 - 2);
        }
      }
      break;

    case 'flag':
      // Pole
      ctx.fillStyle = PAL.pole;
      ctx.fillRect(x + TILE/2 - 2, y - TILE * 4, 4, TILE * 5);
      // Flag
      ctx.fillStyle = PAL.flag;
      ctx.beginPath();
      ctx.moveTo(x + TILE/2 + 2, y - TILE * 4);
      ctx.lineTo(x + TILE/2 + 20, y - TILE * 3);
      ctx.lineTo(x + TILE/2 + 2, y - TILE * 2);
      ctx.fill();
      // Base
      ctx.fillStyle = '#888';
      ctx.fillRect(x + TILE/2 - 8, y + TILE - 6, 16, 6);
      break;
  }
}

function drawBackground(cx) {
  // Sky gradient
  const grad = ctx.createLinearGradient(0, 0, 0, H);
  grad.addColorStop(0, PAL.bg2);
  grad.addColorStop(1, PAL.bg1);
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, W, H);

  // Clouds (parallax x0.3)
  const cloudPositions = [100, 280, 450, 620, 800, 1000, 1200, 1400, 1700, 2100, 2400, 2700];
  const cloudY = [60, 100, 50, 80, 120, 55, 90, 70, 100, 60, 85, 75];
  ctx.fillStyle = PAL.cloud;
  for (let i = 0; i < cloudPositions.length; i++) {
    const cx2 = cloudPositions[i] - cx * 0.3;
    const cy = cloudY[i];
    drawCloud(cx2, cy);
  }
}

function drawCloud(x, y) {
  ctx.beginPath();
  ctx.arc(x,      y,     20, 0, Math.PI * 2);
  ctx.arc(x + 22, y - 10, 26, 0, Math.PI * 2);
  ctx.arc(x + 50, y,     22, 0, Math.PI * 2);
  ctx.arc(x + 25, y + 10, 18, 0, Math.PI * 2);
  ctx.fill();
}

// ── Camera ────────────────────────────────────────────────────────────────────
function updateCamera() {
  const target = sammy.x - W / 3;
  camera.x += (target - camera.x) * 0.15;
  camera.x = Math.max(0, Math.min(LEVEL_W - W, camera.x));
}

// ── Collision: Sammy vs. enemies ──────────────────────────────────────────────
function checkSammyEnemyCollision() {
  if (sammy.dead || sammy.invincible > 0) return;
  for (const e of enemies) {
    if (!e.alive || e.squished) continue;
    if (overlapRect(sammy.x, sammy.y, sammy.w, sammy.h, e.x, e.y, e.w, e.h)) {
      // Stomp from above
      if (sammy.vy > 0 && sammy.y + sammy.h < e.y + e.h - 4) {
        e.squish();
        sammy.vy = JUMP_FORCE * 0.6;
      } else {
        sammy.hit();
      }
    }
  }
}

// ── Collision: Sammy vs. coins ─────────────────────────────────────────────────
function checkSammyCoinCollision() {
  for (const c of coins) {
    if (c.collected) continue;
    if (overlapRect(sammy.x, sammy.y, sammy.w, sammy.h, c.x - c.r, c.y - c.r, c.r*2, c.r*2)) {
      c.collected = true;
      coinsCollected++;
      score += 100;
      spawnParticles(c.x, c.y, PAL.coin, 5);
      updateHUD();
    }
  }
}

// ── Check win condition ───────────────────────────────────────────────────────
function checkWin() {
  for (const t of tiles) {
    if (t.type === 'flag') {
      if (overlapRect(sammy.x, sammy.y, sammy.w, sammy.h, t.x, t.y - TILE * 4, TILE + 20, TILE * 5)) {
        gameState = 'win';
        score += 1000;
        updateHUD();
      }
    }
  }
}

// ── Message overlay ───────────────────────────────────────────────────────────
let messageTimer = 0;

function drawMessage() {
  if (gameState === 'dead' || gameState === 'gameover' || gameState === 'win') {
    messageTimer++;
    if (messageTimer < 60) return; // short delay before showing

    ctx.fillStyle = 'rgba(0,0,0,0.5)';
    ctx.fillRect(W/2 - 200, H/2 - 60, 400, 140);
    ctx.strokeStyle = '#f7c948';
    ctx.lineWidth = 3;
    ctx.strokeRect(W/2 - 200, H/2 - 60, 400, 140);

    ctx.textAlign = 'center';
    ctx.font = 'bold 36px monospace';
    if (gameState === 'win') {
      ctx.fillStyle = '#f7c948';
      ctx.fillText('YOU WIN!', W/2, H/2 - 10);
      ctx.font = '20px monospace';
      ctx.fillStyle = '#fff';
      ctx.fillText(`SCORE: ${score}`, W/2, H/2 + 20);
    } else if (gameState === 'gameover') {
      ctx.fillStyle = '#e03030';
      ctx.fillText('GAME OVER', W/2, H/2 - 10);
    } else {
      ctx.fillStyle = '#fff';
      ctx.fillText('OH NO!', W/2, H/2 - 10);
      ctx.font = '20px monospace';
      ctx.fillStyle = '#aaa';
      ctx.fillText(`LIVES: ${lives}`, W/2, H/2 + 20);
    }

    ctx.font = '16px monospace';
    ctx.fillStyle = '#f7c948';
    ctx.fillText('Press R to restart', W/2, H/2 + 55);
  }
}

// ── Main loop ─────────────────────────────────────────────────────────────────
function gameLoop() {
  // Restart
  if (keys['r'] || keys['R']) {
    initGame();
    messageTimer = 0;
  }

  // Update
  if (gameState === 'playing') {
    sammy.update();
    for (const e of enemies) e.update();
    for (const c of coins) c.update();
    updateParticles();
    updateCamera();
    checkSammyEnemyCollision();
    checkSammyCoinCollision();
    checkWin();
  } else if (gameState === 'dead') {
    sammy.update(); // let Sammy fall off screen
    updateParticles();
    if (sammy.y > LEVEL_H + 200) {
      // After falling, reset position and switch to just showing message
      sammy.y = -9999;
    }
  } else {
    updateParticles();
  }

  // Draw
  ctx.clearRect(0, 0, W, H);
  drawBackground(camera.x);

  // Tiles (back)
  for (const t of tiles) {
    if (t.x - camera.x > -TILE && t.x - camera.x < W + TILE) {
      drawTile(t, camera.x);
    }
  }

  // Coins
  for (const c of coins) {
    if (c.x - camera.x > -32 && c.x - camera.x < W + 32) {
      c.draw(camera.x);
    }
  }

  // Enemies
  for (const e of enemies) {
    if (e.x - camera.x > -TILE && e.x - camera.x < W + TILE) {
      e.draw(camera.x);
    }
  }

  // Particles
  drawParticles(camera.x);

  // Sammy
  sammy.draw(camera.x);

  // UI overlay
  drawMessage();

  requestAnimationFrame(gameLoop);
}

initGame();
gameLoop();
