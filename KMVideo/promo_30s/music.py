"""原创 BGM + 音效合成（120 BPM，Am–F–C–G），与 render.html 共用同一时间轴。

全部由代码生成，无第三方音源，版权归属清晰，可在抖音/X/Instagram/Facebook 商用发布。
用法：python3 music.py OUT.wav
"""
import sys
import numpy as np
from scipy.signal import butter, sosfilt
import wave

SR = 44100
DUR = 30.0
BEAT = 0.5
N = int(SR * DUR)
L = np.zeros(N)
R = np.zeros(N)
rng = np.random.default_rng(2020)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def tt(d):
    return np.arange(int(d * SR)) / SR


def filt(x, kind, f, order=2):
    w = np.asarray(f, dtype=float) / (SR / 2)
    sos = butter(order, w if w.ndim else float(w), btype=kind, output="sos")
    return sosfilt(sos, x)


def add(sig, t0, g=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= N:
        return
    sig = sig[: N - i]
    L[i:i + len(sig)] += sig * g * np.sqrt(0.5 * (1 - pan))
    R[i:i + len(sig)] += sig * g * np.sqrt(0.5 * (1 + pan))


def saw(f, t, det=0.0):
    ph = (f * (1 + det)) * t
    return 2 * (ph - np.floor(ph + 0.5))


def adsr(n_s, a=0.005, d=0.1, s=0.6, r=0.05, total=None):
    t = tt(total or n_s + r)
    e = np.where(t < a, t / a, s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    rel = t > n_s
    e[rel] *= np.exp(-(t[rel] - n_s) / max(r, 1e-4) * 5)
    return e


# ---------- 乐器 ----------
def kick(g=1.0):
    t = tt(0.35)
    f = 45 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) * np.exp(-t * 7) + 0.3 * filt(rng.standard_normal(len(t)), "high", 3000) * np.exp(-t * 90)) * g


def clap():
    t = tt(0.25)
    n = filt(rng.standard_normal(len(t)), "band", [900, 2600])
    e = np.exp(-t * 22) + 0.6 * np.exp(-((t - 0.012) % 0.011) * 300) * (t < 0.035)
    return n * e * 0.9


def hat(open_=False):
    t = tt(0.28 if open_ else 0.06)
    return filt(rng.standard_normal(len(t)), "high", 7000) * np.exp(-t * (14 if open_ else 70)) * 0.5


def bass_note(m, d):
    t = tt(d)
    x = saw(hz(m), t) + 0.5 * np.sin(2 * np.pi * hz(m - 12) * t)
    x = filt(x, "low", 900)
    return x * adsr(d * 0.8, 0.004, 0.12, 0.5, 0.03, total=d)[: len(t)]


def pluck(m, d, bright=3500):
    t = tt(d)
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * (t > 0.12)
    x = saw(hz(m) * vib, t, 0.004) + saw(hz(m) * vib, t, -0.006) + 0.6 * np.sign(np.sin(2 * np.pi * hz(m - 12) * t))
    x = filt(x, "low", bright)
    return x * adsr(d * 0.85, 0.004, 0.18, 0.45, 0.05, total=d)[: len(t)] * 0.35


def pad(ms, d, cut=1400):
    t = tt(d)
    x = sum(saw(hz(m), t, dt) for m in ms for dt in (-0.005, 0.0, 0.006))
    x = filt(x, "low", cut)
    e = np.minimum(1, t / 0.25) * np.minimum(1, (d - t) / 0.2)
    return x * e * 0.08


def stab(ms, d=0.18):
    t = tt(d)
    x = sum(saw(hz(m), t, dt) for m in ms for dt in (-0.007, 0.007))
    return filt(x, "low", 3200) * np.exp(-t * 14) * 0.12


