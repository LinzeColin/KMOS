// kmbear.js: 开明小熊（KM Bear）, painted in the same brush-and-ink medium as Clawd.
// Design (from the KMBear release, 2D素材包/使用说明.md): cream-white bear, dark-brown eyes, pink cheeks, light-blue
// goggles on the forehead with a dark-blue strap, a mist-blue short work bib with two buttons and a KM chest pocket,
// arms that end in whole round paws, thick short limbs, wide ear roots that move with the head.
//
// kmbear(x, y, u, o): (x, y) = ground point between the feet; u = size unit. The bear is about 9u wide and 13.6u tall.
// Body-local coordinates in the front view (used by the o.draw hook):
//   feet y 0; torso centre (0, -4.6u); bib pocket (0, -4.5u); head centre (0, -9.5u); eyes (±1.8u, -9.55u);
//   nose (0, -8.75u); mouth (0, -8.1u); goggles (0, -11.45u); ears (±3u, -12.3u); shoulders (±2.9u, -6.4u).
// Arms: o.aL / o.aR use Clawd's convention (0 = straight out, + = up, − = down, ±1.5 vertical), so feel(), emotions()
// and move() from clawd.js drive the bear unchanged. At rest the arms hang beside the body.
// o.armL / o.armR are called at the paw centre in arm space (+x runs outward along the arm).
//
// Bear-only options: goggles 0..1 (0 = on the forehead, 1 = pulled down over the eyes), talk 0..1 (mouth open for
// speech; drive it with speak()), noGoggles, noBlush, fur / bib colour overrides (furCol, bibCol).
// Everything Clawd accepts for pose, view, face, emote, tint and boil works the same way.

const BEAR = {
  fur: '#F8F0E3', furDk: '#E4D3BC', furLt: '#FFFAF2', line: '#7A5540', earIn: '#F2B8B0', blush: '#F5A6A5',
  eye: '#3A2318', nose: '#4B2D20', bib: '#87AEE2', bibDk: '#5F8BCB', km: '#1E4FA6',
  lens: '#CFE4F8', lensRim: '#86B0E4', strap: '#2D5BA9', btn: '#4F7EC4', mouthIn: '#6B2E35', tongue: '#EE8A95',
};

// Key views, like Clawd's: every view faces screen-right, flip mirrors it.
//   face: feature centre x and horizontal squash (null = no face).  ears: [x, far].  arms: [pivotX, dir, which, layer]
//   (layer 0 = behind the torso, 1 = in front).  legs: [x, far].  bib: [x shift, width scale].  headRx: head half-width.
const BEAR_VIEWS = {
  front: { face: { cx: 0, fw: 1, sides: [-1, 1] }, ears: [[-3, 0], [3, 0]], headRx: 4.3, bib: [0, 1],
           arms: [[-2.9, -1, 'L', 1], [2.9, 1, 'R', 1]], legs: [[-1.75, 0], [1.75, 0]] },
  q:     { face: { cx: 1.15, fw: .8, sides: [-1, 1] }, ears: [[-2.3, 1], [3.3, 0]], headRx: 4.2, bib: [.55, .9],
           arms: [[-2.3, -1, 'L', 0], [3.1, 1, 'R', 1]], legs: [[-1.3, 1], [1.9, 0]] },
  side:  { face: { cx: 1.9, fw: .6, sides: [1] }, side: true, ears: [[-.7, 0]], headRx: 3.8, bib: [.7, .78],
           arms: [[.2, 0, 'R', 1]], legs: [[-1.1, 1], [.9, 0]] },
  qback: { face: null, back: true, ears: [[-3.3, 0], [2.3, 1]], headRx: 4.2, bib: [-.55, .9],
           arms: [[2.3, 1, 'L', 0], [-3.1, -1, 'R', 1]], legs: [[1.3, 1], [-1.9, 0]] },
  back:  { face: null, back: true, ears: [[-3, 0], [3, 0]], headRx: 4.3, bib: [0, 1],
           arms: [[-2.9, -1, 'R', 1], [2.9, 1, 'L', 1]], legs: [[-1.75, 0], [1.75, 0]] },
};

// Clawd's arm angles start straight out; the bear's arms rest hanging down, so the same numbers are remapped:
// a ≤ 0.2 stays near hanging, and raising past 0.2 lifts the arm up to vertical at 1.5.
const bearArm = a => a >= .2 ? -1.05 + (a - .2) * 1.97 : -1.05 + (a - .2) * .12;

