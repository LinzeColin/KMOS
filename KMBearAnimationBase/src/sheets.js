// sheets.js: 开明小熊的模型表（标准循环），只作参考，不进成片；这里允许标签文字。
//   node render.mjs --loop=bear_views --sheet=1 --cols=1 --w=1920 --flat --out=docs/bear_views.jpg
//   node render.mjs --loop=bear_emotions --sheet=1 --cols=1 --w=1920 --flat --out=docs/bear_emotions.jpg
(() => {
  const label = (txt, x, y, size = 20) => letter(txt, x, y, size, PAL.ink, { ink: false, alpha: .8 });
  const floor = (y, x0 = 0, x1 = W) => inkLine([[x0 + 40, y + 6], [W / 2, y + 4], [x1 - 40, y + 7]], .6, mixCol(PAL.paper, PAL.ink, .35), 'inkfine', .5);

  LOOPS.bear_views = t => {
    ['front', 'q', 'side', 'qback', 'back'].forEach((v, i) => {
      const x = 220 + i * 370; kmbear(x, 470, 26, { ...feel('neutral', t, { seed: i }), view: v }); label(v, x, 505, 24);
    });
    floor(470);
    const y2 = 960, u2 = 18, row = [
      ['goggles down', x => kmbear(x, y2, u2, { ...feel('determined', t), goggles: .5 + .5 * Math.sin(t * TAU / 2) })],
      ['talk', x => kmbear(x, y2, u2, { ...feel('happy', t), talk: speak(t % 2, .2, 1.8) })],
      ['wave', x => kmbear(x, y2, u2, { ...move('wave', t), eyes: 'happy' })],
      ['walk (side)', x => kmbear(x, y2, u2, { ...move('walk', t), view: 'side' })],
      ['jump', x => kmbear(x, y2, u2, { ...feel('excited', t), ...jump(t % 1.5, .35, .95, 3) })],
      ['hold', x => kmbear(x, y2, u2, { ...feel('proud', t), aR: 1.2, armR: (u, sw) => paint(starPts(u * .9, 0, u * 1.3, .5, 5), { wash: '#FFE27A', sw }) })],
    ];
    row.forEach(([name, f], i) => { const x = 170 + i * 316; f(x); label(name, x, y2 + 34); });
    floor(y2);
  };
  LOOPS.bear_views.len = 4;

  LOOPS.bear_emotions = t => {
    const names = Object.keys(EMO), cols = 8, cw = W / cols, ch = H / 4;
    names.forEach((name, i) => {
      const cx = cw * (i % cols) + cw / 2, gy = ch * Math.floor(i / cols) + ch - 50;
      kmbear(cx, gy, 13, feel(name, t, { seed: i }));
      label(name, cx, gy + 26);
    });
    for (let r = 0; r < 4; r++) floor(ch * r + ch - 50);
  };
  LOOPS.bear_emotions.len = 4;
})();
