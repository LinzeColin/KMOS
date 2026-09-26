// cast.js：演员与道具。都在世界坐标里画（窑宝中心 KILN），只有百分表是屏幕坐标的“仪表”。
// 世界布局（1080×1920 竖屏，镜头默认对准 (0, 960)，缩放 1）：窑宝在左中，厂长在右前，木箱落在两人之间，
// 大齿圈工位在右边 x≈1600，云上行业岛在上方 y≈-2600。

const KILN = { x: -150, y: 720, R: 300, Ri: 236, rs: 222, rr: 88 };
const ROLL = [[-150 - 211, 1045], [-150 + 211, 1045]];   // 两只托轮圆心（与轮带相切，33°）
const GROUND = 1250;
const MGR = { x: 250, y: 1335 };                          // 厂长脚底
const CRATE = { x: 10, y: 1410 };                         // 木箱落地点（底边中点）
const GEAR = { x: 1620, y: 760, R: 330, n: 30, th: 34 };

// ---------- 背景：水泥厂（视差层） ----------
function plant(t, smoke) {
  boilSeed('hills');
  paint([[-1400, 1180], [-900, 1080], [-500, 1140], [-100, 1060], [400, 1130], [900, 1050], [1400, 1120], [1400, 1300], [-1400, 1300]], { wash: '#A9B7C9', washOp: 200, ink: null, curv: .6 });
  // 预热器塔（左）
  boilSeed('tower');
  paint(rectPts(-640, 170, 250, 1100, 3), { wash: '#C9B79E', ink: INK, sw: .8 });
  for (let k = 0; k < 4; k++) {
    const y = 250 + k * 240;
    paint([[-620, y], [-420, y], [-440, y + 120], [-520, y + 190], [-600, y + 120]], { wash: STEEL_LT, ink: INK, sw: .7 });
    inkLine([[-650, y + 200], [-380, y + 200]], .7, INK, 'inkfine', 0);
  }
  inkLine([[-515, 170], [-515, 90]], 1.4, INK, 'ink', 0);
  // 筒仓（右）
  boilSeed('silos');
  for (const [x0, w, top] of [[170, 150, 520], [330, 140, 600]]) {
    paint([[x0, top], [x0 + w / 2, top - 55], [x0 + w, top], [x0 + w, 1260], [x0, 1260]], { wash: '#DCCDB5', ink: INK, sw: .8, curv: .15 });
    inkLine([[x0 + w * .25, top + 20], [x0 + w * .25, 1240]], .5, '#A89678', 'inkfine', 0);
  }
  // 烟囱 + 烟
  boilSeed('chimney');
  paint(rectPts(505, 40, 70, 1220, 2), { wash: '#E7DCC8', ink: INK, sw: .8 });
  for (const y of [60, 150]) paint(rectPts(505, y, 70, 45, 1), { wash: '#D96B55', ink: null });
  for (let i = 0; i < 9; i++) {
    const age = frac(t * .22 + i / 9), r = 30 + age * 110;
    boilSeed('smoke' + i);
    paint(ellPts(540 + age * 260 + Math.sin(i * 3 + t) * 20, 30 - age * 520, r, r * .8, 14, 4), { wash: mixCol('#9C98A8', '#FFF8EE', smoke), washOp: 200 * (1 - age), ink: null });
  }
}
function floorLayer() {
  boilSeed('floor');
  paint(rectPts(-2400, GROUND - 10, 6200, 1400, 4), { wash: '#CDB595', ink: null });
  inkLine([[-2400, GROUND - 8], [3800, GROUND - 8]], 1.1, INK, 'ink', 0);
  for (let i = 0; i < 26; i++) { const x = -2200 + hash(i) * 5800, y = GROUND + 60 + hash(i + 50) * 500; inkLine([[x, y], [x + 60 + hash(i + 9) * 90, y + 4]], .5, '#9C8466', 'inkfine', .3); }
}