let BEAR_N = 0;
function kmbear(x, y, u, o = {}) {
  const id = o.boilKey ?? 'b' + (++BEAR_N), rs = part => boilSeed(`kmbear ${id} ${part}`);
  x += (o.dx || 0) * u;
  const V = BEAR_VIEWS[o.view] || BEAR_VIEWS.front;
  const dy = (o.dy || 0) * u, sq = (o.sq || 0) + (o.take || 0), sm = clamp(o.smear || 0);
  const sw = clamp(u / 15, .45, 2.4) * .62 * (o.swMul || 1), J = u * .05, L = BEAR.line;
  const tc = o.tint && (TINT[o.tint] || o.tint), tk = clamp(o.tintK ?? 1) * .3;
  const fur = mixCol(o.furCol || BEAR.fur, tc || BEAR.fur, tc ? tk : 0), furDk = mixCol(BEAR.furDk, tc || BEAR.furDk, tc ? tk : 0);
  const bib = o.bibCol || BEAR.bib, P = pts => pts.map(([a, b]) => [a * u, b * u]);

  rs('shadow');
  if (!o.noShadow) {
    const f = 1 - Math.min(.5, Math.abs(o.dy || 0) * .05);
    paint(ellPts(x, y + u * .15, u * 4.2 * f, u * .8 * f, 22), { fill: PAL.ink, fillOp: 80, bleed: .25, tex: .3, border: .1, ink: null });
  }
  if (sm > .05) smearTrail(x, y + dy - 3 * u, u * .9, { R: 4.3 }, sm, o.smearDir ?? (o.flip ? -1 : 1), fur);

  push();
  translate(x, y + dy);
  if (o.rot) rotate(o.rot);
  scale((o.flip ? -1 : 1) * (o.sx ?? 1) * (1 + sq * .6) * (1 + sm * .3), (o.sy ?? 1) * (1 - sq));

  const arm = ([px, dir, which, layer]) => {
    rs('arm' + which);
    const A = bearArm(which === 'L' ? (o.aL ?? .2) : (o.aR ?? .2)), hook = which === 'L' ? o.armL : o.armR;
    const col = layer === 0 ? furDk : fur;
    push(); translate(px * u, -6.4 * u);
    if (dir === 0) {   // profile: the near arm swings forward (+) or back (−) from the shoulder
      rotate(Math.PI / 2 - .25 - (A + 1.05) * .9);
      paint(rrPts(-.8 * u, -.75 * u, 4.2 * u, 1.5 * u, .75 * u, J), { wash: col, ink: L, sw: sw * .8 });
      if (hook) { translate(2.7 * u, 0); hook(u, sw); }
    } else {
      rotate(dir < 0 ? A : -A);
      paint(rrPts(dir < 0 ? -3.6 * u : -.4 * u, -.8 * u, 4 * u, 1.6 * u, .8 * u, J), { wash: col, ink: L, sw: sw * .8 });
      if (hook) { translate(dir * 2.75 * u, 0); if (dir < 0) scale(-1, 1); hook(u, sw); }
    }
    pop();
  };

  // legs, arms behind, ears, torso + bib, arms in front, head, face, goggles
  if (!o.noLegs) V.legs.forEach(([lx, isFar], i) => {
    rs('leg' + i);
    let h = 3.2, sx = 0;
    if (o.walk != null) {
      const ph = (o.walk + i * .5) * TAU;
      if (V.side) { sx = Math.sin(ph) * .7; h = 3.2 - Math.max(0, Math.cos(ph)) * .8; }
      else { const lift = Math.sin(ph); if (lift > 0) h = 3.2 - lift * .9; }
    }
    paint(rrPts((lx + sx - 1.25) * u, -3.4 * u, 2.5 * u, h * u + .2 * u, 1.1 * u, J), { wash: isFar ? furDk : fur, ink: L, sw: sw * .8 });
  });
  V.arms.filter(a => a[3] === 0).forEach(arm);

  rs('torso');
  const [bx, bw] = V.bib;
  paint(ellPts(bx * .4 * u, -4.7 * u, 3.4 * u * (V.side ? .8 : 1), 2.9 * u, 30, J), { wash: fur, ink: L, sw });
  rs('bib');
  if (!V.back) {
    const bib0 = P([[-2.35, -5.95], [2.35, -5.95], [2.75, -4.4], [3.05, -3.1], [2.6, -2.75], [0, -2.65], [-2.6, -2.75], [-3.05, -3.1], [-2.75, -4.4]].map(([a, b]) => [bx + a * bw, b]));
    paint(bib0, { wash: bib, ink: L, sw: sw * .7, curv: .25 });
    for (const s of [-1, 1]) {   // straps and buttons
      const sx0 = bx + s * 1.95 * bw;
      paint(P([[sx0 - .38, -5.9], [sx0 + .38, -5.9], [sx0 + .32 + s * .1, -7.35], [sx0 - .44 + s * .1, -7.35]]), { wash: bib, ink: L, sw: sw * .6 });
      paint(ellPts(sx0 * u, -5.75 * u, .3 * u, .3 * u, 10), { wash: BEAR.btn, ink: L, sw: sw * .45 });
    }
    if (!V.side) {   // the KM pocket, lettered in paint strokes
      const kx = bx * u, ky = -4.5 * u, pw = 2.4 * u * bw, ph = 1.5 * u;
      paint(rrPts(kx - pw / 2, ky - ph / 2, pw, ph, .3 * u, J * .5), { wash: mixCol(bib, '#FFFFFF', .12), ink: mixCol(bib, L, .45), sw: sw * .5 });
      if (u > 6) {
        if (o.flip) { push(); translate(kx, 0); scale(-1, 1); translate(-kx, 0); }   // letters read the right way when mirrored
        const G = pts => pts.map(([a, b]) => [kx + a * u * bw, ky + b * u]), w = sw * 1.1;
        inkLine(G([[-.85, -.42], [-.85, .42]]), w, BEAR.km, 'inkfine', 0);
        inkLine(G([[-.25, -.42], [-.8, .0]]), w, BEAR.km, 'inkfine', 0);
        inkLine(G([[-.62, -.12], [-.22, .42]]), w, BEAR.km, 'inkfine', 0);
        inkLine(G([[.1, .42], [.14, -.42], [.47, .1], [.8, -.42], [.84, .42]]), w, BEAR.km, 'inkfine', 0);
        if (o.flip) pop();
      }
    }
  } else {   // from behind: straps run down the back to the hem band
    for (const s of [-1, 1]) { const sx0 = bx + s * 1.5; paint(P([[sx0 - .35, -7.3], [sx0 + .35, -7.3], [sx0 + .35, -3.9], [sx0 - .35, -3.9]]), { wash: bib, ink: L, sw: sw * .6 }); }
    paint(P([[bx - 3, -3.9], [bx + 3, -3.9], [bx + 3.05, -3.05], [bx, -2.7], [bx - 3.05, -3.05]]), { wash: bib, ink: L, sw: sw * .7, curv: .2 });
  }
  V.arms.filter(a => a[3] === 1 && !V.side).forEach(arm);

  // head (ears first, so the head overlaps their roots)
  push(); translate(0, -9.5 * u); rotate(o.headRot || 0); translate(0, 9.5 * u);
  V.ears.forEach(([ex, isFar], i) => {
    rs('ear' + i);
    const r = isFar ? 1.2 : 1.35;
    paint(ellPts(ex * u, -12.3 * u, r * u, r * u, 18, J), { wash: isFar ? furDk : fur, ink: L, sw: sw * .8 });
    if (!V.back && !isFar) paint(ellPts(ex * u + (V.face ? V.face.cx * .12 * u : 0), -12.2 * u, .72 * u, .72 * u, 14), { wash: BEAR.earIn, ink: null });
  });
  rs('head');
  const hr = V.headRx;
  if (V.side) paint(ellPts(3.3 * u, -8.5 * u, 1.45 * u, 1.05 * u, 20, J * .6), { wash: BEAR.furLt, ink: L, sw: sw * .8 });   // snout, under the head
  paint(ellPts(0, -9.5 * u, hr * u, 3.75 * u, 40, J), { wash: fur, ink: L, sw });
  if (V.side) paint(ellPts(3.45 * u, -8.5 * u, 1.2 * u, .85 * u, 18), { wash: BEAR.furLt, ink: null });   // snout face over the head edge
  if (V.face) faceOf(u, o, sw, V);
  rs('goggles');
  if (!o.noGoggles) goggles(u, o, sw, V);
  pop();

  V.arms.filter(a => a[3] === 1 && V.side).forEach(arm);
  rs('draw'); if (o.draw) o.draw(u, sw);
  pop();

  rs('emote');
  if (o.emote) {
    const dir = o.flip ? -1 : 1, ex = x + dir * 4.6 * u, ey = y + dy - 13 * u * (1 - sq);
    emote(o.emote, ex, ey, u * .8, o.emoteK ?? 1, o.emoteAge ?? T);
  }
  rs('after');
}