def noise_sweep(d, f0, f1, g=1.0, rise=True):
    t = tt(d)
    n = rng.standard_normal(len(t))
    out = np.zeros_like(n)
    k = 16
    for j in range(k):
        a, b = j * len(n) // k, (j + 1) * len(n) // k
        f = f0 * (f1 / f0) ** (j / (k - 1))
        out[a:b] = filt(n[a:b], "band", [f * 0.7, min(f * 1.4, 20000)])
    e = (t / d) ** 2 if rise else np.exp(-t * 6)
    return out * e * g


def tone(f, d, dec=8.0, kind="sine"):
    t = tt(d)
    w = np.sin(2 * np.pi * f * t) if kind == "sine" else np.sign(np.sin(2 * np.pi * f * t)) * 0.5
    return w * np.exp(-t * dec)


def boing(d=0.45):
    t = tt(d)
    f = 180 + 420 * np.exp(-t * 6) * (1 + 0.35 * np.sin(2 * np.pi * 14 * t))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5) * 0.6


def slide(f0, f1, d, g=0.5, wob=5.0):
    t = tt(d)
    f = f0 * (f1 / f0) ** (t / d) * (1 + 0.03 * np.sin(2 * np.pi * wob * t))
    x = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.5 + np.sin(2 * np.pi * np.cumsum(f) / SR)
    return filt(x, "low", 1800) * np.minimum(1, t / 0.03) * np.minimum(1, (d - t) / 0.05) * g


# ---------- 编曲 ----------
CH = [[57, 60, 64], [53, 57, 60], [55, 60, 64], [55, 59, 62]]   # Am F C G
ROOT = [45, 41, 48, 43]
HOOK = [
    [(0, 76, 1), (2, 76, 1), (3, 79, 1), (4, 81, 2), (6, 79, 1), (7, 76, 1)],
    [(0, 72, 1), (2, 74, 1), (3, 76, 2), (6, 74, 1), (7, 72, 1)],
    [(0, 76, 1), (2, 76, 1), (3, 79, 1), (4, 81, 1), (5, 84, 2), (7, 81, 1)],
    [(0, 79, 2), (2, 76, 1), (3, 74, 1), (4, 76, 4)],
]
GROOVE = [(8.0, 20.0), (23.0, 27.875), (28.0, 29.5)]


def in_groove(t):
    return any(a <= t < b for a, b in GROOVE)


