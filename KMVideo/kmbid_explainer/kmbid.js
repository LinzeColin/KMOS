// kmbid.js: KMBID 搜标网站讲解片（62 秒）。分镜见 STORYBOARD.md。
(() => {
  const C = { wall: '#F1E6D2', floor: '#D9C3A0', sky: '#DCEAF6', blue: '#6E9BD8', blueDk: '#4C78B8', night: '#232E5C',
    navy: '#2F3C7A', gold: '#F2C14E', goldDk: '#D69A2A', green: '#5FAE6A', red: '#E0605A', violet: '#8A6CC0',
    card: '#FFFDF6', desk: '#C08F62', deskDk: '#946945', morning: '#F7DDB0', rose: '#E88AA0' };
  const URL = 'kmbid.linzezhang.com';

  // ---------- 开明 Logo：图片随字幕层一起合成 ----------
  const LOGO = new Image(); LOGO.src = 'assets/km_logo.png';
  const EMB = new Image(); EMB.src = 'assets/km_emblem.png';
  const loaded = img => new Promise(ok => { if (img.complete) ok(); else { img.onload = ok; img.onerror = ok; } });   // decode() stalls in background tabs
  (window.PRELOAD ||= []).push(loaded(LOGO), loaded(EMB), document.fonts.load('64px Smiley', '开明搜标网站'));
  const _drawLetters = drawLetters;
  drawLetters = c => {
    for (const L of LETTERS) if (L.img) {
      const k = L.pop != null ? backOut(L.pop) : 1; if (k <= .01) continue;
      c.save(); c.globalAlpha = L.alpha ?? 1; c.translate(L.x, L.y); c.rotate(L.rot || 0); c.scale(k, k);
      c.drawImage(L.img, -L.w / 2, -L.h / 2, L.w, L.h); c.restore();
    }
    const all = LETTERS; LETTERS = all.filter(L => !L.img); _drawLetters(c); LETTERS = all;
  };
  const image = (img, x, y, w, o = {}) => {
    let h = w * img.naturalHeight / img.naturalWidth;
    if (CAM && !o.screen) { [x, y] = toScreen(x, y); w *= CAM.zoom; h *= CAM.zoom; }
    LETTERS.push({ img, x, y, w, h, ...o });
  };
  const brand = (a = 1) => image(LOGO, 250, 54, 420, { screen: true, alpha: a });

  // ---------- 字幕与讲解员口型 ----------
  const CAPS = [
    [1.0, 4.0, '每天翻几十个网站找标'], [4.3, 6.6, '……好累！'],
    [7.9, 10.8, '试试这个搜标网站'], [11.0, 13.8, '不注册、不用学，打开就能用'],
    [14.8, 18.6, '几十个招标网站的公告'], [18.9, 22.6, '自动汇到一个网站里看'],
    [23.8, 27.4, '每天自动更新'], [27.6, 29.8, '睡一觉，新标就到了'],
    [30.6, 33.4, 'AI 找机会，你来判断'], [33.6, 36.4, '看一眼，回一句：要 / 不要 / 待确认'], [36.6, 40.2, '反馈越多，推得越准'],
    [41.2, 44.8, '更多好机会，更多中标'], [45.0, 50.6, '公司业绩涨了，大家的提成、奖金、绩效才能涨'],
    [51.8, 55.0, '对公司好，对每个人都好'], [55.2, 58.0, '不用学技术，也不用懂 AI'], [58.2, 61.6, '打开网站就好'],
  ];
  const say = (txt, x, y, size, col, t, a, b, o = {}) => letter(txt, x, y, size, col, {
    font: `${size}px Smiley`, stroke: o.stroke ?? PAL.ink, ink: o.ink ?? true, pop: Math.min(1, (t - a) * 4), alpha: 1 - seg(t, b - .2, b), screen: true, ...o });
  function captions(t) { for (const [a, b, txt] of CAPS) if (t >= a && t <= b) say(txt, 960, 128, 66, PAL.cream, t, a, b); }
  const talk = t => Math.max(0, ...CAPS.map(([a, b]) => speak(t, a + .1, b - .35)));
  const narrator = (t, mood) => ({ ...mood, mouth: talk(t) > .22 ? 'open' : (mood.mouth || 'smile') });

  // ---------- 道具 ----------
  const P = (pts, x = 0, y = 0, s = 1) => pts.map(([a, b]) => [x + a * s, y + b * s]);
  function room(wall, floor = C.floor, fy = 930) {
    boilSeed('wall'); paint(rectPts(-1400, -1400, W + 2800, H + 2800), { wash: wall, ink: null });
    boilSeed('floor'); paint(rectPts(-1400, fy, W + 2800, 1400), { wash: floor, ink: null }); inkLine([[-900, fy], [W / 2, fy + 2], [W + 900, fy]], .6, PAL.ink, 'ink', .3);
  }
  function sheet(x, y, s, rot, col = C.card, key = 'p') {
    boilSeed(key); push(); translate(x, y); rotate(rot);
    paint(rectPts(-s * 1.4, -s * 1.8, s * 2.8, s * 3.6, s * .04), { wash: col, ink: PAL.ink, sw: .7 });
    for (let i = 0; i < 4; i++) inkLine([[-s, -s * 1.1 + i * s * .6], [s * (i === 3 ? .2 : 1), -s * 1.1 + i * s * .6]], .45, PAL.indigo, 'inkfine', 0);
    pop();
  }
  function pile(x, y, n) {
    for (let i = 0; i < n; i++) {
      boilSeed('pile' + i);
      const ox = (hash(i * 3.1) - .5) * 40, r = (hash(i * 7.7) - .5) * .12;
      push(); translate(x + ox, y - i * 15); rotate(r);
      paint(rectPts(-120, -9, 240, 16, 1.5), { wash: i % 5 === 2 ? '#F4EFE4' : C.card, ink: PAL.ink, sw: .55 });
      pop();
    }
  }
  function card(x, y, w, h, i, mark = null, k = 1) {
    if (k <= .01) return;
    boilSeed('card' + i); push(); translate(x, y); scale(backOut(k));
    paint(rrPts(-w / 2, -h / 2, w, h, 12, 1), { wash: C.card, ink: PAL.ink, sw: .7 });
    paint(rrPts(-w / 2 + 14, -h / 2 + 14, h - 28, h - 28, 8), { wash: [C.blue, C.green, C.gold, C.rose, C.violet][i % 5], ink: null });
    inkLine([[-w / 2 + h, -h * .14], [w / 2 - 30, -h * .14]], .7, PAL.ink, 'inkfine', 0);
    inkLine([[-w / 2 + h, h * .18], [w * .1, h * .18]], .5, mixCol(PAL.ink, C.card, .5), 'inkfine', 0);
    if (mark) stampMark(w / 2 - 40, 0, h * .42, mark);
    pop();
  }
  function stampMark(x, y, s, m) {
    if (m === 'yes') inkLine(P([[-.8, 0], [-.2, .6], [.9, -.7]], x, y, s), 3.2, C.green, 'ink', 0);
    else if (m === 'no') { inkLine(P([[-.7, -.7], [.7, .7]], x, y, s), 3.2, C.red, 'ink', 0); inkLine(P([[.7, -.7], [-.7, .7]], x, y, s), 3.2, C.red, 'ink', 0); }
    else emote('?', x, y + s * .2, s * .55, 1, 1);
  }
  function browser(x, y, w, h, n, key = 'win') {
    boilSeed(key);
    paint(rrPts(x - w / 2, y - h / 2, w, h, 22, 1.5), { wash: '#FBF8F1', ink: PAL.ink, sw: 1 });
    paint(rrPts(x - w / 2, y - h / 2, w, 78, 22, 1), { wash: C.blue, ink: PAL.ink, sw: .8 });
    [C.red, C.gold, C.green].forEach((c, i) => paint(ellPts(x - w / 2 + 34 + i * 32, y - h / 2 + 39, 10, 10, 10), { wash: c, ink: null }));
    paint(rrPts(x - w / 2 + 140, y - h / 2 + 18, w - 180, 42, 20), { wash: C.card, ink: PAL.ink, sw: .5 });
    letter(URL, x + 50, y - h / 2 + 40, 30, PAL.ink, { font: '30px Smiley', ink: false });
    const ch = 76, top = y - h / 2 + 130;
    for (let i = 0; i < 6; i++) { const k = clamp(n - i); if (top + i * (ch + 14) + ch / 2 > y + h / 2 - 10) break; card(x, top + i * (ch + 14), w - 80, ch, i, null, k); }
  }
  function funnel(x, y) {
    boilSeed('funnel');
    paint([[x - 200, y], [x + 200, y], [x + 50, y + 170], [x + 50, y + 240], [x - 50, y + 240], [x - 50, y + 170]], { wash: C.gold, ink: PAL.ink, sw: 1 });
    paint(ellPts(x, y, 200, 34, 28), { wash: C.goldDk, ink: PAL.ink, sw: .9 });
  }
  function site(x, y, col, i) {
    boilSeed('site' + i);
    paint(rrPts(x - 80, y - 58, 160, 116, 12, 1), { wash: C.card, ink: PAL.ink, sw: .7 });
    paint(rrPts(x - 80, y - 58, 160, 26, 10), { wash: col, ink: PAL.ink, sw: .5 });
    for (let k = 0; k < 3; k++) inkLine([[x - 58, y - 12 + k * 22], [x + (k === 2 ? 10 : 58), y - 12 + k * 22]], .45, PAL.indigo, 'inkfine', 0);
  }
  function book(x, y, rot, key = 'book') {
    boilSeed(key); push(); translate(x, y); rotate(rot);
    paint(rrPts(-120, -80, 240, 160, 10, 1), { wash: C.violet, ink: PAL.ink, sw: 1 });
    paint(rectPts(96, -74, 20, 148), { wash: C.card, ink: PAL.ink, sw: .5 });
    pop();
    letter('AI 教程', x, y, 40, PAL.cream, { font: '40px Smiley', rot, ink: false });
  }
  function desk(x, y, w) {
    boilSeed('desk');
    paint(rectPts(x - w / 2, y, w, 30, 1), { wash: C.desk, ink: PAL.ink, sw: .9 });
    for (const s of [-1, 1]) paint(rectPts(x + s * (w / 2 - 40) - 14, y + 30, 28, 930 - y + 10), { wash: C.deskDk, ink: PAL.ink, sw: .7 });
  }
  function laptop(x, y, n, glowK = 0) {
    boilSeed('laptop');
    if (glowK) glow(x, y - 120, 260, '#BFE0FF', glowK);
    paint([[x - 190, y], [x + 190, y], [x + 220, y + 18], [x - 220, y + 18]], { wash: '#9AA6BF', ink: PAL.ink, sw: .8 });
    paint(rrPts(x - 180, y - 250, 360, 250, 14), { wash: '#39456E', ink: PAL.ink, sw: .9 });
    paint(rrPts(x - 164, y - 236, 328, 222, 8), { wash: '#FBF8F1', ink: null });
    for (let i = 0; i < 3; i++) card(x, y - 196 + i * 66, 290, 54, i + 7, null, clamp(n - i));
  }
  function coin(x, y, r, spin, key) {
    boilSeed(key); const rx = r * Math.max(.12, Math.abs(Math.cos(spin)));
    paint(ellPts(x, y, rx, r, 20), { wash: C.gold, ink: PAL.ink, sw: .8 });
    if (rx > r * .5) paint(ellPts(x, y, rx * .62, r * .62, 16), { wash: '#F8D776', ink: C.goldDk, sw: .5 });
  }
  function target(x, y, r) {
    boilSeed('target');
    [[1, C.red], [.75, C.card], [.5, C.red], [.25, C.card], [.1, C.gold]].forEach(([k, c]) => paint(ellPts(x, y, r * k, r * k, 30), { wash: c, ink: PAL.ink, sw: .7 }));
    paint(rectPts(x - 12, y + r, 24, 930 - y - r), { wash: C.deskDk, ink: PAL.ink, sw: .6 });
  }
  function arrow(x, y, k, key) {
    if (k <= 0) return;
    boilSeed(key); const len = 150, ang = -.35, sx = x - Math.cos(ang) * len * 3 * (1 - k), sy = y - Math.sin(ang) * len * 3 * (1 - k);
    inkLine([[sx - Math.cos(ang) * len, sy - Math.sin(ang) * len], [sx, sy]], 1.6, PAL.ink, 'ink', 0);
    paint(P([[-1, -.6], [0, 0], [-1, .6]], sx - Math.cos(ang) * len + 0, sy - Math.sin(ang) * len, 22), { wash: C.rose, ink: PAL.ink, sw: .5 });
  }
  function plane(x, y, s, rot, key) {
    boilSeed(key); push(); translate(x, y); rotate(rot);
    paint(P([[-1.4, -.5], [1.4, 0], [-1.4, .6], [-.8, 0]], 0, 0, s), { wash: C.card, ink: PAL.ink, sw: .7 });
    pop();
  }
  function bar(x, base, h, icon, k) {
    if (k <= 0) return;
    boilSeed('bar' + icon); const hh = h * backOut(k);
    paint(rrPts(x - 80, base - hh, 160, hh, 14, 1), { wash: [C.blue, C.green, C.gold, C.rose][icon], ink: PAL.ink, sw: .9 });
    const iy = base - hh - 70;
    if (k < .6) return;
    boilSeed('icon' + icon);
    if (icon === 0) { paint(ellPts(x - 10, iy - 10, 38, 38, 20), { wash: C.sky, ink: PAL.ink, sw: 1.4 }); inkLine([[x + 16, iy + 18], [x + 50, iy + 52]], 3, PAL.ink, 'ink', 0); }
    if (icon === 1) { paint(P([[-40, -46], [40, -46], [30, 0], [0, 16], [-30, 0]], x, iy), { wash: C.gold, ink: PAL.ink, sw: 1, curv: .3 }); paint(rectPts(x - 28, iy + 22, 56, 20), { wash: C.goldDk, ink: PAL.ink, sw: .6 }); }
    if (icon === 2) { paint(rectPts(x - 50, iy - 60, 100, 120, 1), { wash: C.card, ink: PAL.ink, sw: 1 }); for (let r = 0; r < 3; r++) for (let c = 0; c < 2; c++) paint(rectPts(x - 36 + c * 44, iy - 46 + r * 34, 28, 20), { wash: C.sky, ink: null }); image(EMB, x, iy - 88, 70); }
    if (icon === 3) { paint(P([[-44, -10], [-20, -40], [20, -40], [44, -10], [50, 40], [-50, 40]], x, iy), { wash: '#C9A06A', ink: PAL.ink, sw: 1, curv: .5 }); letter('¥', x, iy + 8, 48, PAL.cream, { font: '48px Smiley', ink: false }); }
  }
  function lantern(u) {
    glow(0, 0, u * 9, '#FFD27A', .9);
    paint(rrPts(-u * .9, -u * 1.1, u * 1.8, u * 2.2, u * .4), { wash: '#FFE8A6', ink: PAL.ink, sw: .6 });
  }

  // ---------- A 纸堆（0–7） ----------
  function shotPile(t, lt, dur) {
    camBegin(960 - 20 * lt, 560, 1 + .015 * lt);
    room(C.wall);
    const n = Math.min(38, 12 + Math.floor(lt * 5));
    pile(1180, 930, n);
    for (let i = 0; i < 7; i++) {   // 不停落下的公告
      const t0 = .2 + i * .8, k = seg(lt, t0, t0 + .9); if (k <= 0 || k >= 1) continue;
      sheet(1180 + Math.sin(k * 7 + i) * 90, lerp(-120, 930 - n * 15, easeIn(k)), 34, Math.sin(k * 9 + i) * .6, C.card, 'fall' + i);
    }
    const bear = emotions(lt, [[0, 'nervous'], [2.2, 'sad'], [4.2, 'dizzy'], [5.4, 'surprised', { lookX: 1 }]]);
    kmbear(720, 930, 28, { ...bear, view: 'q' });
    const hk = seg(lt, 3.7, 4.2);   // 砸头的那张
    if (hk > 0) sheet(lerp(900, 735, hk) + (hk < 1 ? Math.sin(hk * 12) * 30 : 0), lerp(-120, 930 - 13.4 * 28 - 20 * (1 - seg(lt, 4.2, 4.3)), easeIn(hk)), 30, hk < 1 ? Math.sin(hk * 10) : -.15 + .05 * spring(lt, 4.2), '#FFF3C4', 'bonk');
    const hop = jump(lt, 5.0, 5.5, 5), cx = lerp(1520, 1440, seg(lt, 5.0, 5.5));
    clawd(cx, 930, 16, { ...narrator(t, emotions(lt, [[0, 'neutral'], [5.1, 'idea']])), dy: hop.dy, sq: hop.sq, flip: true, noShadow: lt < 5 });
    camEnd();
    brand(); captions(t); flushLetters();
    if (lt < .5) iris(720, 520, lerp(0, 1500, easeIn(lt / .5)));
    if (lt > dur - .3) brushWipe((lt - (dur - .3)) / .6, [C.blueDk, C.blue]);
  }

  // ---------- B 网站（7–14） ----------
  function shotSite(t, lt, dur) {
    const push = easeIn(seg(lt, dur - .8, dur));
    camBegin(lerp(960, 1200, push), lerp(560, 470, push), 1 + push * 1.8);
    room(C.sky, '#C8D9C0');
    const wy = lerp(-700, 520, backOut(seg(lt, .5, 1.2)));
    browser(1200, wy, 900, 620, seg(lt, 1.4, 3.2) * 5);
    const st = stroll(lt, .6, 2.4, -200, 340, 28);
    const bear = emotions(lt, [[0, 'neutral'], [2.5, 'surprised', { lookX: 1 }], [3.3, 'hopeful'], [4.05, 'scared'], [5.3, 'relieved'], [6.0, 'happy']]);
    kmbear(st.x, 930, 28, { ...bear, walk: st.walk, view: lt < 2.4 ? 'q' : bear.view, dy: (bear.dy || 0) + st.dy });
    const bk = seg(lt, 4.0, 4.35), kick = seg(lt, 5.05, 5.9);   // 教程从天而降，被 Clawd 踢飞
    if (bk > 0 && kick < 1) {
      const p = kick > 0 ? arcPt([500, 870], [-300, 200], 300, kick) : [500, lerp(-200, 870, easeIn(bk))];
      book(p[0], p[1], kick * -6 + (bk < 1 ? .3 : 0));
    }
    const hop = jump(lt, 4.55, 5.0, 3), cx = lerp(760, 640, ease(seg(lt, 4.55, 5.0)));
    const mood = emotions(lt, [[0, 'happy'], [4.1, 'determined'], [5.1, 'laugh'], [6, 'proud']]);
    clawd(cx, 930, 17, { ...narrator(t, mood), dy: hop.dy, sq: hop.sq, aR: lt < 4 ? 1.1 : mood.aR, aL: kick > 0 && kick < .3 ? 1.3 : mood.aL, flip: kick > 0 && kick < .5 });
    camEnd();
    brand(); captions(t); flushLetters();
    if (lt < .3) brushWipe(.5 + lt / .6, [C.blueDk, C.blue]);
    flash(seg(lt, dur - .3, dur));
  }

  // ---------- C 聚合（14–23） ----------
  function shotFunnel(t, lt, dur) {
    camBegin(960, 560 - 10 * lt, 1.02 - .004 * lt);
    room('#E3EEF8', '#CFDDEA', 980);
    const sites = []; for (let j = 0; j < 8; j++) sites.push([200 + j * 217, 290 + Math.sin(j * 1.3) * 40 + (j % 2) * 30]);
    sites.forEach(([x, y], j) => site(x, y + Math.sin(t * 2 + j) * 6, [C.blue, C.green, C.gold, C.rose, C.violet, C.red][j % 6], j));
    const mouth = [960, 560];
    if (lt > .5) sites.forEach(([x, y], j) => { for (let m = 0; m < 2; m++) {
      const ph = frac((lt - .5) * .55 + j * .137 + m * .5); const p = arcPt([x, y + 40], mouth, 90, ph);
      sheet(p[0], p[1], 14 * (1 - ph * .4), ph * 4 + j, C.card, `fly${j}_${m}`);
    } });
    funnel(960, 560);
    const n = Math.min(6, Math.max(0, (lt - 1.4) * 1.1));
    for (let i = 0; i < 6; i++) card(960, 1010 - i * 16, 300, 64, i, null, clamp(n - i));
    kmbear(1640, 980, 24, { ...emotions(lt, [[0, 'surprised'], [2.6, 'starstruck'], [6.2, 'happy']]), view: 'q', flip: true });
    clawd(1120, 572, 11, { ...narrator(t, { ...move('bounce', t), eyes: 'happy' }) });
    camEnd();
    brand(); captions(t); flushLetters();
    flash(1 - seg(lt, 0, .35));
    if (lt > dur - .3) brushWipe((lt - (dur - .3)) / .6, [C.night, C.navy]);
  }

  // ---------- D 夜晚（23–30） ----------
  function shotNight(t, lt, dur) {
    const dawn = ease(seg(lt, 4.9, 5.9));
    camBegin(960, 560, 1.03);
    room(mixCol(C.night, C.morning, dawn), mixCol('#1A2248', C.floor, dawn));
    boilSeed('window'); paint(rrPts(1300, 170, 380, 330, 16, 1), { wash: mixCol('#101838', '#FFE9B8', dawn), ink: PAL.ink, sw: 1 });
    const mk = seg(lt, 0, 5.2);
    if (dawn < 1) { boilSeed('moon'); glow(lerp(1360, 1640, mk), lerp(300, 230, mk), 90, '#FFF3C8', .7 * (1 - dawn)); paint(ellPts(lerp(1360, 1640, mk), lerp(300, 230, mk), 34, 34, 18), { wash: '#FFF6D8', ink: null }); }
    if (dawn > 0) { boilSeed('sun'); glow(1490, lerp(520, 300, dawn), 200, '#FFC766', dawn); paint(ellPts(1490, lerp(520, 300, dawn), 48, 48, 20), { wash: '#FFD66E', ink: null }); }
    inkLine([[1490, 170], [1490, 500]], .8, PAL.ink, 'ink', 0); inkLine([[1300, 335], [1680, 335]], .8, PAL.ink, 'ink', 0);
    boilSeed('clock'); paint(ellPts(980, 260, 70, 70, 26), { wash: C.card, ink: PAL.ink, sw: 1 });
    const spin = seg(lt, .8, 5.2) * TAU * 6;
    inkLine([[980, 260], [980 + Math.sin(spin) * 52, 260 - Math.cos(spin) * 52]], 1.1, PAL.ink, 'ink', 0);
    inkLine([[980, 260], [980 + Math.sin(spin / 12) * 34, 260 - Math.cos(spin / 12) * 34]], 1.6, PAL.ink, 'ink', 0);
    const bear = emotions(lt, [[0, 'sleepy'], [5.6, 'surprised'], [6.2, 'love']]);
    kmbear(560, 1000, 25, { ...bear, rot: lt < 5.6 ? .16 : bear.rot, lookX: lt > 5.6 ? 1 : 0 });
    desk(760, 790, 640);
    const n = Math.min(3, lt * .6);
    laptop(820, 790, n, lt > 5.8 ? .6 : .25);
    for (let i = 0; i < 4; i++) { const k = seg(lt, .8 + i * 1.1, 1.5 + i * 1.1); if (k > 0 && k < 1) { const p = arcPt([1060, 700], [820, 640], 90, k); card(p[0], p[1], 120, 34, i + 3, null, 1 - k * .3); } }
    clawd(1080, 790, 13, { ...narrator(t, lt < 5.6 ? feel('determined', t) : feel('proud', t)), aR: 1.1, armR: u => lantern(u) });
    camEnd();
    brand(); captions(t); flushLetters();
    if (lt < .3) brushWipe(.5 + lt / .6, [C.night, C.navy]);
    if (lt > dur - .5) iris(560, 700, lerp(1500, 0, ease((lt - (dur - .5)) / .5)));
  }

  // ---------- E 反馈（30–40.5） ----------
  function shotFeedback(t, lt, dur) {
    const zoom = easeIn(seg(lt, dur - .8, dur));
    camBegin(lerp(960, 1600, zoom), lerp(560, 480, zoom), 1 + zoom * 6);
    room('#F4EAD8');
    target(1600, 480, 180);
    const hits = [[1.0, 150, -80], [1.8, -130, 110], [2.6, 60, 150], [6.9, 70, -50], [7.6, -45, 30], [8.3, 18, -14], [8.9, 3, 4]];
    hits.forEach(([t0, dx, dy], i) => arrow(1600 + dx, 480 + dy, seg(lt, t0, t0 + .22), 'ar' + i));
    boilSeed('table'); paint(rectPts(760, 800, 520, 26, 1), { wash: C.desk, ink: PAL.ink, sw: .9 });
    const T0 = [1.2, 2.5, 3.8, 5.2, 5.9], marks = ['yes', 'no', 'maybe', 'yes', 'no'];
    let stampDown = 0;
    T0.forEach((ti, i) => {
      const slide = seg(lt, ti, ti + .45), fly = seg(lt, ti + .9, ti + 1.5); if (slide <= 0 || fly >= 1) return;
      if (fly > 0) { const p = arcPt([930, 760], [1180, 700], 160, fly); plane(p[0], p[1], 26, -.3 + fly * .6, 'pl' + i); return; }
      stampDown = Math.max(stampDown, Math.sin(clamp(seg(lt, ti + .5, ti + .8)) * Math.PI));
      card(lerp(1150, 930, ease(slide)), 760, 250, 70, i, lt > ti + .65 ? marks[i] : null, 1);
    });
    const bear = emotions(lt, [[0, 'determined'], [4.6, 'happy'], [8.4, 'excited']]);
    kmbear(650, 930, 27, { ...bear, view: 'q', aR: lerp(.9, .3, stampDown), armR: u => { boilSeed('stamp'); paint(rrPts(-u * .5, -u * 1.6, u * 1, u * 1.4, u * .3), { wash: C.red, ink: PAL.ink, sw: .6 }); paint(rectPts(-u * .8, -u * .3, u * 1.6, u * .6), { wash: C.deskDk, ink: PAL.ink, sw: .6 }); } });
    const cm = emotions(lt, [[0, 'happy'], [2.0, 'thinking'], [5.0, 'idea'], [7.2, 'cool']]);
    clawd(1230, 930, 16, { ...narrator(t, cm), flip: true });
    camEnd();
    brand(); captions(t); flushLetters();
    if (lt < .5) iris(650, 600, lerp(0, 1500, easeIn(lt / .5)));
    if (lt > dur - .25) flash(seg(lt, dur - .25, dur), C.gold);
  }

  // ---------- F 收益（40.5–51） ----------
  function shotMoney(t, lt, dur) {
    camBegin(960, 560, 1.02);
    room('#FBEFD6', '#E8CFA0');
    const drop = seg(lt, .2, 1.1), cr = lerp(1200, 60, easeOut(seg(lt, 0, .6)));
    const hs = [170, 250, 350, 470];
    hs.forEach((h, i) => bar(560 + i * 260, 930, h, i, seg(lt, 1.3 + i * .9, 2.0 + i * .9)));
    if (lt > 4.7) { boilSeed('trend'); inkLine(hs.map((h, i) => [560 + i * 260, 930 - h - 150]).slice(0, 1 + Math.floor(clamp(seg(lt, 4.7, 5.6)) * 3.99)), 1.4, C.goldDk, 'ink', .3); }
    if (lt < 1.4) coin(960, lerp(560, 890, easeIn(drop)) - 80 * Math.abs(Math.sin(seg(lt, 1.1, 1.4) * Math.PI)), cr, lt * 6, 'bigcoin');
    const party = lt > 5.3;
    [[1500, 18, 1], [1680, 24, 0], [1840, 18, 2]].forEach(([x, u, s]) => {
      const hop = party ? jump(frac((lt - 5.3 + s * .23) / 1.1) * 1.1, .2, .75, 2.5) : { dy: 0, sq: 0 };
      const mood = party ? feel(s === 0 ? 'starstruck' : 'excited', t, { seed: s }) : feel('hopeful', t, { seed: s });
      kmbear(x, 930, u, { ...mood, dy: (mood.dy || 0) + hop.dy, sq: (mood.sq || 0) + hop.sq, flip: true, boilKey: 'mate' + s });
    });
    if (lt > 5.0) for (let i = 0; i < 22; i++) {
      const ph = frac((lt - 5.0) * .45 + hash(i * 4.1)), x = 1300 + hash(i * 2.3) * 620;
      coin(x + Math.sin(ph * 6 + i) * 30, lerp(-60, 900, ph), 18, lt * 5 + i, 'rain' + i);
    }
    clawd(260, 930, 16, { ...narrator(t, emotions(lt, [[0, 'happy'], [5.3, 'love']])), aR: 1.2 });
    camEnd();
    brand(); captions(t);
    if (lt > 5.4) say('收益以实际中标、项目利润及公司提成制度为准', 960, 1040, 28, PAL.ink, t, 45.9, 50.8, { stroke: C.card, ink: false });
    flushLetters();
    if (lt < .3) flash(1 - lt / .3, C.gold);
    if (lt > dur - .3) brushWipe((lt - (dur - .3)) / .6, [C.goldDk, C.gold]);
  }

  // ---------- G 片尾（51–62） ----------
  function shotEnd(t, lt, dur) {
    const pull = ease(seg(lt, 6.6, 7.6));
    camBegin(960, lerp(560, 340, pull), lerp(1.05, .7, pull));
    room(PAL.paper, '#E4D2B0');
    desk(960, 790, 420);
    laptop(960, 790, 1, .4);
    const five = seg(lt, 2.1, 2.4), slap = spring(lt, 2.4, 7, 30), up = jump(lt, 2.0, 2.8, 7);
    const bm = emotions(lt, [[0, 'happy'], [2.4, 'excited'], [3.6, 'happy']]);
    const wave = lt > 3.6 ? move('wave', t) : {};
    kmbear(620, 960, 27, { ...bm, ...(lt < 3.6 ? { aR: lerp(.3, .95, five) } : { aR: wave.aL, aL: .3 }), rot: -.04 * slap });
    const cm = emotions(lt, [[0, 'happy'], [2.4, 'laugh'], [3.6, 'love']]);
    clawd(lerp(1300, 900, ease(seg(lt, .6, 1.9))), 960, 17, { ...narrator(t, cm), ...(lt > 3.6 ? move('wave', t, 1) : { aL: lerp(.5, 1.05, five) }), dy: (cm.dy || 0) + up.dy, sq: (cm.sq || 0) + up.sq, flip: true });
    if (lt > 2.4 && lt < 2.9) { boilSeed('clap'); emote('spark', 790, 420, 34, seg(lt, 2.4, 2.5)); }
    camEnd();
    if (lt > 6.8) {
      image(LOGO, 960, 300, 1100, { screen: true, pop: Math.min(1, (lt - 6.8) * 3) });
      say(URL, 960, 450, 84, C.blueDk, t, 57.8, 70, { stroke: PAL.cream });
    } else brand();
    captions(t); flushLetters();
    if (lt < .3) brushWipe(.5 + lt / .6, [C.goldDk, C.gold]);
    if (lt > dur - .8) iris(960, 700, lerp(1500, 0, ease((lt - (dur - .8)) / .8)));
  }

  shots([[0, shotPile], [7, shotSite], [14, shotFunnel], [23, shotNight], [30, shotFeedback], [40.5, shotMoney], [51, shotEnd]]);
})();