// ---------- 窑宝：端面朝镜头的回转窑 ----------
// st: dy（颠起）, rot（轮带转角）, rep(φ)（该材料角已车好 0..1）, rust（托轮锈 0..1）, face: {eyes, mouth, blush, gloom, sweat, look, tint, burp}
const TYRE_PITS = [[.3, 1], [1.9, .7], [3.3, 1.2], [4.6, .8], [5.6, .9]];   // 材料角 + 深度
function pitAt(phi) { let d = 0; for (const [a, k] of TYRE_PITS) { const x = Math.atan2(Math.sin(phi - a), Math.cos(phi - a)); d += k * Math.exp(-x * x * 40); } return d; }
function kiln(t, st) {
  const { x, y, R, Ri, rs, rr } = KILN, cy = y + (st.dy || 0), rot = st.rot, rep = st.rep || (() => 0);
  // 托轮（反向转）
  ROLL.forEach(([rx, ry], i) => {
    boilSeed('roller' + i);
    const ra = -rot * R / rr + i;
    paint(circPts(rx, ry, rr, 30), { wash: mixCol(STEEL_DK, RUST, (st.rust ?? 1) * .7), ink: INK, sw: .9 });
    paint(circPts(rx, ry, rr * .78, 24), { wash: mixCol(STEEL, '#C07A4E', (st.rust ?? 1) * .6), ink: null });
    if (st.rollShine && st.rollShine[i] > 0) inkLine(arcPts(rx, ry, rr * .88, -2.6, -2.6 + 2.4 * st.rollShine[i], 12), 2.2, CREAM, 'inkfine', .5);
    for (let k = 0; k < 3; k++) { const a = ra + k * TAU / 3; inkLine([[rx, ry], [rx + Math.cos(a) * rr * .7, ry + Math.sin(a) * rr * .7]], .8, INK, 'inkfine', 0); }
    paint(circPts(rx, ry, 16, 10), { wash: INK, ink: null });
  });
  // 墩座 + 轴承座
  boilSeed('pier');
  paint([[ROLL[0][0] - 190, 1112], [ROLL[1][0] + 170, 1112], [ROLL[1][0] + 200, GROUND + 6], [ROLL[0][0] - 220, GROUND + 6]], { wash: '#B8AD9F', ink: INK, sw: .9 });
  ROLL.forEach(([rx, ry], i) => { boilSeed('house' + i); paint(rectPts(rx - 100, ry + 14, 200, 70, 2), { wash: '#6E7C9C', ink: INK, sw: .8 }); });
  // 筒身：斜伸向后面的预热器塔（平面示意，让人一眼看出这是一根长长的回转窑）
  kilnBody(t, x, cy, R, st);
  // 轮带（外圈）：磨损处凹凸不平，车过的地方变圆
  boilSeed('tyre');
  const outer = circPts(x, cy, R, 72, a => R - 16 * pitAt(a - rot) * (1 - rep(a - rot)) + (1 - rep(a - rot)) * 3 * Math.sin((a - rot) * 23));
  paint(outer, { wash: mixCol(STEEL, '#9A8C86', st.sick ?? 0), ink: INK, sw: 1.2 });
  // 锈斑与磨损红光（随轮带转）
  for (let k = 0; k < TYRE_PITS.length; k++) {
    const [a0, dk] = TYRE_PITS[k], w = 1 - rep(a0), a = a0 + rot;
    if (w < .05) continue;
    const px = x + Math.cos(a) * (R - 36), py = cy + Math.sin(a) * (R - 36);
    boilSeed('pit' + k);
    paint(ellPts(px, py, 30 * dk, 17 * dk, 12, 2, a + Math.PI / 2), { wash: RUST, washOp: 230 * w, ink: null });
    if (st.glowPits) glow(px, py, 60 * dk, '#FF6A3D', .55 * w * st.glowPits);
  }
  // 镜面高光：车好的弧段
  boilSeed('shine');
  const sh = st.shine || 0;
  if (sh > 0) {
    inkLine(arcPts(x, cy, R - 14, -2.3, -2.3 + 1.5 * sh, 18), 3, '#FFFFFF', 'inkfine', .5);
    inkLine(arcPts(x, cy, R - 30, .4, .4 + .9 * sh, 12), 1.8, CREAM, 'inkfine', .5);
  }
  // 轮带与筒体之间的缝 + 筒体端面（窑宝的脸盘）
  boilSeed('gap');
  paint(circPts(x, cy, Ri, 48), { wash: '#3B3450', ink: INK, sw: .8 });
  boilSeed('face disc');
  const f = st.face || {};
  paint(circPts(x, cy, rs, 48), { wash: mixCol('#BCC9DD', '#A9B4A4', f.tint ?? 0), ink: INK, sw: 1 });
  paint(circPts(x - 40, cy - 60, rs * .62, 30), { wash: '#D3DDEB', washOp: 150, ink: null });
  for (let k = 0; k < 16; k++) { const a = rot + k * TAU / 16; paint(ellPts(x + Math.cos(a) * (rs - 20), cy + Math.sin(a) * (rs - 20), 6, 6, 8), { wash: STEEL_DK, ink: null }); }
  kilnFace(t, x, cy, f);
  // 屏幕空间反射（照镜子）：厂长的小倒影
  if (st.reflect > 0) {
    boilSeed('reflect');
    const a = .55, px = x + Math.cos(a) * (R - 44), py = cy + Math.sin(a) * (R - 44), k = st.reflect;
    paint(ellPts(px, py + 12, 34 * k, 36 * k, 14), { wash: '#F2CFAE', washOp: 230, ink: INK, sw: .5 });
    paint(ellPts(px, py - 14, 38 * k, 18 * k, 12), { wash: HARD, washOp: 235, ink: INK, sw: .5 });
    for (const s2 of [-1, 1]) paint(heartPts(px + s2 * 12 * k, py + 10, 7 * k), { wash: '#E2476E', ink: null });
    inkLine(through([[px, py - 30], [px + 12, py - 52], [px - 8, py - 62], [px + 6, py - 80]]), 1.2, '#FFFFFF', 'inkfine', .5);
    glow(px - 20, py - 20, 50, '#FFFFFF', .6);
  }
}
function kilnBody(t, x, y, R, st) {
  const d = [-340, -265], L = Math.hypot(d[0], d[1]), n = [d[1] / L, -d[0] / L];
  const segp = (k0, k1, r0, r1, key, col) => {
    const a = [x + d[0] * k0, y + d[1] * k0], b = [x + d[0] * k1, y + d[1] * k1];
    boilSeed('body' + key);
    paint([[a[0] + n[0] * r0, a[1] + n[1] * r0], [b[0] + n[0] * r1, b[1] + n[1] * r1], [b[0] - n[0] * r1, b[1] - n[1] * r1], [a[0] - n[0] * r0, a[1] - n[1] * r0]], { wash: col, ink: INK, sw: .9 });
    // 转动的焊缝
    for (let i = 0; i < 3; i++) { const u = frac(i / 3 + t * .5), q = [lerp(a[0], b[0], .5), lerp(a[1], b[1], .5)], rr = lerp(r0, r1, .5); inkLine([[q[0] + n[0] * rr * (u * 2 - 1) - d[0] * .02, q[1] + n[1] * rr * (u * 2 - 1) - d[1] * .02], [q[0] + n[0] * rr * (u * 2 - 1) + d[0] * .02, q[1] + n[1] * rr * (u * 2 - 1) + d[1] * .02]], .5, '#4B5470', 'inkfine', 0); }
  };
  const rf = k => R * lerp(.8, .5, k);
  boilSeed('body far'); paint(circPts(x + d[0], y + d[1], rf(1), 30), { wash: '#5A6480', ink: INK, sw: .8 });
  segp(.55, 1, rf(.55), rf(1), 'far', mixCol('#7C88A6', '#8E8680', st.sick ?? 0));
  boilSeed('body ring'); paint(circPts(x + d[0] * .55, y + d[1] * .55, rf(.55) * 1.14, 30), { wash: STEEL, ink: INK, sw: .9 });
  segp(0, .55, rf(0), rf(.55), 'near', mixCol('#7C88A6', '#8E8680', st.sick ?? 0));
}
function kilnFace(t, x, y, f) {
  const lx = (f.look || 0) * 16, ly = (f.lookY || 0) * 12;
  boilSeed('kface');
  if (f.gloom > 0) for (let k = 0; k < 4; k++) inkLine([[x - 80 + k * 50, y - 190], [x - 80 + k * 50, y - 150 + 12 * Math.sin(k)]], 1, mixCol(INK, '#6D86BE', .4), 'inkfine', 0);
  for (const s of [-1, 1]) {
    const ex = x + s * 72 + lx, ey = y - 25 + ly, e = f.eyes || 'normal';
    if (e === 'normal' || e === 'wide') {
      const h = e === 'wide' ? 96 : 80, w = e === 'wide' ? 44 : 36;
      paint(rrPts(ex - w / 2, ey - h / 2, w, h, w / 2), { wash: INK, ink: null });
      paint(ellPts(ex - w * .15, ey - h * .22, w * .18, h * .1, 8), { wash: CREAM, ink: null });
      if (f.lid > 0) paint(rectPts(ex - w / 2 - 6, ey - h / 2 - 8, w + 12, (h + 8) * f.lid, 0), { wash: mixCol('#BCC9DD', '#A9B4A4', f.tint ?? 0), ink: null });
      if (f.lid > 0) inkLine([[ex - w / 2 - 4, ey - h / 2 + (h + 8) * f.lid - 8], [ex + w / 2 + 4, ey - h / 2 + (h + 8) * f.lid - 8 - s * 6]], 1.2, INK, 'ink', 0);
      if (f.bags) inkLine(arcPts(ex, ey + h * .45, w * .7, .5, 2.6, 8), .8, '#6E6A86', 'inkfine', .5);
    } else if (e === 'squeeze') {
      inkLine([[ex - 26 * s, ey - 26], [ex + 18 * s, ey], [ex - 26 * s, ey + 26]], 2.2, INK, 'ink', .1);
    } else if (e === 'happy') {
      inkLine(arcPts(ex, ey + 16, 30, Math.PI * 1.1, Math.PI * 1.9, 10), 2.4, INK, 'ink', .5);
    } else if (e === 'closed') {
      inkLine([[ex - 28, ey + 6], [ex + 28, ey + 6]], 2.2, INK, 'ink', 0);
    } else if (e === 'swirl') {
      const P = []; for (let k = 0; k < 18; k++) { const a = k * .7 + t * 8 * s, r = 4 + k * 1.6; P.push([ex + Math.cos(a) * r, ey + Math.sin(a) * r]); } inkLine(P, 1.4, INK, 'inkfine', .5);
    }
  }
  if (f.blush > 0) for (const s of [-1, 1]) paint(ellPts(x + s * 128, y + 48, 30, 17, 12), { wash: PAL.rose, washOp: 200 * f.blush, ink: null });
  const m = f.mouth, my = y + 82;
  if (m === 'wobble') inkLine([[x - 46, my + 6], [x - 23, my - 5], [x, my + 6], [x + 23, my - 5], [x + 46, my + 6]], 1.6, INK, 'ink', .6);
  else if (m === 'smile') inkLine(arcPts(x, my - 30, 48, .5, Math.PI - .5, 12), 2, INK, 'ink', .5);
  else if (m === 'grin') paint([...arcPts(x, my - 22, 56, .25, Math.PI - .25, 14)], { wash: '#7A2E3B', ink: INK, sw: 1.1 });
  else if (m === 'O') paint(ellPts(x, my + 4, 20 + 14 * (f.burp || 0), 24 + 16 * (f.burp || 0), 16), { wash: '#6A2D3A', ink: INK, sw: 1 });
  else if (m === 'frown') inkLine(arcPts(x, my + 40, 42, -Math.PI + .6, -.6, 12), 1.8, INK, 'ink', .5);
  if (f.sweat > 0) { const k = f.sweat; boilSeed('ksweat'); paint([[x + 190, y - 150 + 30 * (1 - k)], [x + 210, y - 110 + 30 * (1 - k)], [x + 190, y - 96 + 30 * (1 - k)], [x + 172, y - 110 + 30 * (1 - k)]], { wash: PAL.sky, washOp: 255 * k, ink: INK, sw: .6, curv: .6 }); }
}

