// plates.js：四块水彩天空底板。只在预渲染时用真正的 p5.brush 水彩填充画一次（node render.mjs --loop=plate_<名> --stills=0），
// 视频里每帧直接贴图。色彩弧：灰（病了）→ 紫（噩梦）→ 金（修好）→ 蓝（云端）→ 金（片尾）。
(() => {
  const wc = (P, col, op = 150, bleed = .18, tex = .6) => paint(P, { fill: col, fillOp: op, bleed, tex, border: .5, ink: null });
  const blob = (x, y, rx, ry, rot = 0) => ellPts(x, y, rx, ry, 26, rx * .06, rot);

  defPlate('gray', '#A7AEC0', () => {
    paint(rectPts(-40, -40, W + 80, H + 80), { wash: '#B3B8C6', ink: null });
    wc(blob(540, 120, 900, 520), '#6F7894', 170, .25);
    wc(blob(200, 520, 520, 260, .2), '#8E93A6', 120, .3);
    wc(blob(860, 700, 480, 220, -.2), '#8E93A6', 110, .3);
    wc(blob(540, 1150, 1000, 280), '#D9B7B0', 140, .2);
    wc(blob(300, 1000, 380, 140, .1), '#E5CBBE', 120, .25);
    wc(blob(540, 1700, 900, 400), '#9EA3B3', 120, .2);
  });
  defPlate('gold', '#F6E3B4', () => {
    paint(rectPts(-40, -40, W + 80, H + 80), { wash: '#F7E6BC', ink: null });
    for (let i = 0; i < 7; i++) {              // 从地平线放射出的水彩光束（仿原片舞台背景）
      const a = -Math.PI / 2 + (i - 3) * .42, L = 1500, w = .17;
      wc([[540, 1150], [540 + Math.cos(a - w) * L, 1150 + Math.sin(a - w) * L], [540 + Math.cos(a + w) * L, 1150 + Math.sin(a + w) * L]], i % 2 ? '#F5C35A' : '#F0A39A', 120, .22);
    }
    wc(blob(540, 1180, 700, 260), '#F7C77E', 150, .25);
    wc(blob(160, 300, 300, 200, .3), '#EF9C8F', 110, .3);
    wc(blob(900, 420, 280, 180, -.3), '#F4B6A5', 110, .3);
    wc(blob(540, 1700, 900, 400), '#E7B48A', 110, .2);
  });
  defPlate('blue', '#CFE6F5', () => {
    paint(rectPts(-40, -40, W + 80, H + 80), { wash: '#D5EAF6', ink: null });
    wc(blob(540, 100, 900, 500), '#9CCBEB', 150, .25);
    wc(blob(200, 900, 420, 260, .2), '#F3C9D6', 120, .3);
    wc(blob(880, 1300, 420, 260, -.2), '#F6D9C2', 120, .3);
    wc(blob(540, 1750, 900, 380), '#B7DAF0', 130, .2);
    wc(blob(700, 600, 300, 160), '#FFFFFF', 140, .3);
  });
  defPlate('night', '#4B3A78', () => {
    paint(rectPts(-40, -40, W + 80, H + 80), { wash: '#4B3A78', ink: null });
    for (let i = 0; i < 4; i++) {              // 旋涡
      const P = []; for (let k = 0; k < 30; k++) { const a = k * .32 + i * 1.57, r = 60 + k * 26; P.push([540 + Math.cos(a) * r, 960 + Math.sin(a) * r * 1.2]); }
      wc(ribbon(P, 60, 240), ['#8A68C8', '#221640', '#B070B8', '#2E2352'][i], 200, .2);
    }
    wc(blob(540, 960, 260, 260), '#C07AC0', 160, .3);
    wc(blob(540, 960, 120, 120), '#F0B0D0', 150, .3);
  });

  // 噩梦底板裁成柔边圆，放进气泡
  const basePrepare = window.prepare;
  window.prepare = async () => {
    await basePrepare();
    const img = await new Promise(ok => { const im = new Image(); im.onload = () => ok(im); im.onerror = () => ok(null); im.src = 'assets/plates/night.jpg'; });
    if (!img) { PLATE.nightMask = null; return; }
    const g = createGraphics(1080, 1080); g.pixelDensity(1); const c = g.drawingContext;
    c.save(); c.beginPath(); c.arc(540, 540, 530, 0, TAU); c.clip(); c.drawImage(img, 0, 420, 1080, 1080, 0, 0, 1080, 1080); c.restore();
    const gr = c.createRadialGradient(540, 540, 420, 540, 540, 540); gr.addColorStop(0, 'rgba(75,58,120,0)'); gr.addColorStop(1, 'rgba(75,58,120,1)');
    c.globalCompositeOperation = 'source-atop'; c.fillStyle = gr; c.fillRect(0, 0, 1080, 1080);
    PLATE.nightMask = g;
  };
})();