def bar_of(t):
    return int(t // 2) % 4


# 前奏 0–4：低通 pad + 轻打点
for b in range(2):
    add(pad(CH[b], 2.0, 900), b * 2.0, 1.0)
for i in range(8):
    add(hat(), i * BEAT + 0.25, 0.25, 0.3)
# 窑“嘎吱”
for t0 in (0.6, 1.6):
    add(slide(260, 180, 0.35, 0.35, 22), t0)
# 悲伤长号 wah-wah
for k, (m, d) in enumerate([(67, .3), (66, .3), (65, .3), (64, .6)]):
    add(slide(hz(m), hz(m) * 0.985, d, 0.45, 5), 2.0 + k * 0.3)
add(noise_sweep(0.55, 300, 6000, 0.9), 3.6)

# 铺垫 4–7.875：鼓进场，军鼓滚奏 + 上升音
for i in range(8):
    t0 = 4.0 + i * BEAT
    add(kick(0.9), t0)
    add(hat(), t0 + 0.25, 0.35, 0.2)
    add(bass_note(ROOT[bar_of(t0)], 0.22), t0 + 0.25, 0.5)
for b in range(2):
    add(pad(CH[2 + b], 2.0, 1600), 4.0 + b * 2.0, 1.1)
for i in range(26):
    add(tone(2400 + (i % 3) * 300, 0.12, 30), 4.2 + i * 0.1, 0.12, (i % 2) * 0.6 - 0.3)
for t0 in (4.3, 4.75):
    add(tone(1568, 0.5, 6) + tone(2093, 0.5, 6), t0, 0.35)
for i in range(14):
    add(noise_sweep(0.08, 2500, 6000, 0.5, rise=False), 5.5 + i * 0.1, 0.5, 0.4)
add(boing(), 6.25, 0.9)
roll_t = 6.0
step = 0.25
while roll_t < 7.875:
    add(clap(), roll_t, 0.25 + 0.5 * (roll_t - 6.0) / 1.875)
    roll_t += step
    step = max(0.0625, step * 0.86)
add(noise_sweep(1.87, 400, 9000, 0.8), 6.0)
for k in range(12):
    f = 1320 if (k // 2) % 2 == 0 else 1650
    add(tone(f, 0.05, 1, "square"), 7.0 + k * 0.05, 0.3)

# 8.0 爆点 + 主段落
def impact(t0, g=1.0):
    add(tone(55, 1.2, 2.5) * 1.2, t0, g)
    add(filt(rng.standard_normal(int(1.2 * SR)), "high", 2500) * np.exp(-tt(1.2) * 3.5) * 0.5, t0, g)
    add(kick(1.2), t0, g)


impact(8.0)
impact(23.0, 0.7)
impact(28.0, 1.0)

t = 8.0
while t < 30.0 - 1e-6:
    if in_groove(t):
        bi = int(round((t - 8.0) / BEAT))
        add(kick(), t)
        if bi % 2 == 1:
            add(clap(), t, 0.8)
        add(hat(True), t + 0.25, 0.4, 0.25)
        add(hat(), t + 0.125, 0.25, -0.3)
        add(hat(), t + 0.375, 0.25, -0.3)
        r = ROOT[bar_of(t)]
        add(bass_note(r, 0.2), t, 0.6)
        add(bass_note(r + 12, 0.2), t + 0.25, 0.5)
        add(stab(CH[bar_of(t)]), t + 0.25, 1.0, 0.2)
    t += BEAT

for bar_start in [8.0 + 2 * k for k in range(6)] + [24.0, 26.0]:
    idx = int(((bar_start - 8.0) / 2) % 4)
    for slot, m, ln in HOOK[idx]:
        t0 = bar_start + slot * 0.25
        if t0 < 27.875:
            add(pluck(m, ln * 0.25), t0, 0.9, 0.1)
            add(pluck(m + 12, ln * 0.25, 6000), t0, 0.25, -0.2)

# 卡车：急刹 + 倒车嘀嘀
t_s = tt(0.55)
screech = np.sin(2 * np.pi * np.cumsum(2100 + 300 * np.sin(2 * np.pi * 23 * t_s)) / SR) * np.exp(-t_s * 2)
add((screech * 0.5 + filt(rng.standard_normal(len(t_s)), "band", [1500, 4000]) * 0.4) * np.minimum(1, t_s / 0.05), 8.95, 0.45)
add(kick(0.7), 9.45)
for k in range(4):
    add(tone(1000, 0.08, 4, "square"), 9.5 + k * 0.125, 0.3)
# 甩镜 whoosh
for t0 in (9.8, 11.75, 13.75, 15.75, 17.75, 19.75, 23.0, 27.1):
    add(noise_sweep(0.35, 500, 7000, 0.55), t0)
# 工位音效
for a, b in ((10.1, 11.8), (12.15, 13.8)):
    d = b - a
    tn = tt(d)
    grind = filt(rng.standard_normal(len(tn)), "band", [2500, 9000]) * (0.6 + 0.4 * np.sin(2 * np.pi * 16 * tn) ** 2)
    add(grind * np.minimum(1, tn / 0.05) * np.minimum(1, (d - tn) / 0.1), a, 0.12, 0.3)
tn = tt(0.8)
crackle = filt(rng.standard_normal(len(tn)), "high", 3000) * (rng.random(len(tn)) > 0.97)
add(crackle, 14.5, 0.6, -0.2)
add(tone(3136, 0.6, 5) + tone(4186, 0.6, 7), 15.35, 0.25)
add(tone(2637, 0.9, 4) + tone(3951, 0.9, 5), 17.0, 0.35)
add(slide(3000, 800, 0.3, 0.25, 40), 18.05)
add(kick(0.8), 19.0)
add(filt(rng.standard_normal(int(0.1 * SR)), "band", [800, 2000]) * np.exp(-tt(0.1) * 40), 19.0, 0.6)

# 20.0 唱片急停 → 悬念 → 老板偷喝
ts = tt(0.4)
scratch = filt(rng.standard_normal(len(ts)), "band", [400, 3000]) * np.abs(np.sin(2 * np.pi * 7 * ts)) * np.exp(-ts * 5)
add(scratch + slide(700, 120, 0.4, 0.4, 3), 20.0, 0.8)
for i in range(6):
    add(filt(tone(1100 if i % 2 == 0 else 800, 0.08, 40), "band", [500, 3000]), 20.5 + i * BEAT, 0.5, 0.2)
for i, m in enumerate([57, 60, 64, 69, 64, 60]):
    add(filt(tone(hz(m), 0.3, 12), "low", 2000), 20.5 + i * BEAT + 0.25, 0.35, -0.2)
add(tone(1760, 0.4, 12) + tone(2640, 0.4, 14), 20.8, 0.3)
ts = tt(0.32)
slurp = filt(rng.standard_normal(len(ts)), "band", [600, 1800]) * (0.5 + 0.5 * np.sin(2 * np.pi * 18 * ts)) * np.minimum(1, ts / 0.04)
add(slurp, 22.15, 0.6)
add(boing(), 22.5, 0.9)
add(noise_sweep(0.5, 800, 9000, 0.6), 22.5)

# 数据段：计数滴答、落点、标签
for i in range(18):
    add(tone(1500 + i * 60, 0.05, 50), 24.5 + i * 0.05, 0.18)
PENTA = [69, 72, 74, 76, 79, 81, 84, 86, 88]
for i in range(22):
    add(tone(hz(PENTA[i % 9] + 12 * (i // 9 % 2)), 0.15, 18), 24.9 + i * 0.1 + 0.3, 0.12, (i % 3 - 1) * 0.5)
for t0 in (25.5, 26.0):
    add(stab(CH[2], 0.35), t0, 1.6)
for i in range(6):
    add(tone(hz(PENTA[i + 2]), 0.12, 20), 26.5 + i / 12, 0.2)
add(noise_sweep(0.78, 300, 10000, 0.7), 27.1)

# 片尾：C 大三和弦长音 + 三下点名 + 眨眼叮
t_end = tt(2.0)
final = sum(saw(hz(m), t_end, d) for m in (48, 60, 64, 67, 72) for d in (-0.004, 0.004))
add(filt(final, "low", 3000) * np.exp(-t_end * 1.2) * 0.1, 28.0)
for k, t0 in enumerate((28.5, 28.75, 29.0)):
    add(pluck(76 + [0, 3, 5][k], 0.2), t0, 1.0)
add(tone(3520, 0.8, 5) + tone(5274, 0.8, 7), 29.1, 0.25)
add(stab([60, 64, 67, 72], 0.5), 29.5, 1.8)
add(kick(1.0), 29.5)

# 7.875–8.0 与 27.875–28.0 留白，制造冲击
for a, b in ((7.875, 8.0), (27.875, 28.0)):
    i0, i1 = int(a * SR), int(b * SR)
    L[i0:i1] *= 0.05
    R[i0:i1] *= 0.05

# 母带：柔性限幅 + 尾部淡出
fade = np.ones(N)
fn = int(0.35 * SR)
fade[-fn:] = np.linspace(1, 0, fn)
mix = np.stack([L, R], 1) * fade[:, None]
mix = np.tanh(mix * 1.6 / np.max(np.abs(mix))) * 0.95
pcm = (mix * 32767).astype(np.int16)
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote", sys.argv[1], pcm.shape)