// ---------- 厂长 ----------
// st: face {eyes, mouth, tears, blush, sweat, look}, lean, dy, sq, aL/aR（手的位置，相对身体）, bowl, noodleHat 0..1, curl（呆毛 0..1 + wob）, puff
function manager(t, x, y, st) {
  const s = st.s || 1, sq = st.sq || 0, dy = st.dy || 0;
  push(); translate(x, y + dy); rotate(st.lean || 0); scale(s * (1 + sq * .5), s * (1 - sq));
  // 腿
  boilSeed('mgr legs');
  for (const k of [-1, 1]) {
    paint(ribbon([[k * 26, -100], [k * 28, -50], [k * 30, -8]], 30, 26), { wash: '#3E4A6B', ink: INK, sw: .8 });
    paint(ellPts(k * 36, -4, 30, 14, 12), { wash: INK, ink: null });
  }
  // 身体：蓝色工装 + 反光条
  boilSeed('mgr body');
  const body = ellPts(0, -185, 100, 108, 28, 2);
  paint(body, { wash: '#3F6FA8', ink: INK, sw: 1 });
  paint(rectPts(-96, -175, 192, 22, 1), { wash: HARD, washOp: 235, ink: null });
  paint(rectPts(-60, -290, 26, 110, 1), { wash: HARD, washOp: 235, ink: null });
  paint(rectPts(34, -290, 26, 110, 1), { wash: HARD, washOp: 235, ink: null });
  // 手臂（ribbon）+ 手
  const sh = { L: [-78, -240], R: [78, -240] };
  const hand = { L: st.hL || [-150, -170], R: st.hR || [140, -175] };
  boilSeed('mgr arms');
  for (const k of ['L', 'R']) {
    const a = sh[k], b = hand[k], m = [(a[0] + b[0]) / 2 + (k === 'L' ? -20 : 20), (a[1] + b[1]) / 2 + 18];
    paint(ribbon([a, m, b], 34, 26), { wash: '#3F6FA8', ink: INK, sw: .9 });
    paint(ellPts(b[0], b[1], 20, 18, 12), { wash: '#F2CFAE', ink: INK, sw: .7 });
  }
  // 碗（左手）+ 筷子（右手）
  if (st.bowl) {
    boilSeed('bowl');
    const [bx, by] = hand.L;
    paint([[bx - 70, by - 20], [bx + 70, by - 20], [bx + 50, by + 34], [bx - 50, by + 34]], { wash: '#F4EFE6', ink: INK, sw: .9, curv: .4 });
    inkLine([[bx - 64, by - 6], [bx + 64, by - 6]], 1.2, '#4A74B8', 'inkfine', 0);
    if (st.bowlNoodles !== false) paint(ellPts(bx, by - 24, 62, 22, 16, 2), { wash: '#E8C35A', ink: INK, sw: .6 });
    if (st.bowlNoodles !== false) paint(ellPts(bx - 8, by - 34, 26, 10, 10, 2), { wash: '#9B6A3A', ink: null });
    const [cx, cy] = hand.R, ca = st.chop ?? -.6;
    inkLine([[cx, cy], [cx + Math.cos(ca) * -120, cy + Math.sin(ca) * -120]], 1.2, '#8A5A34', 'ink', 0);
    inkLine([[cx + 10, cy + 6], [cx + 10 + Math.cos(ca + .08) * -120, cy + 6 + Math.sin(ca + .08) * -120]], 1.2, '#8A5A34', 'ink', 0);
  }
  // 头
  boilSeed('mgr head');
  const hx = 0, hy = -330, f = st.face || {};
  paint(ellPts(hx - 74, hy + 4, 14, 20, 10), { wash: '#F2CFAE', ink: INK, sw: .7 });
  paint(ellPts(hx, hy, 74, 70, 26, 1.5), { wash: '#F5D3B0', ink: INK, sw: 1 });
  managerFace(t, hx, hy, f);
  // 安全帽
  boilSeed('mgr hat');
  const hatUp = st.hatUp || 0;
  push(); translate(hx, hy - 38 - hatUp); rotate(st.hatRot || 0);
  paint(arcPts(0, 0, 82, Math.PI, TAU, 16).concat([[82, 0]]), { wash: HARD, ink: INK, sw: 1 });
  paint(rectPts(-100, -4, 200, 20, 1), { wash: HARD, ink: INK, sw: .9 });
  inkLine([[0, -80], [0, -2]], .7, '#C49A22', 'inkfine', 0);
  // 头上的热干面
  if (st.noodleHat > 0) {
    const k = st.noodleHat; boilSeed('hat noodles');
    for (let i = 0; i < 7; i++) {
      const x0 = -70 + i * 23, P = [[x0, -60 + Math.abs(x0) * .3]];
      for (let j = 1; j < 5; j++) P.push([x0 + Math.sin(i + j * 1.7) * 14, -60 + Math.abs(x0) * .3 + j * 26 * k + Math.sin(t * 6 + i) * 2]);
      inkLine(P, 2.6, '#E8C35A', 'ink', .6);
    }
    paint(ellPts(0, -66, 34, 14, 10), { wash: '#9B6A3A', washOp: 220, ink: null });
    paint(ellPts(18, -74, 10, 5, 6), { wash: PAL.sap, ink: null });
  }
  // 车屑呆毛（弹簧）
  if (st.curl > 0) {
    const w = st.curlWob || 0, P = []; boilSeed('curl');
    for (let k = 0; k <= 40; k++) { const u = k / 40, a = u * TAU * 4.5, h = u * 150 * st.curl; P.push([Math.cos(a) * 16 * (1 - u * .3) + w * 60 * u * u, -80 - h + Math.sin(a) * 5]); }
    inkLine(P, 2.2, '#BFC8D8', 'inkfine', .4);
    inkLine(P.map(([a, b]) => [a + 2, b - 2]), 1, '#FFFFFF', 'inkfine', .4);
  }
  pop();
  pop();
}
function managerFace(t, x, y, f) {
  const lx = (f.look || 0) * 10, ly = (f.lookY || 0) * 8, e = f.eyes || 'dot';
  // 圆眼镜
  for (const s of [-1, 1]) paint(circPts(x + s * 30 + lx * .3, y - 4, 23, 16), { wash: '#FFFFFF', washOp: 120, ink: INK, sw: .9 });
  inkLine([[x - 7, y - 6], [x + 7, y - 6]], .9, INK, 'inkfine', 0);
  for (const s of [-1, 1]) {
    const ex = x + s * 30 + lx, ey = y - 4 + ly;
    if (e === 'dot') paint(ellPts(ex, ey, 6, 8, 8), { wash: INK, ink: null });
    else if (e === 'wide') { paint(ellPts(ex, ey, 11, 13, 10), { wash: INK, ink: null }); paint(ellPts(ex - 3, ey - 4, 3, 3, 6), { wash: CREAM, ink: null }); }
    else if (e === 'happy') inkLine(arcPts(ex, ey + 6, 11, Math.PI * 1.1, Math.PI * 1.9, 8), 1.6, INK, 'ink', .5);
    else if (e === 'half') { inkLine([[ex - 12, ey - 2], [ex + 12, ey - 2]], 1.4, INK, 'ink', 0); paint(ellPts(ex, ey + 3, 6, 4, 8), { wash: INK, ink: null }); }
    else if (e === 'closed') inkLine([[ex - 11, ey], [ex + 11, ey]], 1.6, INK, 'ink', 0);
    else if (e === 'cry') inkLine([[ex - 12, ey - 4], [ex, ey + 2], [ex + 12, ey - 4]], 1.6, INK, 'ink', .3);
    else if (e === 'heart') paint(heartPts(ex, ey, 14), { wash: '#E2476E', ink: INK, sw: .6 });
    else if (e === 'star') paint(starPts(ex, ey, 15, .45, 5), { wash: HARD, ink: INK, sw: .6 });
  }
  // 眉毛
  const br = f.brow || 0;
  for (const s of [-1, 1]) inkLine([[x + s * 18, y - 34 - br * 8], [x + s * 42, y - 36 + br * s * 0 - (br > 0 ? br * 12 : br * -6)]], 1.4, INK, 'ink', 0);
  // 八字胡
  paint(ribbon([[x - 34, y + 30], [x - 14, y + 22], [x, y + 26], [x + 14, y + 22], [x + 34, y + 30]], 14, 6), { wash: '#4A3A34', ink: null });
  const m = f.mouth, my = y + 44;
  if (m === 'chew') { const o = .5 + .5 * Math.sin(t * 22); paint(ellPts(x, my, 12, 3 + 7 * o, 10), { wash: '#6A2D3A', ink: INK, sw: .6 }); }
  else if (m === 'O') paint(ellPts(x, my + 2, 12, 15, 12), { wash: '#6A2D3A', ink: INK, sw: .7 });
  else if (m === 'wail') paint(ellPts(x, my + 4, 22, 17, 12), { wash: '#6A2D3A', ink: INK, sw: .7 });
  else if (m === 'flat') inkLine([[x - 16, my], [x + 16, my]], 1.4, INK, 'ink', 0);
  else if (m === 'smile') inkLine(arcPts(x, my - 12, 20, .5, Math.PI - .5, 10), 1.6, INK, 'ink', .5);
  else if (m === 'grin') paint(arcPts(x, my - 10, 24, .15, Math.PI - .15, 12), { wash: '#7A2E3B', ink: INK, sw: .7 });
  else if (m === 'puff') { for (const s of [-1, 1]) paint(ellPts(x + s * 46, y + 30, 20, 17, 10), { wash: '#F7B89A', ink: INK, sw: .5 }); inkLine([[x - 7, my], [x + 7, my]], 1.2, INK, 'ink', 0); }
  if (f.blush > 0) for (const s of [-1, 1]) paint(ellPts(x + s * 52, y + 20, 14, 8, 10), { wash: PAL.rose, washOp: 200 * f.blush, ink: null });
  if (f.tears > 0) for (const s of [-1, 1]) { boilSeed('tears' + s); const k = f.tears, P = []; for (let j = 0; j < 6; j++) P.push([x + s * (32 + j * 9 + Math.sin(t * 20 + j) * 3), y + 10 + j * 22 * k]); paint(ribbon(P, 10, 16), { wash: PAL.sky, washOp: 230, ink: INK, sw: .4 }); }
  if (f.sweat > 0) { boilSeed('msweat'); const k = f.sweat; paint([[x + 80, y - 60], [x + 92, y - 36], [x + 80, y - 26], [x + 68, y - 36]], { wash: PAL.sky, washOp: 255 * k, ink: INK, sw: .5, curv: .6 }); }
}

