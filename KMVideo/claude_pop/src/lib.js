// lib.js：本片通用工具——时间表取值、水彩底板、字幕胶囊、拟声大字、无状态粒子、几何。
// 所有函数都是 t 的纯函数：帧会并行乱序渲染，不许在帧之间保存状态。
const EV = CUE.ev;
const INK = PAL.ink, CREAM = PAL.cream;
const HARD = '#F2C53D';          // 安全帽黄
const STEEL = '#8C9AB4', STEEL_DK = '#56607E', STEEL_LT = '#C9D3E4';
const RUST = '#B4592F', RUST_DK = '#7E3620';
const CAP_Y = 1470;              // 字幕胶囊中心（抖音底部 UI 之上）

// 被 t0 时刻的一次“咯噔”踢起来：先猛地上跳，再阻尼回弹。返回向上为负的位移（像素）。
function kick(t, t0, amp) {
  const a = t - t0; if (a < 0 || a > .9) return 0;
  if (a < .07) return -amp * Math.sin(a / .07 * Math.PI / 2);
  return -amp * Math.exp(-(a - .07) * 9) * Math.cos((a - .07) * 24);
}
const kicks = (t, ts, amp) => ts.reduce((s, t0) => s + kick(t, t0, amp), 0);
// 0→1 弹出、t1 后 0.2s 收回
function popK(t, t0, t1 = 1e9, d = .3) {
  if (t < t0) return 0;
  const a = backOut(seg(t, t0, t0 + d)), b = t > t1 ? 1 - easeIn(seg(t, t1, t1 + .2)) : 1;
  return a * b;
}

// ---------- 几何 ----------
function circPts(cx, cy, r, n = 40, rf = null, rot = 0) {
  const p = []; for (let i = 0; i < n; i++) { const a = rot + i / n * TAU, rr = rf ? rf(a - rot, i) : r; p.push([cx + Math.cos(a) * rr, cy + Math.sin(a) * rr]); } return p;
}
function arcPts(cx, cy, r, a0, a1, n = 24) { const p = []; for (let i = 0; i <= n; i++) { const a = lerp(a0, a1, i / n); p.push([cx + Math.cos(a) * r, cy + Math.sin(a) * r]); } return p; }
// 齿轮外轮廓：R = 齿根半径，th = 齿高，rot = 转角，skip(i) = 该齿是否缺失，grow(i) = 该齿长出的比例 0..1
function gearPts(cx, cy, R, teeth, th, rot, grow = null) {
  const p = [], step = TAU / teeth;
  for (let i = 0; i < teeth; i++) {
    const g = grow ? grow(i) : 1, a = rot + i * step, h = R + th * g;
    p.push([cx + Math.cos(a) * R, cy + Math.sin(a) * R]);
    p.push([cx + Math.cos(a + step * .18) * h, cy + Math.sin(a + step * .18) * h]);
    p.push([cx + Math.cos(a + step * .5) * h, cy + Math.sin(a + step * .5) * h]);
    p.push([cx + Math.cos(a + step * .68) * R, cy + Math.sin(a + step * .68) * R]);
  }
  return p;
}
const rotP = (p, a, cx = 0, cy = 0) => { const c = Math.cos(a), s = Math.sin(a), x = p[0] - cx, y = p[1] - cy; return [cx + x * c - y * s, cy + x * s + y * c]; };

// ---------- 水彩底板（预渲染的大面积水彩天空；无 GPU 时实时画太慢） ----------
// 每块底板是一个 LOOP（plate_<名>），用真正的 p5.brush 水彩填充画一次，存成 assets/plates/<名>.jpg。
const PLATE = {}, PLATE_DEF = {};
function defPlate(name, base, fn) {
  PLATE_DEF[name] = { base, fn };
  const L = LOOPS['plate_' + name] = t => { FAST_FILL = false; boilSeed('plate ' + name); fn(); FAST_FILL = !!PROJECT.fastFill; };
  L.len = 1;
}
window.prepare = async () => {
  for (const name of Object.keys(PLATE_DEF)) {
    try { PLATE[name] = await loadImage(`assets/plates/${name}.jpg`); } catch (e) { PLATE[name] = null; }
  }
};
// 屏幕空间画一块底板：a = 不透明度，s = 放大（留视差余量），dx/dy = 视差位移
function plate(name, a = 1, dx = 0, dy = 0, s = 1.12) {
  if (a <= .01) return;
  const img = PLATE[name];
  if (!img) { paint(rectPts(-60, -60, W + 120, H + 120), { wash: PLATE_DEF[name].base, washOp: 255 * a, ink: null }); return; }
  flushBrush();
  push(); if (a < 1) tint(255, 255 * a);
  image(img, W / 2 - W * s / 2 + dx, H / 2 - H * s / 2 + dy, W * s, H * s);
  noTint(); pop();
}

