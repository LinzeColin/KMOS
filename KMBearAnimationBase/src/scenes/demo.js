// demo.js: 「击掌」——小熊对着一张纸发愁，Clawd 跳进来帮忙，两人击掌。展示套件在跑，不是模板。
(() => {
  const SKY = '#DCE9F5', FLOOR = '#C9D8B4';
  function room(lt) {
    paint(rectPts(-80, -80, W + 160, H + 160), { wash: SKY, ink: null });
    boilSeed('floor'); paint(rectPts(-80, 880, W + 160, 300), { wash: FLOOR, ink: PAL.ink, sw: .6 });
    boilSeed('sun'); glow(1580, 220, 260, '#FFE3A0', .6);
  }
  function paper(x, y, s, rot) {
    push(); translate(x, y); rotate(rot);
    paint(rectPts(-s * 1.4, -s * 1.8, s * 2.8, s * 3.6, s * .05), { wash: '#FFFDF6', ink: PAL.ink, sw: .8 });
    for (let i = 0; i < 4; i++) inkLine([[-s, -s * 1.1 + i * s * .6], [s * (i === 3 ? .2 : 1), -s * 1.1 + i * s * .6]], .5, PAL.indigo, 'inkfine', 0);
    pop();
  }
  function highfive(t, lt, dur) {
    camBegin(960 + 30 * Math.sin(lt * .5), 620, 1.05 + .015 * lt);
    room(lt);
    const bearMood = emotions(lt, [[0, 'thinking'], [2.4, 'surprised'], [3.3, 'happy'], [4.4, 'excited']]);
    const hop = jump(lt, 1.9, 2.5, 4), cx = lerp(1700, 1150, easeOut(seg(lt, 1.9, 2.5)));
    const five = seg(lt, 3.6, 3.9), slap = spring(lt, 3.9, 7, 30), up = jump(lt, 3.5, 4.3, 7);
    kmbear(820, 900, 34, { ...bearMood, aR: lt < 3.3 ? 1.2 : lerp(1.2, .95, five), aL: lt < 2.4 ? 1 : bearMood.aL,
      armR: lt < 3.3 ? (u) => paper(u * .6, -u * .4, u * .9, -.2 + .05 * Math.sin(lt * 3)) : null, rot: -.04 * slap });
    clawd(cx, 900, 22, { ...emotions(lt, [[0, 'excited'], [3.9, 'laugh']]), dy: hop.dy + up.dy, sq: hop.sq + up.sq, flip: true,
      aL: lt < 3.3 ? .5 : lerp(.5, 1.05, five), rot: .05 * slap, noShadow: lt < 1.9 });
    if (lt > 3.9 && lt < 4.4) { boilSeed('clap'); emote('spark', 1060, 450, 30, seg(lt, 3.9, 4)); }
    camEnd();
    if (lt < .4) iris(960, 540, lerp(0, 1400, easeIn(lt / .4)));
    if (lt > dur - .6) iris(820, 560, lerp(1400, 0, ease((lt - (dur - .6)) / .6)));
  }
  shots([[0, highfive]]);
})();