// ---------- 开明高新木箱 ----------
function crate(t, x, y, st) {
  const w = 260, h = 210, sq = st.sq || 0;
  push(); translate(x + (st.dx || 0), y + (st.dy || 0)); rotate(st.rot || 0); scale(1 + sq * .6, 1 - sq);
  boilSeed('crate');
  paint(rectPts(-w / 2, -h, w, h, 2), { wash: '#C98B4E', ink: INK, sw: 1 });
  for (let k = 1; k < 4; k++) inkLine([[-w / 2 + 6, -h + k * h / 4], [w / 2 - 6, -h + k * h / 4]], .6, '#8E5A2C', 'inkfine', 0);
  inkLine([[-w / 2 + 10, -10], [w / 2 - 10, -h + 10]], 1.4, '#8E5A2C', 'ink', 0);
  paint(rectPts(-w / 2 - 8, -h - 4, 22, h + 6, 1), { wash: '#A86B38', ink: INK, sw: .7 });
  paint(rectPts(w / 2 - 14, -h - 4, 22, h + 6, 1), { wash: '#A86B38', ink: INK, sw: .7 });
  // 标签
  paint(rectPts(-86, -h + 40, 172, 92, 1), { wash: CREAM, washOp: 235, ink: INK, sw: .6 });
  const [lx, ly] = toScreen(x + (st.dx || 0), y + (st.dy || 0) - h + 86);
  if (st.label !== false) letter('开明高新', lx, ly - 12 * (CAM ? CAM.zoom : 1), 40 * (CAM ? 1 : 1), '#C4452F', { font: `${40 * (CAM ? CAM.zoom : 1)}px "Smiley Sans"`, ink: false, rot: (st.rot || 0) + (CAM ? CAM.rot : 0), screen: true });
  if (st.label !== false) letter('在线修复 · 小心轻放', lx, ly + 24 * (CAM ? CAM.zoom : 1), 18, INK, { font: `${18 * (CAM ? CAM.zoom : 1)}px "ZCOOL KuaiLe"`, ink: false, rot: (st.rot || 0), screen: true });
  // 盖子
  const lid = st.lid || 0, peek = st.peek || 0;
  if (lid < 1) {
    push(); translate(0, -h - peek * 34); rotate(-peek * .08);
    if (peek > .05) { paint(rectPts(-w / 2 + 8, 0, w - 16, peek * 34, 0), { wash: '#2A2030', ink: null }); }
    boilSeed('crate lid');
    paint(rectPts(-w / 2 - 12, -22, w + 24, 26, 1.5), { wash: '#B8773F', ink: INK, sw: .9 });
    pop();
    if (peek > .3) for (const s of [-1, 1]) paint(rrPts(s * 26 - 7, -h - peek * 30 + 4, 14, 22 * peek, 7), { wash: CREAM, ink: null });
  }
  pop();
}