// ---------- 字幕胶囊（仿原片底部字幕）：逐字弹入、{关键词} 高亮黄、随拍轻跳，下面一行英文 ----------
function parseHL(s) { const out = []; let hl = false; for (const ch of s) { if (ch === '{') { hl = true; continue; } if (ch === '}') { hl = false; continue; } out.push({ ch, hl }); } return out; }
function captions(t) {
  for (const C of CUE.captions) if (t > C.t0 - .02 && t < C.t1 + .25) drawCaption(t, C);
}
function drawCaption(t, C) {
  const k = backOut(seg(t, C.t0, C.t0 + .26)) * (1 - easeIn(seg(t, C.t1, C.t1 + .2)));
  if (k <= .01) return;
  const age = t - C.t0, p = pulse(t, 8), chars = parseHL(C.zh);
  letterFn(c => {
    const zf = '58px "ZCOOL KuaiLe"', ef = '600 31px "Fredoka"';
    c.font = zf; const ws = chars.map(o => c.measureText(o.ch).width), zw = ws.reduce((a, b) => a + b, 0);
    c.font = ef; const ew = c.measureText(C.en).width;
    const pw = Math.min(W - 40, Math.max(zw, ew) + 96), ph = 150;
    c.translate(W / 2, CAP_Y); c.rotate(Math.sin(t * 1.3 + C.t0) * .012); const s = k * (1 + .015 * p); c.scale(s, s);
    // 胶囊：墨色，右下一层暖色“错版”阴影
    c.fillStyle = 'rgba(217,119,87,.9)'; c.beginPath(); c.roundRect(-pw / 2 + 8, -ph / 2 + 9, pw, ph, 44); c.fill();
    c.fillStyle = 'rgba(43,34,51,.94)'; c.beginPath(); c.roundRect(-pw / 2, -ph / 2, pw, ph, 44); c.fill();
    c.textAlign = 'center'; c.textBaseline = 'middle'; c.font = zf;
    let x = -zw / 2;
    chars.forEach((o, i) => {
      const t0 = .04 + i * .032, ck = backOut(seg(age, t0, t0 + .2));
      if (ck > .01) {
        c.save(); c.translate(x + ws[i] / 2, -24 - (1 - ck) * 26 - (o.hl ? 7 * p : 0)); c.scale(ck, ck);
        if (o.hl) c.rotate(Math.sin(t * 9 + i) * .06);
        c.fillStyle = o.hl ? HARD : '#FFF3DE'; c.fillText(o.ch, 0, 0); c.restore();
      }
      x += ws[i];
    });
    c.globalAlpha = seg(age, .3, .55); c.font = ef; c.fillStyle = '#F2A283'; c.fillText(C.en, 0, 40);
  });
}

// ---------- 拟声大字（屏幕坐标；世界坐标先 toScreen）----------
function boom(txt, x, y, size, col, t, t0, o = {}) {
  const age = t - t0, life = o.life ?? .9; if (age < 0 || age > life) return;
  letterFn(c => {
    const k = backOut(clamp(age * 6.5)), fade = 1 - seg(age, life - .18, life);
    c.globalAlpha = fade; c.translate(x, y); c.rotate((o.rot ?? -.1) + Math.sin(age * 26) * .05 * (1 - age / life));
    const s = k * (o.grow ? 1 + age * o.grow : 1); c.scale(s, s);
    c.font = `${size}px "${o.font || 'Smiley Sans'}"`; c.textAlign = 'center'; c.textBaseline = 'middle'; c.lineJoin = 'round';
    c.fillStyle = INK; c.fillText(txt, size * .05, size * .08);
    c.lineWidth = size * .14; c.strokeStyle = INK; c.strokeText(txt, 0, 0);
    c.fillStyle = col; c.fillText(txt, 0, 0);
  });
}

// ---------- 无状态粒子：第 i 颗在 t0 + i/rate 出生，任意帧都能独立算出 ----------
function sparks(x, y, t, t0, t1, o = {}) {
  const rate = o.rate || 40, life = o.life || .45, g = o.g ?? 1500, sp = o.speed || 700, dir = o.dir ?? -Math.PI / 2, spread = o.spread ?? 1.2;
  const i0 = Math.max(0, Math.floor((t - life - t0) * rate)), i1 = Math.floor((Math.min(t, t1) - t0) * rate);
  if (i1 < 0) return;
  boilSeed('sparks' + (o.key || '') + x);
  for (let i = i0; i <= i1; i++) {
    const age = t - (t0 + i / rate); if (age < 0 || age > life) continue;
    const a = dir + (hash(i * 3.1 + (o.seed || 0)) - .5) * spread, v = sp * (.5 + hash(i * 7.7 + 1) * .8);
    const px = x + Math.cos(a) * v * age, py = y + Math.sin(a) * v * age + g * age * age / 2;
    const vx = Math.cos(a) * v, vy = Math.sin(a) * v + g * age, L = .028 * (1 - age / life);
    inkLine([[px, py], [px - vx * L, py - vy * L]], o.sw || 1.1, age < life * .4 ? '#FFF1B8' : (o.col || '#FF9A3D'), 'inkfine', 0);
  }
}
// 彩纸：小色块沿抛物线飞散翻转
function confetti(x, y, t, t0, n = 26, o = {}) {
  const age = t - t0; if (age < 0 || age > (o.life || 1.6)) return;
  const cols = [HARD, PAL.rose, PAL.teal, PAL.sky, PAL.clayLt, PAL.cream];
  for (let i = 0; i < n; i++) {
    boilSeed('conf' + i + x);
    const a = -Math.PI / 2 + (hash(i * 5.3) - .5) * 2.6, v = (o.speed || 900) * (.4 + hash(i * 2.9) * .8);
    const px = x + Math.cos(a) * v * age * Math.exp(-age * .8), py = y + Math.sin(a) * v * age * Math.exp(-age * .8) + 520 * age * age;
    const s = (o.size || 13) * (1 - seg(age, (o.life || 1.6) - .4, o.life || 1.6)), r = age * (6 + hash(i) * 8) + i;
    if (s < 1) continue;
    const P = [[-s, -s * .55], [s, -s * .55], [s, s * .55], [-s, s * .55]].map(q => rotP(q, r)).map(q => [q[0] * (1 + .6 * Math.sin(age * 12 + i)) + px, q[1] + py]);
    paint(P, { wash: cols[i % cols.length], ink: null });
  }
}