// ---------- face ----------
function faceOf(u, o, sw, V) {
  const F = V.face;
  push(); translate(F.cx * u, 0); scale(F.fw, 1);
  const bl = o.noBlush ? 0 : clamp(.55 + (o.blush || 0) * .45);
  if (bl > .02) for (const s of F.sides) paint(ellPts(s * (F.fw < .9 ? 2.35 : 2.85) * u, -8.45 * u, .8 * u, .45 * u, 14), { wash: BEAR.blush, washOp: 200 * bl, ink: null });
  if (!V.side) {
    paint(ellPts(0, -8.3 * u, 1.6 * u, 1.12 * u, 22, u * .03), { wash: BEAR.furLt, ink: mixCol(BEAR.furLt, BEAR.line, .25), sw: sw * .5 });
    paint(ellPts(0, -8.8 * u, .45 * u, .32 * u, 12), { wash: BEAR.nose, ink: null });
    paint(ellPts(-.12 * u, -8.9 * u, .13 * u, .07 * u, 6), { wash: BEAR.furLt, washOp: 200, ink: null });
  }
  pop();
  if (V.side) paint(ellPts(4.55 * u, -8.8 * u, .38 * u, .3 * u, 10), { wash: BEAR.nose, ink: null });
  push(); translate(F.cx * u, 0); scale(F.fw, 1);
  bearEyes(u, o, sw, F.sides);
  pop();
  push();
  if (V.side) translate(3.75 * u, 0); else { translate(F.cx * u, 0); scale(F.fw, 1); }
  bearMouth(u, o.talk > .05 ? (o.talk > .6 ? 'open' : 'o') : o.mouth, sw, o.talk || 0, V.side);
  pop();
}