// ---------- 车刀架（在线车削工具），刀尖在 (x, y) ----------
function toolPost(t, x, y, st) {
  boilSeed('toolpost');
  const cut = st.cut || 0;
  // 立柱与底座（开明橙）
  paint(rectPts(x - 250, y + 40, 64, GROUND - y - 60, 2), { wash: '#E0873C', ink: INK, sw: 1 });
  for (let k = 0; k < 5; k++) { const yy = y + 80 + k * 90; inkLine([[x - 250, yy], [x - 186, yy + 60]], .8, '#9C4F1C', 'inkfine', 0); }
  paint(rectPts(x - 320, GROUND - 40, 200, 40, 2), { wash: '#6E7C9C', ink: INK, sw: .9 });
  for (const wx of [x - 300, x - 140]) paint(circPts(wx, GROUND, 22, 12), { wash: INK, ink: null });
  // 刀座 + 刀杆
  paint(rectPts(x - 270, y - 30, 130, 80, 2), { wash: '#6E7C9C', ink: INK, sw: 1 });
  paint([[x - 150, y - 12], [x - 6 + cut * 3, y - 4], [x, y + 4], [x - 150, y + 16]], { wash: STEEL_LT, ink: INK, sw: .9 });
  // 手轮
  const a = st.crank || 0;
  paint(circPts(x - 290, y + 10, 34, 16), { wash: null, ink: INK, sw: 1.1 });
  inkLine([[x - 290, y + 10], [x - 290 + Math.cos(a) * 34, y + 10 + Math.sin(a) * 34]], 1.4, INK, 'ink', 0);
}

