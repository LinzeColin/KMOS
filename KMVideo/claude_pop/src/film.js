// film.js：一镜到底。全片只有一个镜头 shot，镜头路径 CAMK 在同一个手绘世界里推、拉、甩、钻气泡、升云、落回。
// 时间全部来自 cues.js（EV）。每帧是 t 的纯函数。
(() => {
  const B = { x: 80, y: 500, rb: 232, s: .2 };        // 思想气泡（世界坐标）；气泡里的噩梦按 s 缩放画进去
  const ISLE_T = [EV.isle1, EV.isle2, EV.isle3, EV.isle4, EV.isle5];

  // ---------- 镜头路径：[时刻, [cx, cy, zoom], 进入该关键帧用的缓动] ----------
  const CAMK = [
    [0, [-150, 680, 1.9]],
    [3.6, [-60, 900, 1.0], ease],
    [4.6, [40, 930, 1.0], ease],
    [8.0, [60, 915, 1.04], ease],
    [8.5, [95, 690, 1.3], ease],
    [9.0, [B.x, B.y, 5.1], easeIn],
    [11.55, [B.x, B.y + 8, 5.3], k => k],
    [11.95, [40, 840, 1.0], easeOut],
    [12.6, [40, 640, .95], ease],
    [13.0, [40, 930, 1.0], easeIn],
    [15.75, [40, 1010, 1.13], ease],
    [16.0, [30, 1010, 1.13], k => k],
    [16.4, [20, 960, 1.18], easeOut],
    [16.95, [-100, 830, 1.05], ease],
    [19.6, [-130, 830, 1.08], ease],
    [20.35, [-470, 760, 1.3], ease],
    [21.95, [-440, 740, 1.34], k => k],
    [22.75, [120, 800, 1.0], ease],
    [23.2, [170, 930, 1.3], ease],
    [23.9, [150, 940, 1.35], k => k],
    [24.35, [-360, 1010, 1.7], ease],
    [26.0, [-345, 1000, 1.8], k => k],
    [26.25, [1420, 520, 1.35], ease],
    [26.95, [1470, 470, 1.35], ease],
    [27.3, [1640, 460, 1.2], ease],
    [27.95, [1560, 640, 1.0], ease],
    [28.0, [1590, 700, 1.0], k => k],
    [28.35, [40, 900, 1.0], ease],
    [30.4, [20, 850, 1.1], ease],
    [32.0, [20, 850, 1.1], k => k],
    [33.3, [-1600, -2630, .95], ease],
    [34.5, [-800, -2720, .95], ease],
    [35.5, [0, -2630, .95], ease],
    [36.5, [800, -2720, .95], ease],
    [37.6, [1600, -2630, .95], ease],
    [38.1, [1600, -2630, .95], k => k],
    [39.4, [0, -2580, .34], ease],
    [40.0, [0, -2580, .32], k => k],
    [41.0, [-40, 690, .88], ease],
    [45.2, [-50, 680, .92], ease],
    [46.0, [-55, 676, .93], k => k],
  ];
  function camAt(t) {
    let i = 1; while (i < CAMK.length - 1 && t > CAMK[i][0]) i++;
    const [t0, a] = CAMK[i - 1], [t1, b, e] = CAMK[i], k = (e || ease)(seg(t, t0, t1));
    let cx = lerp(a[0], b[0], k), cy = lerp(a[1], b[1], k), z = Math.exp(lerp(Math.log(a[2]), Math.log(b[2]), k)), rot = 0;
    // 甩镜：轻微旋转
    for (const [w0, w1, r] of [[26.0, 26.25, .07], [28.0, 28.35, -.06], [32.0, 33.3, .05], [40.0, 41.0, -.05]]) if (t > w0 && t < w1) rot += r * Math.sin(Math.PI * seg(t, w0, w1));
    // 冲击震屏
    for (const [t0, amp, d] of [[EV.crateLand, 16, .45], [EV.drop, 10, .35], [EV.chomp, 12, .4], [EV.card, 9, .35], [EV.clunk1, 4, .2], [EV.clunk2, 4, .2], [EV.clunk3, 4, .2], [EV.nclunk1, 5, .2], [EV.nclunk2, 5, .2], [EV.nclunk3, 9, .3], [EV.lastClunk, 6, .25]]) {
      const a2 = t - t0; if (a2 >= 0 && a2 < d) { const [sx, sy] = shakeXY(t, amp * (1 - a2 / d)); cx += sx / z; cy += sy / z; }
    }
    return { cx, cy, z, rot };
  }

  // ---------- 窑宝的状态 ----------
  const OMEGA = TAU / 2;                        // 轮带 2 秒一圈
  const rotAt = t => t * OMEGA;
  const CUT0 = EV.cutStart, TH0 = rotAt(CUT0);
  // 材料角 φ 是否已被左侧（屏幕角 π）的刀车过
  const repAt = t => phi => { if (t < CUT0) return 0; const need = (((Math.PI - phi - TH0) % TAU) + TAU) % TAU; return clamp((rotAt(t) - TH0 - need) / .35 + 1); };
  const CLUNKS = [[EV.clunk1, 22], [EV.clunk2, 22], [EV.clunk3, 22], [EV.nclunk1, 24], [EV.nclunk2, 24], [EV.nclunk3, 44]];
  function kilnState(t) {
    const dy = CLUNKS.reduce((s, [t0, a]) => s + kick(t, t0, a), 0) + (t > EV.lastClunk ? kick(t, EV.lastClunk, 7) : 0);
    const fixed = seg(t, CUT0, CUT0 + 2.1);
    const sinceClunk = Math.min(...CLUNKS.map(([t0]) => t - t0 >= 0 ? t - t0 : 99));
    const f = { tint: 1 - fixed, gloom: t < 16 ? 1 : 1 - fixed, eyes: 'normal', lid: .45, bags: t < 22, mouth: 'wobble', look: 0, lookY: 0 };
    if (sinceClunk < .3) { f.eyes = 'squeeze'; f.sweat = 1 - sinceClunk / .3; }
    if (t > 8 && t < 12) { f.look = .6; f.lookY = -.4; }
    if (t > 12 && t < 13.2) { f.lookY = -1; f.lid = .1; f.eyes = 'wide'; }
    if (t > 13.2 && t < 16) { f.look = .9; f.lookY = .6; f.lid = .2; }
    if (t > 16 && t < 18) { f.lookY = -1; f.lid = 0; f.eyes = 'wide'; f.mouth = 'O'; }
    if (t > 18.1 && t < 19.2) { f.eyes = 'swirl'; }
    if (t > 19.2 && t < 20.5) { f.look = -1; f.lid = .1; }
    if (t > 20.5 && t < 22.6) { f.eyes = 'happy'; f.blush = .8; f.mouth = 'smile'; }
    if (t > 22.6) { f.eyes = 'normal'; f.lid = 0; f.mouth = 'smile'; f.blush = .4; f.look = .5; }
    if (t > 28.35 && t < EV.burp) { f.eyes = 'closed'; f.mouth = 'flat'; f.blush = .2; }
    if (t >= EV.burp && t < EV.burp + .5) { f.eyes = 'happy'; f.mouth = 'O'; f.burp = Math.sin(Math.PI * seg(t, EV.burp, EV.burp + .5)); f.blush = 1; }
    if (t >= EV.burp + .5) { f.eyes = 'happy'; f.mouth = 'grin'; f.blush = .8; }
    if (t > 40) { f.eyes = t > 44.2 ? 'happy' : 'normal'; f.lid = 0; f.lookY = t < 44 ? -.8 : 0; f.mouth = 'grin'; }
    const rr = 1 - seg(t, 24.4, 25.9);
    return { dy, rot: rotAt(t), rep: repAt(t), sick: 1 - fixed, glowPits: t < 22.5 ? (1 - fixed) : 0, face: f, rust: rr,
      rollShine: [1 - rr, 1 - rr], shine: t > CUT0 ? fixed : 0, reflect: t > EV.mirror && t < 24.1 ? backOut(seg(t, EV.mirror, EV.mirror + .25)) : 0 };
  }

  // ---------- 厂长的状态 ----------
  function noodleArc(t, t0, h) { const a = t - t0; return a > 0 && a < .45 ? -h * 4 * (a / .45) * (1 - a / .45) : 0; }
  function mgrState(t) {
    const st = { bowl: true, face: { eyes: 'happy', mouth: 'chew', look: -1 }, hL: [-150, -175], hR: [120, -210], chop: -.6 + .25 * Math.sin(t * 6) };
    const tk = [EV.clunk1, EV.clunk2, EV.clunk3, EV.nclunk1, EV.nclunk2, EV.nclunk3, EV.crateLand, EV.drop, EV.chipLand, EV.burp, EV.lastClunk]
      .reduce((s, t0) => { const q = take(t, t0, t0 === EV.nclunk3 || t0 === EV.crateLand ? 1.4 : .8); return { sq: s.sq + q.sq, dy: s.dy + q.dy }; }, { sq: 0, dy: 0 });
    st.sq = tk.sq; st.dy = tk.dy * 40;
    const hand = st.hR; if (t < 8) { const bite = Math.max(0, Math.sin(t * Math.PI)); st.hR = [120 - 90 * bite, -210 - 80 * bite]; }
    // 咯噔时面条从碗里跳起
    st.bowlNoodles = !(t > EV.nclunk3 && t < 40);
    if ([EV.nclunk1, EV.nclunk2].some(t0 => t > t0 && t < t0 + .35) || (t > EV.nclunk3 && t < EV.nclunk3 + .35)) { st.face = { eyes: 'wide', mouth: 'O', look: -1, lookY: -.5, brow: 1 }; }
    if (t > EV.nclunk3 + .2 && t < EV.noodleHat) st.face = { eyes: 'wide', mouth: 'O', lookY: -1, brow: 1 };
    st.noodleHat = t > EV.noodleHat && t < EV.crateLand ? backOut(seg(t, EV.noodleHat, EV.noodleHat + .2)) : 0;
    if (t > EV.noodleHat) st.hR = [110, -190];
    if (t > EV.noodleHat + .1 && t < 8) st.face = { eyes: 'half', mouth: 'flat', look: 1 };
    if (t > 8 && t < 11.6) { st.face = { eyes: 'wide', mouth: 'wobble', lookY: -1, sweat: 1, brow: 1 }; st.lean = .04 * Math.sin(t * 20); }
    if (t > 11.6 && t < 12.3) { st.face = { eyes: 'cry', mouth: 'wail', tears: seg(t, 11.6, 11.9) }; st.bowl = true; }
    if (t > 12.3 && t < 13) st.face = { eyes: 'wide', mouth: 'O', lookY: -1, look: -.3, tears: 1 - seg(t, 12.3, 12.6), brow: 1 };
    if (t > 13 && t < 13.4) st.face = { eyes: 'wide', mouth: 'wail', look: -1, brow: 1 };
    if (t > 13.4 && t < 16) { st.face = { eyes: 'dot', mouth: 'O', look: -1, lookY: .4, sweat: t > EV.peek ? 1 : 0 }; st.lean = -.1 * ease(seg(t, 13.4, 14.5)) + (t > EV.peek ? .08 : 0); }
    if (t > 16 && t < 17) st.face = { eyes: 'star', mouth: 'grin', look: -1, lookY: -.5, blush: .6 };
    if (t > 17 && t < 20.4) st.face = { eyes: 'dot', mouth: 'smile', look: -1, lookY: -1 };
    if (t > 20.4 && t < EV.chipLand) st.face = { eyes: 'wide', mouth: 'O', look: -1, lookY: -.6, brow: 1 };
    st.curl = t > EV.chipLand ? backOut(seg(t, EV.chipLand, EV.chipLand + .2)) : 0;
    st.curlWob = spring(t, EV.chipLand, 4, 16) + spring(t, EV.burp, 2.5, 14) * 2 + spring(t, EV.lastClunk, 4, 16) + .15 * Math.sin(t * 3);
    if (t > EV.chipLand && t < EV.mirror) st.face = { eyes: 'wide', mouth: 'O', lookY: -1, brow: 1 };
    if (t > EV.mirror && t < 24.2) { st.face = { eyes: 'heart', mouth: 'grin', look: -1, blush: 1 }; st.lean = -.16 * ease(seg(t, EV.mirror, EV.mirror + .3)); st.hR = [40, -430]; }
    if (t > 28.35 && t < EV.listen) st.face = { eyes: 'wide', mouth: 'puff', look: -1, lookY: -1, blush: .5 };
    if (t > EV.listen && t < EV.burp) { st.face = { eyes: 'closed', mouth: 'puff', look: -1 }; st.lean = -.28 * ease(seg(t, EV.listen, EV.listen + .4)); }
    if (t > EV.burp && t < EV.burp + .5) { st.face = { eyes: 'wide', mouth: 'O', look: -1, brow: 1 }; st.lean = .14 * Math.exp(-(t - EV.burp) * 3); }
    if (t > EV.burp + .5 && t < 32.5) { st.face = { eyes: 'happy', mouth: 'grin', look: -1, blush: .8 }; }
    if (t > 31.5 && t < 32.3) st.hL = [-150, lerp(-175, -370, ease(seg(t, 31.45, 31.75)))];
    if (t > 40) { st.face = { eyes: 'happy', mouth: 'chew', look: -1 }; st.bowlNoodles = true; }
    if (t > EV.lastClunk && t < EV.lastClunk + .45) st.face = { eyes: 'wide', mouth: 'O', look: -1, lookY: -1, brow: 1 };
    if (t > EV.lastClunk + .45 && t < 45) st.face = { eyes: 'half', mouth: 'flat', look: -1, lookY: -1 };
    if (t > 45) st.face = { eyes: 'happy', mouth: 'grin', look: -1, blush: .6 };
    return st;
  }

  // ---------- Clawd 的位置与状态 ----------
  const CL_EMO = [[0, 'excited'], [16.9, 'determined'], [18.1, 'dizzy'], [EV.idea, 'idea'], [20.45, 'determined'], [EV.shades, 'cool'], [24.3, 'determined'],
    [26.8, 'proud'], [27.1, 'scared'], [27.85, 'relieved'], [28.4, 'nervous'], [EV.burp, 'surprised'], [31.0, 'laugh'], [40.2, 'excited'], [41.2, 'happy'], [43.3, 'mischief'], [44.3, 'playful']];
  const TOOL = { x: KILN.x - KILN.R, y: KILN.y };           // 刀尖
  const SEAT = [TOOL.x - 205, TOOL.y - 30];                  // 刀座顶面
  const TYRE_TOP = t => [KILN.x, KILN.y - KILN.R + kilnState(t).dy];
  const ROLL_TOP = [ROLL[0][0], ROLL[0][1] - KILN.rr];
  const GROT0 = -2.27;                                       // 26.3s 时缺齿在 10 点半方向
  const gearRot = t => { const w = (1.22) / 1.0; return GROT0 - (GEAR_MISS + .34) * TAU / GEAR.n + w * (t - EV.weld); };
  function rimPoint(t, back = .16) { const a = toothAngle(gearRot(t)) - back, r = GEAR.R + GEAR.th; return { p: [GEAR.x + Math.cos(a) * r, GEAR.y + Math.sin(a) * r], rot: a + Math.PI / 2 }; }

  function clawdPlan(t) {
    const top = [CRATE.x, CRATE.y - 210];
    let p = top, u = 19, o = {}, vis = t >= EV.drop && !(t > 32.6 && t < 40);
    if (t < 16.4) { const k = backOut(seg(t, EV.drop, EV.drop + .22)); p = [top[0], top[1] + (1 - k) * 140 - 40 * Math.sin(Math.PI * seg(t, 16.05, 16.4))]; u = 24; o = { aL: 1.4, aR: 1.3, emote: 'stars', emoteK: k, emoteAge: t - 16 }; }
    else if (t < 16.9) { const k = seg(t, 16.4, 16.9); p = arcPt(top, TYRE_TOP(t), 200, easeOut(k * 1.0)); u = lerp(24, 19, k); o = { view: 'q', flip: true, sq: -.15 * Math.sin(Math.PI * k) }; }
    else if (t < 19.9) { p = TYRE_TOP(t); o = { view: 'side', flip: true, walk: t * 9, dy: -Math.abs(Math.sin(t * 9 * Math.PI)) * .25, aL: -.9, aR: .3 }; }
    else if (t < 20.45) { const k = seg(t, 19.9, 20.45); p = arcPt(TYRE_TOP(t), SEAT, 220, ease(k)); u = lerp(19, 16, k); o = { view: 'q', flip: true, sq: -.12 * Math.sin(Math.PI * k) }; }
    else if (t < 24.0) { p = SEAT; u = 16; o = { view: 'q', aR: .4 + .5 * Math.sin(t * 12), aL: -.3 }; }
    else if (t < 24.35) { const k = seg(t, 24.0, 24.35); p = arcPt(SEAT, ROLL_TOP, 160, ease(k)); u = 16; o = { view: 'q' }; }
    else if (t < 26.0) { p = ROLL_TOP; u = 16; o = { view: 'side', walk: t * 8, dy: -Math.abs(Math.sin(t * 8 * Math.PI)) * .2, aR: -.4 }; }
    else if (t < 26.25) { const k = ease(seg(t, 26.0, 26.25)), rp = rimPoint(26.25); p = [lerp(ROLL_TOP[0], rp.p[0], k), lerp(ROLL_TOP[1], rp.p[1], k)]; u = 16; o = { smear: 1, smearDir: 1, view: 'side' }; }
    else if (t < 27.25) { const rp = rimPoint(t); p = rp.p; u = 16; o = { rot: rp.rot, view: t < 26.8 ? 'q' : 'front', aR: t < 26.8 ? -.2 : 1.1, aL: t > 26.8 ? 1.1 : 0 }; }
    else if (t < 27.8) { const k = seg(t, 27.25, 27.8), rp = rimPoint(27.25); p = arcPt(rp.p, [GEAR.x - 400, GROUND - 170], 260, easeOut(k)); u = 16; o = { rot: lerp(rp.rot, 0, k), aL: 1.4, aR: 1.4 }; }
    else if (t < 28.0) { p = [GEAR.x - 400, GROUND - 170]; u = 16; }
    else if (t < 28.35) { const k = ease(seg(t, 28.0, 28.35)); p = [lerp(GEAR.x - 400, top[0], k), lerp(GROUND - 170, top[1], k)]; u = lerp(16, 19, k); o = { smear: 1, smearDir: -1, view: 'side', flip: true }; }
    else if (t < 32.6) { p = top; o = { view: 'q', lookX: -.6, lookY: -.6 }; }
    else if (t < 41.0) { const k = easeIn(seg(t, 40.1, 41.0)), tt = TYRE_TOP(t); p = [tt[0], lerp(-700, tt[1], k)]; o = { aL: 1.4, aR: 1.4, sq: -.2 * (1 - k) }; vis = t > 40.1; }
    else { p = TYRE_TOP(t); o = t < 44.2 ? { view: 'side', flip: true, walk: t * 6, dy: -Math.abs(Math.sin(t * 6 * Math.PI)) * .2 } : { view: 'front' }; }
    return { p, u, o, vis };
  }
  function clawdMain(t, ks) {
    const P = clawdPlan(t); if (!P.vis) return null;
    const emo = emotions(t, CL_EMO, { take: .8 });
    let extra = { ...P.o };
    // 跳跃/落地
    let j = { dy: 0, sq: 0 };
    if (t > 31.4 && t < 32.4) j = jump(t, 31.55, 32.05, 6.5);
    if (t > 43.3 && t < 44.5) j = jump(t, 43.6, 44.0, 5);
    if (t > 40.9 && t < 41.5) j = { dy: 0, sq: .28 * Math.exp(-(t - 41) * 8) * Math.cos((t - 41) * 22) };
    const hatOff = t > EV.chomp && t < 27.9 ? 1 : 0;
    const o = { ...emo, ...extra, hat: hatOff ? null : 'hard', boilKey: 'clawd main' };
    o.dy = (emo.dy || 0) + (extra.dy || 0) + j.dy; o.sq = (emo.sq || 0) + (extra.sq || 0) + j.sq;
    if (t > 31.5 && t < 32.2) { o.aR = 1.1; o.view = 'q'; }
    if (t > 23.5 && t < 24.0) o.eyes = 'shades';
    if (t > 44.6) o.view = 'front';
    if (t > EV.wink - .05) { o.eyes = t < EV.wink + .45 ? ['normal', 'wink'] : 'happy'; o.mouth = 'grin'; }
    // 手里的东西
    if (t > 17.9 && t < 19.9) o.armL = (u, sw) => { paint(circPts(u * .8, 0, u * .9, 14), { wash: CREAM, ink: INK, sw: sw * .7 }); const a = needle(t) - Math.PI / 2; inkLine([[u * .8, 0], [u * .8 + Math.cos(a) * u * .7, Math.sin(a) * u * .7]], sw * .8, '#D8433A', 'inkfine', 0); };
    if (t > 24.35 && t < 26.0) o.armR = (u, sw) => { paint(rectPts(0, -u * .35, u * 1.4, u * .7, 1), { wash: '#E0873C', ink: INK, sw: sw * .7 }); paint(circPts(u * 1.6, u * .5, u * .8, 12), { wash: STEEL_LT, ink: INK, sw: sw * .6 }); };
    if (t > 26.25 && t < 26.85) o.armR = (u, sw) => { paint(rectPts(0, -u * .25, u * 1.6, u * .5, 1), { wash: STEEL_DK, ink: INK, sw: sw * .6 }); };
    if (t > 26.25 && t < 27.25) o.lookX = .8;
    if (t > 27.05 && t < 27.3) { o.lookX = 1; o.eyes = 'wide'; }
    clawd(P.p[0], P.p[1], P.u, o);
    // 帽子被咬飞、又落回来
    if (hatOff) { const k = seg(t, EV.chomp, 27.9), hp = arcPt(rimPoint(EV.chomp).p, [P.p[0], P.p[1] - 8 * P.u], 300, k); push(); translate(hp[0], hp[1]); rotate(k * 9); hat(P.u, 'hard', 1); pop(); }
    return P;
  }

  // ---------- 百分表指针 ----------
  function needle(t) {
    const wild = 1.5 * Math.sin(t * 7.3) + .8 * Math.sin(t * 19.1 + 1) + CLUNKS.reduce((s, [t0, a]) => s + kick(t, t0, a / 14), 0);
    const cut = t < CUT0 ? 1 : 1 - seg(t, CUT0, CUT0 + 2.1);
    if (t < 28.4) return wild * Math.max(cut, .12) + (t > 18 && t < 19 ? .6 * Math.sin(t * 30) : 0);
    const s = .5 * Math.exp(-(t - 28.4) * 3.2) * Math.cos((t - 28.4) * 11);
    return t < EV.zero ? s : s * Math.exp(-(t - EV.zero) * 6);
  }
  function dialPlace(t) {
    // 左上角常驻；28.4 挪到画面中央放大看归零；32 升空时退场，40.5 回来
    const corner = [175, 300, 105];
    const c = [540, 700, 260], k = ease(seg(t, 28.35, 28.8)) * (1 - ease(seg(t, 29.9, 30.35)));
    const show = popK(t, 1.0) * (1 - ease(seg(t, 32.0, 32.4))) + (t > 41.6 ? 0 : 0);
    return { x: lerp(corner[0], c[0], k), y: lerp(corner[1], c[1], k), r: lerp(corner[2], c[2], k), k: show };
  }

  // ---------- 主镜头 ----------
  function film(t) {
    const C = camAt(t), ks = kilnState(t), inBubble = t > 9.02 && t < 11.52, sky = t > 32.9 && t < 40.1;
    const stageVis = !inBubble && !sky, gearVis = C.cx > 700, rollerClose = t > 24.3 && t < 26.05;
    // 天空底板（屏幕坐标，轻微视差）
    const px = -C.cx * .04, py = -(C.cy - 900) * .02;
    const gold = t > 16 && t < 32.9 ? ease(seg(t, 16.0, 16.5)) : t > 40 ? 1 : 0;
    const blue = clamp(seg(-C.cy, 200, 1600));
    if (!inBubble) {
      plate('gray', 1, px, clamp(py, -60, 60));
      plate('gold', gold, px, clamp(py, -60, 60));
      plate('blue', blue, 0, 0);
    }
    // 远景工厂（视差层）
    if (stageVis && C.cy > -600) {
      camBegin(C.cx * .6, 960 + (C.cy - 960) * .6, Math.pow(C.z, .75), C.rot);
      plant(t, gold);
      camEnd();
    }
    camBegin(C.cx, C.cy, C.z, C.rot);
    if (stageVis) {
      floorLayer();
      if (gearVis) {
        const g = gearStation(t, { rot: gearRot(t), grow: t < EV.weld ? 0 : ease(seg(t, EV.weld, EV.weld + .5)), weld: t > EV.weld && t < 26.85 ? .8 + .2 * Math.sin(t * 60) : 0, hint: t < EV.weld + .1 ? popK(t, 26.15) : 0, hot: 1 - seg(t, 26.8, 27.3) });
        if (t > EV.weld && t < 26.85) { const a = toothAngle(gearRot(t)); sparks(GEAR.x + Math.cos(a) * (GEAR.R + 20), GEAR.y + Math.sin(a) * (GEAR.R + 20), t, EV.weld, 26.85, { rate: 50, dir: -2.2, spread: 1.6, speed: 500, col: '#9FD8FF', key: 'weld' }); }
        if (t > EV.chomp - .02 && t < EV.chomp + .25) glow(g.pinion[0] - 90, g.pinion[1] + 60, 160, '#FFE08A', 1 - seg(t, EV.chomp, EV.chomp + .25));
        const [sx, sy] = toScreen(g.pinion[0] - 60, g.pinion[1] - 150); boom('嗷呜!!', sx, sy, 150, '#E2476E', t, EV.chomp, { life: .7, rot: .12 });
      }
      if (C.cx < 900) {
        kiln(t, ks);
        if (t > 19.95) {
          const k = easeOut(seg(t, 19.95, 20.45));
          toolPost(t, TOOL.x - (1 - k) * 700, TOOL.y, { cut: t > CUT0 && t < CUT0 + 2.1 ? 1 : 0, crank: t * 6 });
        }
        if (t > CUT0 && t < CUT0 + 2.1) {
          sparks(TOOL.x, TOOL.y - 6, t, CUT0, CUT0 + 2.1, { rate: 55, dir: -2.4, spread: 1.1, speed: 820, key: 'cut' });
          glow(TOOL.x, TOOL.y, 70 + 30 * pulse(t, 8), '#FFB65C', .9);
          for (const b of [20.5, 21.0, 21.5, 22.0]) { const [sx, sy] = toScreen(TOOL.x - 60, TOOL.y - 170); boom('滋——', sx, sy, 72, HARD, t, b, { life: .42, rot: -.18 }); }
        }
        drawChip(t);
        if (rollerClose && t > 24.35) { sparks(ROLL_TOP[0] + 60, ROLL_TOP[1] + 10, t, 24.35, 26.0, { rate: 45, dir: -.6, spread: 1.2, speed: 620, key: 'grind' }); glow(ROLL_TOP[0] + 60, ROLL_TOP[1] + 10, 50, '#FFB65C', .8); }
        if (t > 11.9) crateDraw(t);
        if (!rollerClose) manager(t, MGR.x, MGR.y, mgrState(t));
        drawFlyingNoodles(t);
        if (t > EV.burp) heartRing(t);
      }
      const cp = clawdMain(t, ks);
      if (t > EV.drop && t < EV.drop + 1.6) confetti(CRATE.x, CRATE.y - 230, t, EV.drop, 28, { speed: 1100 });
      if (t > EV.hi5 - .02 && t < EV.hi5 + .3) { const [sx, sy] = toScreen(100, 880); boom('啪!', sx, sy, 110, HARD, t, EV.hi5, { life: .5 }); glow(100, 950, 120, '#FFE08A', 1 - seg(t, EV.hi5, EV.hi5 + .3)); }
      worldBooms(t, ks);
      if (t > 7.9 && t < 12.1) bubble(t);
    }
    if (inBubble) bubble(t);
    // 云（升空 / 落回时穿过）
    if (C.cy < 400) for (let i = 0; i < 14; i++) cloud(-900 + hash(i) * 1800 + (i % 2 ? 80 : -80), -700 - i * 95 - hash(i + 3) * 60, 1.6 + hash(i + 7), 'transit' + i, '#FFF8EE', 245);
    if (sky || (C.cy < -1400)) skyIsles(t);
    camEnd();

    // ---------- 屏幕层 ----------
    const D = dialPlace(t);
    if (D.k > .01) dialUI(t, D.x, D.y, D.r, needle(t), D.k);
    if (t > EV.zero - .05 && t < 30.3) boom('0.00', 540, 1010, 110, '#6E9F58', t, EV.zero, { life: 1.3, rot: 0, font: 'Fredoka' });
    speedLines(t);
    if (t > EV.drop && t < EV.drop + .2) flash(1 - seg(t, EV.drop, EV.drop + .2));
    if (t > EV.card && t < EV.card + .12) flash(.7 * (1 - seg(t, EV.card, EV.card + .12)));
    counter(t);
    endCard(t);
    captions(t);
    // 开场：纸面圆形打开；收尾：圆形收到 Clawd 脸上
    if (t < .7) { flushLetters(); iris(540, 700, lerp(0, 1300, easeIn(seg(t, 0, .7)))); }
    if (t > EV.irisClose) {
      flushLetters();
      const P = clawdPlan(t), C2 = camAt(t), [sx, sy] = toScreen(P.p[0], P.p[1] - 5 * P.u, { cx: C2.cx, cy: C2.cy, zoom: C2.z, rot: C2.rot });
      iris(sx, sy, lerp(1300, 0, ease(seg(t, EV.irisClose, 45.95))) + (t > 45.5 ? 0 : 0));
    }
  }

  // ---------- 零件 ----------
  function crateDraw(t) {
    let y = CRATE.y, sq = 0, dx = 0, rot = 0, peek = 0, lid = 0;
    if (t < EV.crateLand) { y = lerp(-900, CRATE.y, easeIn(seg(t, EV.fallStart, EV.crateLand))); sq = -.12; }
    else sq = .3 * Math.exp(-(t - EV.crateLand) * 9) * Math.cos((t - EV.crateLand) * 26);
    // 落地前的影子
    if (t < EV.crateLand) { boilSeed('crate shadow'); const k = seg(t, EV.fallStart, EV.crateLand); paint(ellPts(CRATE.x, CRATE.y + 6, 60 + 110 * k, 10 + 14 * k, 18), { wash: INK, washOp: 60 + 80 * k, ink: null }); }
    if (t > EV.rollStart && t < EV.gap) { const k = seg(t, EV.rollStart, 15.6), f = 8 + k * 30; dx = Math.sin(t * f * 2) * (2 + 10 * k); rot = Math.sin(t * f * 1.7) * .03 * k; y -= Math.abs(Math.sin(t * f)) * 16 * k; }
    if (t > EV.peek) peek = ease(seg(t, EV.peek, EV.peek + .3));
    if (t > EV.drop) lid = 1;
    crate(t, CRATE.x, y, { sq, dx, rot, peek: t > EV.drop ? 0 : peek, lid });
    // 盖子炸飞
    if (t > EV.drop && t < EV.drop + 1.2) { const k = seg(t, EV.drop, EV.drop + 1.2), lp = arcPt([CRATE.x, CRATE.y - 230], [CRATE.x + 900, CRATE.y - 300], 900, k); push(); translate(lp[0], lp[1]); rotate(k * 12); boilSeed('lid fly'); paint(rectPts(-140, -13, 280, 26, 1.5), { wash: '#B8773F', ink: INK, sw: .9 }); pop(); }
    // 砸地尘土
    if (t > EV.crateLand && t < EV.crateLand + .8) for (let i = 0; i < 8; i++) { const a = t - EV.crateLand, s = (i % 2 ? 1 : -1), x = CRATE.x + s * (140 + a * 400 * (.6 + hash(i) * .6)); boilSeed('dust' + i); paint(ellPts(x, CRATE.y - 20 - a * 90 * hash(i + 3), 40 + a * 70, 26 + a * 40, 12, 3), { wash: '#E9DCC6', washOp: 230 * (1 - a / .8), ink: null }); }
  }
  // 面条：碗里跳 → 飞天扣在帽子上 → 箱子砸地时滑落
  function drawFlyingNoodles(t) {
    const bowl = [MGR.x - 150, MGR.y - 205];
    const hops = [[EV.nclunk1, 110], [EV.nclunk2, 130]];
    for (const [t0, h] of hops) if (t > t0 && t < t0 + .45) noodleBunch(bowl[0], bowl[1] + noodleArc(t, t0, h), (t - t0) * 4, 'hop' + t0);
    if (t > EV.nclunk3 && t < EV.noodleHat) { const k = seg(t, EV.nclunk3, EV.noodleHat), p = arcPt(bowl, [MGR.x, MGR.y - 430], 520, k); noodleBunch(p[0], p[1], k * 9, 'fly'); }
    if (t > EV.crateLand && t < EV.crateLand + .7) { const k = seg(t, EV.crateLand, EV.crateLand + .7), p = arcPt([MGR.x, MGR.y - 430], [MGR.x + 160, MGR.y + 10], 160, k); noodleBunch(p[0], p[1], k * 5, 'fall'); }
    if (t > 44.0 && t < 44.45) noodleBunch(bowl[0], bowl[1] + noodleArc(t, 44.0, 90), (t - 44) * 4, 'last');
  }
  function noodleBunch(x, y, r, key) {
    boilSeed('nb' + key);
    for (let i = 0; i < 6; i++) { const P = []; for (let j = 0; j < 5; j++) { const q = rotP([(i - 2.5) * 12 + Math.sin(j * 2 + i) * 10, (j - 2) * 22], r); P.push([x + q[0], y + q[1]]); } inkLine(P, 2.6, '#E8C35A', 'ink', .6); }
    paint(ellPts(x, y - 10, 22, 12, 8), { wash: '#9B6A3A', washOp: 220, ink: null });
  }
  // 螺旋车屑：从刀尖长出 → 断开 → 飞过窑顶 → 落到厂长安全帽上
  function drawChip(t) {
    if (t < 21.0 || t > EV.chipLand) return;
    boilSeed('chip');
    const hatTop = [MGR.x, MGR.y - 430];
    let base, len, rot = 0;
    if (t < EV.chipSnap) { base = [TOOL.x - 10, TOOL.y - 20]; len = seg(t, 21.0, EV.chipSnap); rot = -.4; }
    else { const k = seg(t, EV.chipSnap, EV.chipLand); base = arcPt([TOOL.x - 10, TOOL.y - 160], hatTop, 700, easeOut(k * .98)); len = 1; rot = -.4 + k * 8; }
    const P = []; for (let k = 0; k <= 44; k++) { const u2 = k / 44, a = u2 * TAU * 5, h = u2 * 240 * len; const q = rotP([Math.cos(a) * 28, -h + Math.sin(a) * 9], rot); P.push([base[0] + q[0], base[1] + q[1]]); }
    inkLine(P, 3.4, '#9AA6BC', 'ink', .4);
    inkLine(P.map(([a2, b2]) => [a2 + 3, b2 - 3]), 1.4, '#FFFFFF', 'inkfine', .4);
    glow(P[P.length - 1][0], P[P.length - 1][1], 30, '#FFD27A', .6);
  }
  // 窑宝打嗝：心形烟圈飘出来
  function heartRing(t) {
    const a = t - EV.burp; if (a > 2.2) return;
    const x = KILN.x + a * 140, y = KILN.y + 60 - a * 330, s = 30 + a * 60;
    boilSeed('heart ring');
    paint(heartPts(x, y, s), { wash: '#F4E9F0', washOp: 230 * (1 - a / 2.2), ink: '#B98AA0', sw: .8 });
    paint(heartPts(x, y + s * .1, s * .55), { wash: '#FFFFFF', washOp: 200 * (1 - a / 2.2), ink: null });
  }
  function bubble(t) {
    const grow = backOut(seg(t, EV.bubble, EV.bubble + .3)), popk = seg(t, EV.bubblePop, EV.bubblePop + .25);
    if (grow <= 0 || popk >= 1) return;
    // 头顶冒出的三个小泡
    const head = [MGR.x - 10, MGR.y - 460];
    boilSeed('bubble dots');
    [[0, 0, 14], [-50, -70, 22], [-100, -150, 32]].forEach(([dx, dy, r], i) => { if (grow > i * .25) paint(circPts(head[0] + dx, head[1] + dy, r * (1 - popk), 12), { wash: '#FFF8EE', ink: INK, sw: .7 }); });
    const rb = B.rb * grow * (1 + popk * .4);
    boilSeed('bubble');
    const edge = circPts(B.x, B.y, rb, 40, (a, i) => rb * (1 + .05 * Math.sin(i * 2.4 * Math.PI)));
    paint(edge, { wash: '#4B3A78', washOp: 255 * (1 - popk), ink: '#FFF8EE', sw: 1.2 * (1 - popk) });
    if (popk > 0) { for (let i = 0; i < 10; i++) { const a = i / 10 * TAU, r = rb * (1 + popk * .6); boilSeed('drop' + i); paint(circPts(B.x + Math.cos(a) * r, B.y + Math.sin(a) * r, 10 * (1 - popk), 8), { wash: '#FFF8EE', ink: null }); } const [sx, sy] = toScreen(B.x, B.y); boom('啵!', sx, sy, 110, CREAM, t, EV.bubblePop, { life: .45 }); return; }
    if (grow < .6) return;
    // 气泡里：噩梦底板 + 噩梦
    const img = PLATE.nightMask;
    if (img) { flushBrush(); push(); image(img, B.x - 540 * B.s, B.y - 540 * B.s, 1080 * B.s, 1080 * B.s); pop(); }
    push(); translate(B.x, B.y); scale(B.s); NM.x = B.x; NM.y = B.y; NM.s = B.s;
    nightmare(t);
    pop();
    const [sx, sy] = toScreen(B.x + 200 * B.s, B.y + 250 * B.s);
    boom('啪叽!', sx, sy, 170, HARD, t, EV.squash, { life: .7, rot: .1 });
  }
  function worldBooms(t, ks) {
    const at = (x, y) => toScreen(x, y);
    [[EV.clunk1, -.12, 300, 1240], [EV.clunk2, .1, 780, 1180], [EV.clunk3, -.06, 540, 1300]].forEach(([t0, r, sx, sy]) => boom('咯噔!', sx, sy, 96, HARD, t, t0, { rot: r, life: .6 }));   // 屏幕坐标：开场镜头推得很近，世界坐标会落进字幕下方
    [[EV.nclunk1, -.1, 90], [EV.nclunk2, .12, 100], [EV.nclunk3, -.08, 140]].forEach(([t0, r, s], i) => { const [sx, sy] = at(KILN.x + 170 + i * 40, 330 - i * 20); boom(i === 2 ? '咯噔!!' : '咯噔!', sx, sy, s, HARD, t, t0, { rot: r, life: .6 }); });
    { const [sx, sy] = at(MGR.x, MGR.y - 520); boom('啪', sx, sy, 70, CREAM, t, EV.noodleHat, { life: .45 }); }
    { const [sx, sy] = at(CRATE.x, CRATE.y - 380); boom('咚!!', sx, sy, 180, HARD, t, EV.crateLand, { life: .7 }); }
    boom('开明高新 到!', 560, 560, 124, HARD, t, EV.drop, { life: 1.2, rot: -.06, grow: .05 });
    { const [sx, sy] = at(MGR.x - 40, MGR.y - 560); boom('叮!', sx, sy, 76, CREAM, t, EV.chipLand, { life: .5 }); }
    { const [sx, sy] = at(ROLL_TOP[0], ROLL_TOP[1] - 250); boom('滋滋滋', sx, sy, 90, HARD, t, 24.4, { life: 1.4, rot: -.1 }); }
    { const [sx, sy] = at(KILN.x + 230, KILN.y - 250); boom('嗝~', sx, sy, 130, '#F4A7B9', t, EV.burp, { life: 1.0, rot: -.08, grow: .15 }); }
    { const [sx, sy] = at(KILN.x + 60, 1050); boom('咯噔!', sx, sy, 96, HARD, t, EV.lastClunk, { rot: .1, life: .55 }); }
    { const [sx, sy] = at(MGR.x - 10, MGR.y - 560); boom('……?', sx, sy, 80, CREAM, t, EV.lastClunk + .45, { life: .6 }); }
  }
  function skyIsles(t) {
    ISLES.forEach((I, i) => {
      const on = ease(seg(t, ISLE_T[i] - .15, ISLE_T[i] + .15));
      isle(t, I, on, i);
      // 岛上的 Clawd：错开相位按拍蹦
      if (on > .02) {
        const pk = backOut(seg(t, ISLE_T[i], ISLE_T[i] + .3)), mv = move(['hop', 'bounce', 'roof', 'shimmy', 'wave'][i], t + i * .13, i);
        clawd(I.x + 170 - (i % 2) * 340, I.y - 12, 13 * pk, { ...mv, eyes: 'happy', mouth: 'grin', hat: 'hard', boilKey: 'isle clawd ' + i, noShadow: true });
        const [sx, sy] = toScreen(I.x, I.y - 470);
        boom(I.zh, sx, sy, 96, HARD, t, ISLE_T[i], { life: 99, rot: (i % 2 ? .06 : -.06) });
        boom(I.en, sx, sy + 70, 40, CREAM, t, ISLE_T[i] + .08, { life: 99, rot: (i % 2 ? .06 : -.06), font: 'Fredoka' });
      }
    });
  }
  function counter(t) {
    if (t < EV.count || t > 40.3) return;
    const n = Math.round(lerp(0, 10000, easeOut(seg(t, EV.count, EV.tada)))), out = 1 - seg(t, 40.0, 40.3);
    letterFn(c => {
      c.globalAlpha = out; c.translate(540, 760); const k = backOut(seg(t, EV.count, EV.count + .3)) * (1 + .08 * pulse2(t, 10)); c.scale(k, k);
      c.textAlign = 'center'; c.textBaseline = 'middle'; c.lineJoin = 'round';
      const s = t < EV.tada ? `${n.toLocaleString('en-US')}` : '近 10,000';
      c.font = '150px "Fredoka"'; c.font = '700 150px "Fredoka"';
      c.lineWidth = 24; c.strokeStyle = INK; c.strokeText(s, 0, 0); c.fillStyle = t < EV.tada ? CREAM : HARD; c.fillText(s, 0, 0);
      c.font = '84px "Smiley Sans"'; c.lineWidth = 16; c.strokeText('家企业的设备保姆', 0, 130); c.fillStyle = CREAM; c.fillText('家企业的设备保姆', 0, 130);
    });
    if (t > EV.tada) { const [sx, sy] = [540, 540]; boom('✦', sx - 360, sy, 90, HARD, t, EV.tada, { life: .9 }); boom('✦', sx + 360, sy + 40, 70, PAL.rose, t, EV.tada + .08, { life: .9 }); }
  }
  function endCard(t) {
    if (t < EV.card - .05) return;
    const k1 = backOut(seg(t, EV.card, EV.card + .3)), k2 = backOut(seg(t, EV.card2, EV.card2 + .3)), k3 = backOut(seg(t, EV.card3, EV.card3 + .3));
    const hide = 1 - seg(t, 45.25, 45.6), p = pulse(t, 8);
    letterFn(c => {
      c.globalAlpha = hide; c.textAlign = 'center'; c.textBaseline = 'middle'; c.lineJoin = 'round';
      const txt = (s, x, y, size, fill, k, font = 'Smiley Sans', rot = 0, sw = .16) => { if (k <= .01) return; c.save(); c.translate(x, y); c.rotate(rot + Math.sin(t * 2 + y) * .01); c.scale(k, k); c.font = `${size}px "${font}"`; c.fillStyle = INK; c.fillText(s, size * .05, size * .08); c.lineWidth = size * sw; c.strokeStyle = INK; c.strokeText(s, 0, 0); c.fillStyle = fill; c.fillText(s, 0, 0); c.restore(); };
      txt('武汉开明高新', 540, 215, 132 * (1 + .02 * p), '#E8743F', k1, 'Smiley Sans', -.04);
      txt('科技有限公司', 600, 318, 58, CREAM, k1 * seg(t, EV.card + .12, EV.card + .3), 'Smiley Sans', -.04);
      if (k2 > .01) { c.save(); c.translate(540, 408); c.rotate(.03); c.scale(k2, k2); c.fillStyle = 'rgba(43,34,51,.92)'; c.beginPath(); c.roundRect(-300, -44, 600, 88, 44); c.fill(); c.font = '56px "ZCOOL KuaiLe"'; c.fillStyle = HARD; c.fillText('大型设备 · 在线修复', 0, 4); c.restore(); }
      txt('抖音搜索 @WHKM2020', 540, 500, 50, CREAM, k3, 'Smiley Sans', .02, .2);
    });
  }
  function speedLines(t) {
    const W0 = [[26.0, 26.25, 'h'], [28.0, 28.35, 'h'], [32.2, 33.1, 'v'], [40.0, 40.9, 'v']];
    for (const [a, b, d] of W0) {
      if (t < a || t > b) continue;
      const k = Math.sin(Math.PI * seg(t, a, b));
      boilSeed('speed' + a);
      for (let i = 0; i < 16; i++) {
        const q = hash(i * 3 + Math.floor(t * 24)), L = 300 + 500 * hash(i + 11);
        if (d === 'h') { const y = 100 + i * 110 + q * 40, x = hash(i + 5) * W; inkLine([[x - L * k, y], [x + L * k, y]], .9, i % 3 ? CREAM : INK, 'inkfine', 0); }
        else { const x = 40 + i * 64 + q * 20, y = hash(i + 5) * H; inkLine([[x, y - L * k], [x, y + L * k]], .9, i % 3 ? '#FFFFFF' : INK, 'inkfine', 0); }
      }
    }
  }

  shots([[0, film]]);
})();