// Eyes: round, dark brown, with a highlight. Kinds follow Clawd's list; the rarer ones reuse Clawd's painted eyes.
function bearEyes(u, o, sw, sides) {
  const kinds = Array.isArray(o.eyes) ? o.eyes : o.eyes === 'wink' ? ['happy', 'normal'] : [o.eyes || 'normal', o.eyes || 'normal'];
  if (kinds[0] === 'shades') return;   // the goggles come down as sunglasses
  const sqz = clamp(o.squint || 0), lx = (o.lookX || 0) * .28 * u, ly = (o.lookY || 0) * .22 * u;
  const brow = (s, tilt, y0 = -10.35) => inkLine([[s * 1.35 * u, (y0 - tilt * s * -.18) * u], [s * 1.8 * u, (y0 - .12) * u], [s * 2.25 * u, (y0 + tilt * s * -.18) * u]].map(([a, b]) => [a, b]), sw * .7, BEAR.line, 'inkfine', .5);
  for (const s of sides) {
    const e = kinds[s < 0 ? 0 : 1];
    push(); translate(s * 1.8 * u, -9.55 * u);
    if (sqz > .75) { inkLine([[-.5 * u, 0], [.5 * u, 0]], sw, BEAR.eye, 'ink', 0); pop(); continue; }
    if (sqz > 0) scale(1 + sqz * .1, 1 - sqz);
    const blink = ['normal', 'look', 'wide', 'shine', 'dot'].includes(e) && ((T * .9 + (o.seed || 0) * 1.7) % 3.3) < .12;
    const arc = (pts, w = 1.2) => inkLine(pts.map(([a, b]) => [a * u, b * u]), sw * w, BEAR.eye, 'ink', .5);
    const round = (rx, ry, hl = 1) => {
      paint(ellPts(lx, ly, rx * u, ry * u, 16), { wash: BEAR.eye, ink: null });
      if (hl && u > 5) {
        paint(ellPts(lx - .2 * u, ly - .25 * u, .19 * u * hl, .21 * u * hl, 8), { wash: BEAR.furLt, ink: null });
        paint(ellPts(lx + .18 * u, ly + .2 * u, .08 * u * hl, .08 * u * hl, 6), { wash: BEAR.furLt, ink: null });
      }
    };
    if (blink) arc([[-.5, .05], [0, .25], [.5, .05]]);
    else switch (e) {
      case 'normal': case 'look': case 'dot': round(.5, .6); break;
      case 'wide': round(.62, .74); break;
      case 'shine': round(.64, .76, 1.5); paint(starPts(lx + .25 * u, ly - .3 * u, .22 * u, .4, 4), { wash: BEAR.furLt, ink: null }); break;
      case 'happy': arc([[-.55, .2], [0, -.35], [.55, .2]]); break;
      case 'closed': arc([[-.55, -.05], [0, .3], [.55, -.05]]); break;
      case 'sleepy': paint(ellPts(lx, .15 * u + ly, .5 * u, .32 * u, 12), { wash: BEAR.eye, ink: null }); arc([[-.6, -.05], [0, -.12], [.6, -.02]], 1); break;
      case 'narrow': paint(ellPts(lx, ly + .1 * u, .52 * u, .26 * u, 12), { wash: BEAR.eye, ink: null }); break;
      case 'angry': case 'determined': round(.48, .55); pop(); push(); translate(s * 1.8 * u, -9.55 * u);
        inkLine([[-s * .75 * u, -1.15 * u], [s * .6 * u, (e === 'angry' ? -.7 : -.85) * u]], sw * 1.1, BEAR.line, 'ink', 0); break;
      case 'sad': case 'teary': round(.48, .58);
        inkLine([[-s * .7 * u, -.85 * u], [s * .6 * u, -1.15 * u]], sw * .9, BEAR.line, 'ink', 0);
        if (e === 'teary') paint(ellPts(lx, .7 * u, .55 * u, .22 * u, 12), { wash: PAL.sky, washOp: 220, ink: null }); break;
      case 'squeeze': arc([[-.45 * -s, -.45], [.4 * -s, 0], [-.45 * -s, .45]], 1.2); break;
      default: scale(.62); eye(e, s, u, o, sw);   // cry, scared, blank, spark, red, heart, x, swirl, shades
    }
    pop();
  }
}