// ---------- 百分表“跳动”（屏幕坐标仪表，原片的 P(DOOM) 温度计换成它） ----------
function dialUI(t, cx, cy, r, ang, k = 1) {
  if (k <= .01) return;
  boilSeed('dial');
  push(); translate(cx, cy); scale(k);
  paint(rectPts(-12, r * .92, 24, r * .55, 1), { wash: STEEL, ink: INK, sw: .8 });      // 测杆
  paint(circPts(0, r * 1.5, 14, 10), { wash: STEEL_DK, ink: INK, sw: .6 });
  paint(circPts(0, 0, r, 36), { wash: STEEL, ink: INK, sw: 1.2 });
  paint(circPts(0, 0, r * .84, 36), { wash: '#FFF8EA', ink: INK, sw: .7 });
  paint([...arcPts(0, 0, r * .8, -Math.PI / 2 + 1.7, -Math.PI / 2 + 2.6, 8), ...arcPts(0, 0, r * .62, -Math.PI / 2 + 2.6, -Math.PI / 2 + 1.7, 8)], { wash: '#F08A7A', washOp: 200, ink: null });
  paint([...arcPts(0, 0, r * .8, -Math.PI / 2 - 2.6, -Math.PI / 2 - 1.7, 8), ...arcPts(0, 0, r * .62, -Math.PI / 2 - 1.7, -Math.PI / 2 - 2.6, 8)], { wash: '#F08A7A', washOp: 200, ink: null });
  for (let i = 0; i < 20; i++) { const a = -Math.PI / 2 + i / 20 * TAU, l = i % 5 === 0 ? .2 : .1; inkLine([[Math.cos(a) * r * .82, Math.sin(a) * r * .82], [Math.cos(a) * r * (.82 - l), Math.sin(a) * r * (.82 - l)]], i % 5 ? .6 : 1, INK, 'inkfine', 0); }
  const na = -Math.PI / 2 + ang;
  paint(ribbon([[-Math.cos(na) * r * .15, -Math.sin(na) * r * .15], [Math.cos(na) * r * .72, Math.sin(na) * r * .72]], r * .09, r * .02), { wash: '#D8433A', ink: INK, sw: .5 });
  paint(circPts(0, 0, r * .1, 10), { wash: INK, ink: null });
  pop();
  letter('跳动', cx, cy + r * .42 * k, r * .24 * k, INK, { font: `${r * .24 * k}px "ZCOOL KuaiLe"`, ink: false, screen: true });
}

// ---------- 大齿圈工位 ----------
// st: rot（齿圈转角）, grow（缺齿长出 0..1）, weld（焊光 0..1）
const GEAR_MISS = 7;
function gearStation(t, st) {
  const { x, y, R, n, th } = GEAR, step = TAU / n;
  boilSeed('gear pedestal');
  paint([[x - 330, GROUND - 170], [x + 330, GROUND - 170], [x + 380, GROUND + 6], [x - 380, GROUND + 6]], { wash: '#B8AD9F', ink: INK, sw: .9 });
  // 小齿轮（右上）+ 电机
  const pa = -Math.PI / 3, pd = R + th + 100, px = x + Math.cos(pa) * pd, py = y + Math.sin(pa) * pd;
  boilSeed('motor');
  paint(rectPts(px + 40, py - 70, 260, 150, 3), { wash: '#6E7C9C', ink: INK, sw: .9 });
  paint(rectPts(px + 100, py + 80, 60, GROUND - py - 80, 2), { wash: '#8A93A8', ink: INK, sw: .8 });
  boilSeed('pinion');
  paint(gearPts(px, py, 100, 12, 30, -st.rot * (R / 100) + .2), { wash: '#B6904A', ink: INK, sw: 1 });
  paint(circPts(px, py, 30, 12), { wash: STEEL_DK, ink: INK, sw: .7 });
  // 大齿圈
  boilSeed('gear');
  paint(gearPts(x, y, R, n, th, st.rot, i => i === GEAR_MISS ? (st.grow ?? 0) : 1), { wash: '#D1A85A', ink: INK, sw: 1.2 });
  if ((st.grow ?? 0) > .05 && st.hot > 0) { const a0 = st.rot + GEAR_MISS * step; boilSeed('hot tooth'); paint(gearPts(x, y, R - 2, n, th, st.rot, i => i === GEAR_MISS ? st.grow : 0).filter((p2, j) => j >= GEAR_MISS * 4 - 1 && j <= GEAR_MISS * 4 + 4), { wash: mixCol('#D1A85A', '#E8F6FF', st.hot), ink: INK, sw: .9 }); }
  paint(circPts(x, y, R * .82, 40), { wash: '#B68E45', ink: INK, sw: .8 });
  for (let k = 0; k < 6; k++) { const a = st.rot + k * TAU / 6; paint(circPts(x + Math.cos(a) * R * .5, y + Math.sin(a) * R * .5, R * .16, 16), { wash: '#6F5A3A', ink: INK, sw: .6 }); }
  paint(circPts(x, y, R * .24, 20), { wash: STEEL, ink: INK, sw: .9 });
  // 缺齿提示：红色虚线圈（焊之前）
  if (st.hint > 0) { const a = st.rot + (GEAR_MISS + .34) * step, cx = x + Math.cos(a) * (R + th * .5), cy = y + Math.sin(a) * (R + th * .5); boilSeed('hint'); for (let k = 0; k < 8; k++) { const b0 = k / 8 * TAU + t * 3; inkLine(arcPts(cx, cy, 52 * st.hint, b0, b0 + .45, 4), 1.6, '#D8433A', 'ink', .5); } }
  // 新齿发亮
  if ((st.grow ?? 0) > 0 && st.grow < 1.2) {
    const a = st.rot + (GEAR_MISS + .34) * step;
    glow(x + Math.cos(a) * (R + th * .5), y + Math.sin(a) * (R + th * .5), 70 * (st.weld || 0) + 10, '#9FD8FF', st.weld || 0);
  }
  return { pinion: [px, py] };
}
// 缺齿中心的世界角
const toothAngle = rot => rot + (GEAR_MISS + .34) * TAU / GEAR.n;

// ---------- 云上行业岛 ----------
const ISLES = [
  { x: -1600, y: -2560, kind: 'cement', zh: '水泥', en: 'Cement' },
  { x: -800, y: -2660, kind: 'steel', zh: '钢铁', en: 'Steel' },
  { x: 0, y: -2560, kind: 'chem', zh: '化工', en: 'Chemical' },
  { x: 800, y: -2660, kind: 'power', zh: '电力', en: 'Power' },
  { x: 1600, y: -2560, kind: 'mine', zh: '矿山', en: 'Mining' },
];
function cloud(x, y, s, key, col = '#FFF8EE', a = 235) {
  // 多个圆的并集外轮廓：取每个圆上不落在其它圆里的点，再按角度排序
  boilSeed('cloud' + key);
  const C = []; const n = 5 + Math.floor(hash(key.length * 7.1 + x) * 3);
  for (let k = 0; k < n; k++) { const u = k / (n - 1) - .5; C.push([x + u * 420 * s, y - (1 - 4 * u * u) * 55 * s + hash(k + x) * 12 * s, (58 + 38 * (1 - 4 * u * u) + 18 * hash(k * 3 + y)) * s]); }
  C.push([x - 120 * s, y + 30 * s, 60 * s], [x + 120 * s, y + 30 * s, 60 * s]);
  const P = [];
  for (const [cx, cy, r] of C) for (let i = 0; i < 20; i++) { const q = i / 20 * TAU, px = cx + Math.cos(q) * r, py = cy + Math.sin(q) * r; if (!C.some(([ox, oy, orr]) => (ox !== cx || oy !== cy) && Math.hypot(px - ox, py - oy) < orr - 1)) P.push([px, py]); }
  const mx = P.reduce((u, p) => u + p[0], 0) / P.length, my = P.reduce((u, p) => u + p[1], 0) / P.length;
  P.sort((p, q) => Math.atan2(p[1] - my, p[0] - mx) - Math.atan2(q[1] - my, q[0] - mx));
  paint(P, { wash: col, washOp: a, ink: '#9FA9C4', sw: .6 });
}
function isle(t, I, on, idx) {
  const { x, y } = I, lit = on;
  const col = c => mixCol(mixCol('#C9C4D4', c, .5), c, lit);   // 未点亮时半饱和，点亮后全彩
  boilSeed('isle' + idx);
  cloud(x, y + 150, 1.5, 'under' + idx, '#FFFFFF', 200);
  paint([[x - 300, y], [x + 300, y], [x + 200, y + 110], [x + 60, y + 230], [x - 90, y + 170], [x - 220, y + 100]], { wash: col('#B89A7A'), ink: INK, sw: .9, curv: .25 });
  paint(ellPts(x, y, 305, 40, 24, 2), { wash: col('#9CC27E'), ink: INK, sw: .9 });
  boilSeed('bld' + idx);
  const k = I.kind;
  if (k === 'cement') {
    paint(rectPts(x - 250, y - 330, 90, 320, 2), { wash: col('#C9B79E'), ink: INK, sw: .7 });
    paint(rrPts(x - 150, y - 150, 330, 80, 40), { wash: col(STEEL), ink: INK, sw: .8 });
    for (const tx of [x - 60, x + 100]) paint(rectPts(tx, y - 160, 30, 100, 1), { wash: col(STEEL_DK), ink: INK, sw: .6 });
  } else if (k === 'steel') {
    paint([[x - 90, y - 10], [x - 60, y - 360], [x + 60, y - 360], [x + 90, y - 10]], { wash: col('#7C6F88'), ink: INK, sw: .8 });
    paint(rectPts(x - 70, y - 400, 140, 40, 1), { wash: col(STEEL_DK), ink: INK, sw: .6 });
    paint(ellPts(x, y - 60, 50, 30, 12), { wash: col('#FF8A3D'), ink: null });
    if (lit > .5) glow(x, y - 60, 90, '#FF8A3D', lit * .8);
    paint(rectPts(x + 120, y - 250, 40, 240, 1), { wash: col('#E7DCC8'), ink: INK, sw: .6 });
  } else if (k === 'chem') {
    for (const [tx, h, w] of [[-170, 330, 50], [-90, 420, 40], [0, 280, 60]]) paint(rrPts(x + tx, y - h, w, h, w / 2), { wash: col('#DDE3EC'), ink: INK, sw: .7 });
    paint(circPts(x + 160, y - 100, 90, 24), { wash: col('#9FC8C4'), ink: INK, sw: .8 });
  } else if (k === 'power') {
    paint([[x - 170, y - 10], [x - 110, y - 200], [x - 140, y - 360], [x + 140, y - 360], [x + 110, y - 200], [x + 170, y - 10]], { wash: col('#D9D4CF'), ink: INK, sw: .8, curv: .3 });
    for (let i = 0; i < 3; i++) { const age = frac(t * .5 + i / 3); boilSeed('steam' + i); paint(ellPts(x + Math.sin(i * 2) * 30, y - 380 - age * 180, 80 + age * 60, 50 + age * 30, 12, 3), { wash: '#FFFFFF', washOp: 200 * (1 - age) * lit, ink: null }); }
  } else {
    paint(rrPts(x - 200, y - 190, 300, 150, 70), { wash: col('#9AA7BD'), ink: INK, sw: .8 });
    paint(rectPts(x - 20, y - 205, 34, 180, 1), { wash: col('#D1A85A'), ink: INK, sw: .6 });
    paint([[x + 120, y - 10], [x + 190, y - 150], [x + 270, y - 10]], { wash: col('#8E7A66'), ink: INK, sw: .7 });
  }
}