// Mouth under the nose. Bear rest face is a small smile. talk 0..1 opens it for speech.
function bearMouth(u, m, sw, talk = 0, side = false) {
  const P = pts => pts.map(([a, b]) => [a * u, b * u]), line = (pts, w = .75, c = .6) => inkLine(P(pts), sw * w, BEAR.line, 'ink', c);
  if (!side) line([[0, -8.5], [0, -8.2]], .6, 0);
  const x0 = side ? -.25 : 0, open = (w, h) => {
    paint(ellPts(x0 * u, -7.8 * u, w * u, h * u, 16), { wash: BEAR.mouthIn, ink: BEAR.line, sw: sw * .5 });
    paint(ellPts(x0 * u, (-7.8 + h * .45) * u, w * .6 * u, h * .38 * u, 10), { wash: BEAR.tongue, ink: null });
  };
  switch (m || 'smile') {
    case 'smile': case 'cat': line([[x0 - .6, -8.2], [x0 - .28, -7.95], [x0, -8.2], [x0 + .28, -7.95], [x0 + .6, -8.2]], .7, .5); break;
    case 'grin': case 'laugh': open(.62, .5); break;
    case 'open': open(.42 + .2 * talk, .26 + .34 * talk); break;
    case 'o': paint(ellPts(x0 * u, -7.9 * u, .22 * u, .22 * u, 10), { wash: BEAR.mouthIn, ink: null }); break;
    case 'O': case 'yawn': case 'wail': open(.4, .55); break;
    case 'flat': line([[x0 - .45, -8.05], [x0 + .45, -8.05]], .7, 0); break;
    case 'frown': line([[x0 - .5, -7.8], [x0, -8.1], [x0 + .5, -7.8]]); break;
    case 'wobble': line([[x0 - .6, -8], [x0 - .3, -8.15], [x0, -8], [x0 + .3, -8.15], [x0 + .6, -8]], .6, .3); break;
    case 'smirk': line([[x0 - .5, -8.05], [x0 + .1, -8.05], [x0 + .55, -8.3]]); break;
    case 'tongue': line([[x0 - .55, -8.2], [x0, -7.9], [x0 + .55, -8.2]]); paint(ellPts((x0 + .15) * u, -7.75 * u, .25 * u, .28 * u, 10), { wash: BEAR.tongue, ink: BEAR.line, sw: sw * .4 }); break;
    case 'pout': line([[x0 - .3, -7.95], [x0, -8.15], [x0 + .3, -7.95]], .9); break;
    case 'teeth': paint(rrPts((x0 - .55) * u, -8.15 * u, 1.1 * u, .5 * u, .15 * u), { wash: BEAR.furLt, ink: BEAR.line, sw: sw * .5 }); break;
    default: line([[x0 - .55, -8.2], [x0, -7.9], [x0 + .55, -8.2]]);
  }
}