// 噩梦画在气泡的局部缩放里；文字要先从局部坐标换回世界坐标再上屏
const NM = { x: 0, y: 0, s: 1 };
const nmScreen = (lx, ly) => toScreen(NM.x + lx * NM.s, NM.y + ly * NM.s);
// ---------- 噩梦气泡里的东西（气泡局部坐标：1080×1920 画面，原点在中心） ----------
function nightmare(t) {
  const G0 = 430;   // 局部地面
  boilSeed('nm ground');
  paint(ellPts(0, G0 + 170, 560, 190, 28, 6), { wash: '#3A2C5E', ink: null });
  // 吊车：钩子下来 → 吊起窑宝 → 横移 → 放到卡车上（10.0 卡车被压扁）
  const lift = ease(seg(t, 9.0, 9.45)), swing = ease(seg(t, 9.45, 9.85)), lower = easeIn(seg(t, 9.85, 10.0));
  const flat = t >= 10, fk = flat ? .35 + .08 * Math.exp(-(t - 10) * 8) * Math.cos((t - 10) * 30) : 1;
  const tx = lerp(900, 230, easeOut(seg(t, 9.1, 9.6)));
  const kx = lerp(-150, 230, swing);
  const onTruck = G0 - 120 * fk - 170;
  const ky = flat ? onTruck : lerp(lerp(G0 - 190, G0 - 560, lift), G0 - 290, lower);
  const hookY = t < 9.0 ? lerp(-1000, G0 - 400, easeOut(seg(t, 8.4, 9.0))) : t < 10 ? ky - 210 : lerp(ky - 210, -900, easeIn(seg(t, 10, 10.5)));
  boilSeed('crane');
  paint(rectPts(-520, -980, 70, 1420, 2), { wash: '#E0873C', ink: INK, sw: .8 });
  paint(rectPts(-520, -980, 1100, 60, 2), { wash: '#E0873C', ink: INK, sw: .8 });
  const hx = kx;
  inkLine([[hx, -920], [hx, hookY]], 1.2, INK, 'ink', 0);
  inkLine([[hx, hookY], [hx + 20, hookY + 40], [hx, hookY + 60], [hx - 16, hookY + 44]], 1.8, INK, 'ink', .5);
  push(); translate(tx, G0); scale(1 + (1 - fk) * .5, fk);
  boilSeed('truck');
  paint(rectPts(-150, -110, 300, 80, 2), { wash: '#D96B55', ink: INK, sw: .8 });
  paint(rectPts(80, -170, 90, 140, 2), { wash: '#D96B55', ink: INK, sw: .8 });
  paint(rectPts(100, -150, 50, 45, 1), { wash: '#BFE3F0', ink: INK, sw: .5 });
  pop();
  for (const wx of [-90, 110]) { boilSeed('wheel' + wx); const off = flat ? (wx < 0 ? -1 : 1) * 60 * easeOut(seg(t, 10, 10.2)) : 0; paint(circPts(tx + wx + off, G0 - 10, 34, 12), { wash: INK, ink: null }); }
  // 被吊走的窑宝（简化小脸盘）
  const kxx = flat ? tx : kx;
  boilSeed('nm kiln');
  paint(circPts(kxx, ky, 190, 36), { wash: STEEL, ink: INK, sw: 1 });
  paint(circPts(kxx, ky, 150, 30), { wash: '#A9B4A4', ink: INK, sw: .8 });
  kilnFace(t, kxx, ky - 20, { eyes: flat ? 'swirl' : 'squeeze', mouth: 'wobble', tint: 1, sweat: 1 });
  // 日历 1 → 60 天
  if (t > 10.3) {
    const k = backOut(seg(t, 10.3, 10.55)), day = Math.round(lerp(1, 60, easeIn(seg(t, 10.4, 11.2))));
    boilSeed('cal');
    push(); translate(170, -520); scale(k); rotate(.08);
    paint(rectPts(-150, -150, 300, 320, 2), { wash: CREAM, ink: INK, sw: 1 });
    paint(rectPts(-150, -150, 300, 80, 1), { wash: '#D8433A', ink: INK, sw: .8 });
    const flip = frac(t * 14);
    if (t < 11.2) paint([[-150, -70], [150, -70], [150, -70 + 240 * (1 - flip)], [-150, -70 + 240 * (1 - flip) * .9]], { wash: '#FFFDF6', ink: INK, sw: .5 });
    pop();
    const [sx, sy] = nmScreen(170, -430), fz = 150 * NM.s * (CAM ? CAM.zoom : 1) * k;
    letter(`${day}天`, sx, sy, fz, INK, { font: `${fz}px "Smiley Sans"`, ink: false, screen: true, rot: .08 });
  }
  // 长翅膀的硬币飞走
  for (let i = 0; i < 7; i++) {
    const b = 11.0 + i * .07, age = t - b; if (age < 0 || age > 1) continue;
    const cx = -100 + i * 60 + Math.sin(age * 6 + i) * 40 + age * (i - 3) * 120, cy = G0 - 80 - age * 900;
    boilSeed('coin' + i);
    const fl = Math.sin(t * 40 + i) * 25;
    paint([[cx - 22, cy], [cx - 70, cy - 30 - fl], [cx - 40, cy + 10]], { wash: '#FFFFFF', ink: INK, sw: .5 });
    paint([[cx + 22, cy], [cx + 70, cy - 30 - fl], [cx + 40, cy + 10]], { wash: '#FFFFFF', ink: INK, sw: .5 });
    paint(circPts(cx, cy, 30, 14), { wash: HARD, ink: INK, sw: .7 });
    const [sx, sy] = nmScreen(cx, cy), fz = 40 * NM.s * (CAM ? CAM.zoom : 1);
    letter('¥', sx, sy, fz, '#9C6A10', { font: `700 ${fz}px "Fredoka"`, ink: false, screen: true });
  }
}