// Goggles: on the forehead, or pulled down over the eyes (o.goggles 0..1). eyes: 'shades' tints the lens dark.
function goggles(u, o, sw, V) {
  const dark = (Array.isArray(o.eyes) ? o.eyes[0] : o.eyes) === 'shades', k = dark ? 1 : ease(clamp(o.goggles || 0)), gy = lerp(-11.45, -9.6, k);
  const hr = V.headRx * lerp(.94, 1, k), lensOp = lerp(225, 150, k);
  if (V.back) {
    paint(rectPts(-hr * u, (gy - .35) * u, 2 * hr * u, .72 * u, J0(u)), { wash: BEAR.strap, ink: BEAR.line, sw: sw * .5 });
    paint(rrPts(-.9 * u, (gy - .45) * u, 1.8 * u, .9 * u, .2 * u), { wash: mixCol(BEAR.strap, '#FFFFFF', .2), ink: BEAR.line, sw: sw * .45 });
    return;
  }
  const F = V.face, cx = F.cx * u;
  if (V.side) {
    paint(rectPts(-hr * .92 * u, (gy - .32) * u, (hr * .92 + 2.4) * u, .66 * u, J0(u)), { wash: BEAR.strap, ink: BEAR.line, sw: sw * .5 });
    paint(rrPts(2.2 * u, (gy - .85) * u, 1.9 * u, 1.7 * u, .6 * u), { wash: dark ? '#2B3450' : BEAR.lens, washOp: lensOp, ink: BEAR.lensRim, sw: sw * .9 });
    return;
  }
  for (const s of [-1, 1]) {   // strap ends out to the head's edge
    const x0 = cx + s * 2.55 * u * F.fw, x1 = s * hr * u * (s * F.cx > 0 ? 1 : .98);
    paint([[x0, (gy - .34) * u], [x1, (gy - .3) * u], [x1, (gy + .36) * u], [x0, (gy + .34) * u]], { wash: BEAR.strap, ink: BEAR.line, sw: sw * .5 });
  }
  push(); translate(cx, gy * u); scale(F.fw, 1);
  const lens = P0(u, [[-2.75, -.55], [-1.2, -.95], [0, -.8], [1.2, -.95], [2.75, -.55], [2.8, .35], [1.6, .72], [.45, .55], [0, .35], [-.45, .55], [-1.6, .72], [-2.8, .35]]);
  paint(lens, { wash: dark ? '#2B3450' : BEAR.lens, washOp: dark ? 235 : lensOp, ink: BEAR.lensRim, sw: sw * .95, curv: .4 });
  inkLine(P0(u, [[-2.1, -.35], [-1.3, -.6]]), sw * .6, '#FFFFFF', 'inkfine', 0);
  inkLine(P0(u, [[1.4, -.55], [1.9, -.45]]), sw * .45, '#FFFFFF', 'inkfine', 0);
  pop();
}
const P0 = (u, pts) => pts.map(([a, b]) => [a * u, b * u]);
const J0 = u => u * .03;

// ---------- speech ----------
// speak(t, t0, t1): a talk value for o.talk that opens and closes on syllables (about 5 a second) between t0 and t1,
// easing in and out, so a narrated line reads as speech. Pair it with the line's caption or voice.
function speak(t, t0, t1, rate = 5.2) {
  if (t < t0 || t > t1) return 0;
  const env = Math.min(1, (t - t0) * 6, (t1 - t) * 6), ph = (t - t0) * rate;
  return env * Math.max(0, Math.sin(ph * Math.PI)) * (.55 + .45 * hash(Math.floor(ph)));
}
