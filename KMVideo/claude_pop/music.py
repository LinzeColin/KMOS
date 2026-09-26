#!/usr/bin/env python3
"""窑宝咯噔了 · 46 秒原创配乐 + 音效合成器（120 BPM，F 大调 / 噩梦段 D 小调）。

全部声音由 numpy/scipy 代码实时合成：没有采样、没有第三方音源、没有现成旋律，
可在抖音 / X / Instagram / Facebook 商用发布。

时间唯一来源：同目录 cues.js（严格 JSON 部分）。改 cues.js 里的时间，音效与编曲节点一起移动。

用法：python3 music.py OUT.wav [--stems DIR]
输出：44.1 kHz / 立体声 / 16-bit / 恰好 46.0 s，集成响度约 -14 LUFS，真峰值 ≤ -1 dBTP。
确定性：所有随机源都用固定种子。

乐器：Karplus-Strong 尤克里里（真实 GCEA 把位、上下扫弦、闷音掐断）、正弦+三角大号贝斯（起音微降调）、
口哨主旋律（连续相位、滑音、延迟颤音、气声）、钢片琴、拨奏弦乐、铜管齐奏（锯齿堆叠 + 滤波包络）、
锯齿 pad、底鼓 / 拍手 / 军鼓 / 808 式金属镲 / 沙锤 / 铃鼓 / 通鼓 / 吊镲；
合成卷积混响（频率相关衰减的噪声脉冲响应）、底鼓侧链压缩、音效闪避、总线压缩、4x 过采样真峰值限幅、
自带 ITU-R BS.1770 响度计把整体推到 -14 LUFS。
"""
import argparse
import json
import os
import sys

import numpy as np
from scipy.io import wavfile
from scipy.ndimage import maximum_filter1d, minimum_filter1d, uniform_filter1d
from scipy.signal import butter, lfilter, oaconvolve, resample_poly, sosfilt

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 44100


# ============================================================ cues
def load_cues(path=os.path.join(HERE, "cues.js")):
    s = open(path, encoding="utf-8").read()
    body = s[s.index("const CUE = ") + len("const CUE = "):]
    obj, _ = json.JSONDecoder().raw_decode(body)
    return obj


CUE = load_cues()
BPM = float(CUE["bpm"])
BEAT = 60.0 / BPM
BAR = 4 * BEAT
E8 = BEAT / 2          # 8th note
S16 = BEAT / 4         # 16th note
DUR = float(CUE["dur"])
SEC = {s["name"]: (float(s["t0"]), float(s["t1"])) for s in CUE["sections"]}
EV = {k: float(v) for k, v in CUE["ev"].items()}


def T(t):
    """seconds -> sample index (sample-accurate grid)."""
    return int(round(t * SR))


N = T(DUR)
rng = np.random.default_rng(20260926)


def tt(d):
    return np.arange(max(1, T(d))) / SR


def hz(m):
    return 440.0 * 2.0 ** ((np.asarray(m, dtype=float) - 69.0) / 12.0)


def noise(n):
    return rng.standard_normal(n)


# ============================================================ DSP helpers
def filt(x, kind, f, order=2):
    w = np.asarray(f, dtype=float) / (SR / 2)
    w = np.clip(w, 1e-4, 0.999)
    sos = butter(order, w if w.ndim else float(w), btype=kind, output="sos")
    return sosfilt(sos, x, axis=-1)


def _biquad(kind, f, q):
    f = min(max(float(f), 15.0), SR * 0.45)
    w0 = 2 * np.pi * f / SR
    cw, sw = np.cos(w0), np.sin(w0)
    al = sw / (2 * q)
    if kind == "low":
        b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]
    elif kind == "high":
        b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]
    else:  # band, 0 dB peak
        b = [al, 0.0, -al]
    a = [1 + al, -2 * cw, 1 - al]
    return np.array(b) / a[0], np.array(a) / a[0]


def bpf(x, f, q=4.0):
    b, a = _biquad("band", f, q)
    return lfilter(b, a, x, axis=-1)


def tvf(x, fc, kind="low", q=0.707, blk=64):
    """time-varying biquad (per-block coefficients, carried state)."""
    fc = np.broadcast_to(np.asarray(fc, dtype=float), x.shape)
    y = np.empty_like(x)
    zi = np.zeros(2)
    for i in range(0, len(x), blk):
        b, a = _biquad(kind, fc[min(i + blk // 2, len(x) - 1)], q)
        y[i:i + blk], zi = lfilter(b, a, x[i:i + blk], zi=zi)
    return y


def env_ad(t, a, d):
    return np.minimum(t / max(a, 1e-5), 1.0) * np.exp(-np.maximum(t - a, 0) / d)


def fade(x, fin=0.002, fout=0.01):
    x = np.array(x, dtype=float)
    n = x.shape[-1]
    i, o = min(n, max(1, T(fin))), min(n, max(1, T(fout)))
    x[..., :i] *= np.linspace(0, 1, i)
    x[..., n - o:] *= np.linspace(1, 0, o)
    return x


def phase(f):
    return 2 * np.pi * np.cumsum(np.broadcast_to(f, np.shape(f))) / SR


def saw_blep(f):
    f = np.asarray(f, dtype=float)
    dt = f / SR
    ph = np.cumsum(dt) % 1.0
    s = 2 * ph - 1
    m = ph < dt
    x = ph[m] / dt[m]
    s[m] -= x + x - x * x - 1
    m = ph > 1 - dt
    x = (ph[m] - 1) / dt[m]
    s[m] -= x * x + x + x + 1
    return s


def tri(ph):
    return 2 / np.pi * np.arcsin(np.sin(ph))


def pan_gains(p):
    th = (np.clip(p, -1, 1) + 1) * np.pi / 4
    return np.cos(th) * np.sqrt(2), np.sin(th) * np.sqrt(2)


def stereo(x, pan=0.0):
    x = np.asarray(x, dtype=float)
    if x.ndim == 2:
        return x
    gl, gr = pan_gains(pan)
    return np.vstack([x * gl, x * gr])


def pan_move(x, p0, p1):
    p = np.linspace(p0, p1, len(x))
    gl, gr = pan_gains(p)
    return np.vstack([x * gl, x * gr])


def norm(x, peak=1.0):
    m = np.max(np.abs(x))
    return x * (peak / m) if m > 0 else x


# ============================================================ buses
BUSES = ["drums", "bass", "keys", "lead", "sfx"]
B = {k: np.zeros((2, N)) for k in BUSES}
SEND = {"music": np.zeros((2, N)), "sfx": np.zeros((2, N))}
KICKS = []  # four-on-the-floor kicks that drive the sidechain


def add(bus, sig, t, g=1.0, pan=0.0, rev=0.0):
    st = stereo(sig, pan) * g
    i = T(t)
    if i < 0:
        st, i = st[:, -i:], 0
    n = min(st.shape[1], N - i)
    if n <= 0:
        return
    B[bus][:, i:i + n] += st[:, :n]
    if rev:
        SEND["sfx" if bus == "sfx" else "music"][:, i:i + n] += st[:, :n] * rev


# ============================================================ instruments
_KS = {}


def ks_string(m, dur, t60=1.0, bright=0.6, var=0):
    """Karplus-Strong plucked string with allpass fine tuning (one lfilter call)."""
    key = (round(float(m), 3), T(dur), round(t60, 3), round(bright, 2), var)
    if key in _KS:
        return _KS[key]
    f = float(hz(m))
    n = T(dur)
    pt = SR / f - 0.5
    P = int(np.floor(pt - 0.1))
    d = pt - P
    c = (1 - d) / (1 + d)
    g = 10 ** (-3.0 / (f * t60))
    r = np.random.default_rng(int(m * 100) * 7 + var)
    ex = r.standard_normal(P)
    ex = lfilter([bright], [1, -(1 - bright)], ex)
    ex -= ex.mean()
    k = max(1, int(0.13 * P))
    ex = ex - 0.7 * np.concatenate([np.zeros(k), ex[:-k]])
    x = np.zeros(n)
    x[:min(P, n)] = ex[:min(P, n)]
    a = np.zeros(P + 3)
    a[0] = 1.0
    a[1] += c
    a[P] += -g * 0.5 * c
    a[P + 1] += -g * 0.5 * (1 + c)
    a[P + 2] += -g * 0.5
    y = lfilter([1.0, c], a, x)
    y = fade(norm(y), 0.0005, 0.008)
    _KS[key] = y
    return y


UKE = {  # re-entrant GCEA voicings (strings G4 C4 E4 A4)
    "F": [69, 60, 65, 69], "C": [67, 60, 64, 72], "Dm": [69, 62, 65, 69],
    "Bb": [70, 62, 65, 70], "Gm": [67, 62, 67, 70], "A": [69, 61, 64, 69],
    "C7": [67, 60, 64, 70], "CE": [67, 60, 64, 72],
}
ROOT = {"F": 41, "C": 36, "CE": 40, "Dm": 38, "Bb": 34, "Gm": 31, "A": 33, "C7": 36}
BRASS = {"F": [65, 69, 72, 77], "C": [64, 67, 72, 76], "Dm": [62, 65, 69, 74],
         "Bb": [62, 65, 70, 74], "C7": [64, 67, 70, 76]}
PAD = {k: [m - 12 for m in v] for k, v in BRASS.items()}
PCS = {"F": {5, 9, 0}, "C": {0, 4, 7}, "Dm": {2, 5, 9}, "Bb": {10, 2, 5}}
SCALE_F = [5, 7, 9, 10, 0, 2, 4]
_strum_n = [0]


def uke_strum(ch, dur, down=True, vel=1.0, spread=0.011, t60=0.9, bright=0.55, strings=(0, 1, 2, 3)):
    notes = UKE[ch]
    order = list(strings) if down else list(strings)[::-1]
    n = T(dur)
    out = np.zeros((2, n))
    _strum_n[0] += 1
    for j, k in enumerate(order):
        off = T(j * spread * (1.0 + 0.2 * np.sin(_strum_n[0] * 1.7 + j)))
        if off >= n - 10:
            continue
        s = ks_string(notes[k], (n - off) / SR, t60, bright if down else bright + 0.1, var=_strum_n[0] % 3)
        amp = (0.85 + 0.15 * np.cos(_strum_n[0] * 2.3 + k)) * (1.0 if down else 0.7)
        gl, gr = pan_gains(-0.3 + 0.2 * k)
        out[0, off:] += s * amp * gl
        out[1, off:] += s * amp * gr
    body = bpf(out, 215, 1.0) * 0.4 + filt(out, "low", 6500)
    return fade(body * vel * 0.3, 0.0005, 0.012)


def tuba(m, dur, vel=1.0):
    t = tt(dur)
    semis = 0.45 * np.exp(-t / 0.035) - 0.3 * np.clip((t - (dur - 0.07)) / 0.07, 0, 1)
    f = hz(m) * 2 ** (semis / 12)
    ph = phase(f)
    x = np.sin(ph) + 0.35 * tri(ph) + 0.18 * np.sin(2 * ph + 0.4)
    blat = filt(saw_blep(f), "low", 1100) * np.exp(-t / 0.06) * 0.45
    env = np.minimum(t / 0.007, 1) * (0.65 + 0.35 * np.exp(-t / 0.09))
    return fade(np.tanh(1.2 * (x + blat)) * env * vel, 0.001, 0.03)


def pizz(m, dur=0.3, vel=1.0):
    return filt(ks_string(m, dur, t60=0.25, bright=0.35), "low", 2600) * vel


def glock(m, dur=1.4, vel=1.0):
    f = float(hz(m))
    t = tt(dur)
    y = np.zeros(len(t))
    for r, a, d in ((1, 1.0, 0.8), (2.76, 0.35, 0.22), (5.40, 0.14, 0.08), (8.93, 0.06, 0.04)):
        if f * r < SR * 0.45:
            y += a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d)
    y += filt(noise(len(t)), "high", 5000) * np.exp(-t / 0.0015) * 0.25
    return fade(y * vel, 0.0005, 0.02)


def whistle_line(notes, t0, t1, vib=0.0065, breath=0.05, bright=0.06):
    """notes: (t_on, dur, midi, vel). One continuous-phase whistle with glides, scoops, delayed vibrato."""
    n = T(t1) - T(t0)
    t = np.arange(n) / SR
    target = np.zeros(n)
    gate = np.zeros(n)
    since = np.full(n, 10.0)
    scoop = np.zeros(n)
    notes = sorted(notes)
    prev_f = float(hz(notes[0][2]))
    for k, (on, d, m, v) in enumerate(notes):
        s = T(on) - T(t0)
        e = s + T(d)
        nxt = T(notes[k + 1][0]) - T(t0) if k + 1 < len(notes) else n
        target[s:nxt] = float(hz(m))
        gate[s:e] = v
        since[s:nxt] = t[s:nxt] - t[s]
        rest_before = k == 0 or (on - (notes[k - 1][0] + notes[k - 1][1])) > 0.06
        if rest_before or d >= 0.45:
            scoop[s:nxt] = np.exp(-(t[s:nxt] - t[s]) / 0.035)
    first = np.argmax(target > 0)
    target[:first] = target[first]
    lf = np.log(target)
    a = 1 - np.exp(-1 / (0.022 * SR))
    lf = lfilter([a], [1, -(1 - a)], lf, zi=[lf[0] * (1 - a)])[0]
    vdep = vib * np.clip((since - 0.12) / 0.2, 0, 1)
    f = np.exp(lf) * (1 + vdep * np.sin(2 * np.pi * 5.6 * t)) * (1 - 0.07 * scoop)
    ph = phase(f)
    y = np.sin(ph) + bright * np.sin(2 * ph)
    ga = 1 - np.exp(-1 / (0.012 * SR))
    amp = lfilter([ga], [1, -(1 - ga)], gate)
    br = filt(noise(n), "band", [900, 5000]) * breath
    return (y + br) * amp


def whistle_echo(x):
    """dotted-8th ping-pong echo, darker each repeat."""
    d = T(3 * E8)
    out = stereo(x, 0.0)
    e1 = filt(x, "low", 3500) * 0.26
    e2 = filt(e1, "low", 2500) * 0.4
    L = np.zeros_like(x)
    R = np.zeros_like(x)
    L[d:] += e1[:-d]
    R[2 * d:] += e2[:-2 * d]
    out[0] += L
    out[1] += R
    return out


def brass(midis, dur, vel=1.0, bright=1.0, fall=False, vibr=False):
    t = tt(dur)
    x = np.zeros(len(t))
    semis = np.zeros(len(t))
    if fall:
        semis -= 3.0 * np.clip((t - (dur - 0.16)) / 0.16, 0, 1) ** 2
    if vibr:
        semis += 0.18 * np.clip((t - 0.18) / 0.2, 0, 1) * np.sin(2 * np.pi * 5.2 * t)
    for m in midis:
        for det in (-0.12, -0.04, 0.04, 0.12):
            x += saw_blep(hz(m + det) * 2 ** (semis / 12))
    x /= 4 * len(midis)
    fc = 350 + 5200 * bright * (0.65 * np.exp(-t / 0.10) + 0.35 * np.exp(-t / 0.7)) * np.minimum(t / 0.018, 1) ** 0.5
    y = tvf(x, fc, "low", 1.1)
    env = np.minimum(t / 0.006, 1) * (0.55 + 0.45 * np.exp(-t / 0.12))
    y = np.tanh(2.2 * y * env) * vel
    return fade(y, 0.001, 0.05)


def pad(ch, dur, cut=1100):
    t = tt(dur)
    out = np.zeros((2, len(t)))
    for c, sgn in ((0, -1), (1, 1)):
        x = np.zeros(len(t))
        for m in PAD[ch]:
            for det in (0.0, 0.09 * sgn):
                x += saw_blep(np.full(len(t), hz(m + det)))
        out[c] = filt(x, "low", cut) / len(PAD[ch])
    e = np.minimum(t / 0.08, 1) * np.minimum((dur - t) / 0.12, 1)
    return out * np.clip(e, 0, 1)


# ---------------------------------------------------------------- drums
def kick(g=1.0, d=0.42):
    t = tt(d)
    f = 48 + 120 * np.exp(-t * 32)
    body = np.sin(phase(f)) * np.exp(-t / 0.16)
    click = filt(noise(len(t)), "high", 2500) * np.exp(-t / 0.004) * 0.35
    return fade(np.tanh(1.6 * (body + click)) * g, 0.0003, 0.02)


def clap(g=1.0):
    t = tt(0.3)
    nz = filt(noise(len(t)), "band", [900, 3200])
    e = np.zeros(len(t))
    for o in (0.0, 0.009, 0.018):
        e += (t >= o) * np.exp(-np.maximum(t - o, 0) / 0.006) * 0.7
    e += (t >= 0.026) * np.exp(-np.maximum(t - 0.026, 0) / 0.07)
    return nz * e * g * 0.6


def snare(g=1.0):
    t = tt(0.25)
    tone = (np.sin(phase(185 + 40 * np.exp(-t * 60))) * 0.6 + np.sin(2 * np.pi * 330 * t) * 0.25) * np.exp(-t / 0.05)
    nz = filt(noise(len(t)), "band", [1500, 9000]) * np.exp(-t / 0.09)
    return fade((tone + nz) * g * 0.8, 0.0003, 0.01)


HATF = np.array([205.3, 304.4, 369.6, 522.7, 540.0, 800.0]) * 2.1


def hat(open_=False, g=1.0):
    d = 0.35 if open_ else 0.07
    t = tt(d)
    met = sum(np.sign(np.sin(2 * np.pi * f * t + i)) for i, f in enumerate(HATF))
    x = filt(met * 0.6 + noise(len(t)), "high", 7500)
    return fade(x * np.exp(-t / (0.11 if open_ else 0.018)) * g * 0.3, 0.0003, 0.01)


def shaker(g=1.0):
    t = tt(0.09)
    x = filt(noise(len(t)), "band", [4500, 11000])
    return x * np.minimum(t / 0.012, 1) * np.exp(-t / 0.03) * g * 0.35


def tamb(g=1.0):
    t = tt(0.16)
    jing = sum(np.sin(2 * np.pi * f * t) for f in (5100, 6300, 7400, 8900)) * 0.2
    x = filt(noise(len(t)) + jing, "high", 5500)
    return x * np.exp(-t / 0.045) * g * 0.35


def tom(f0, g=1.0):
    t = tt(0.35)
    x = np.sin(phase(f0 * (1 + 0.6 * np.exp(-t * 25)))) * np.exp(-t / 0.13)
    x += filt(noise(len(t)), "band", [300, 3000]) * np.exp(-t / 0.02) * 0.3
    return fade(x * g, 0.0003, 0.02)


def crash(g=1.0, d=2.2):
    t = tt(d)
    out = np.zeros((2, len(t)))
    fs = np.array([327, 473, 591, 787, 1123, 1377, 1680, 2210])
    for c in (0, 1):
        met = sum(np.sign(np.sin(2 * np.pi * f * (1 + 0.013 * c) * t + i)) for i, f in enumerate(fs))
        x = filt(noise(len(t)) + 0.3 * met, "high", 4200)
        out[c] = x * (0.25 * np.exp(-t / 0.05) + np.exp(-t / 0.55)) * g * 0.28
    return fade(out, 0.0003, 0.2)


def place_kick(t, g=1.0, sc=True):
    add("drums", kick(g), t)
    if sc:
        KICKS.append(t)


# ============================================================ SFX
def s_shimmer(p=1.0):
    d = 1.4
    out = np.zeros((2, T(d)))
    for i, m in enumerate([77, 81, 84, 89, 93, 96, 101]):
        s = stereo(glock(m, d - i * 0.07, 0.7 + 0.05 * i), -0.6 + 0.2 * i)
        o = T(i * 0.07)
        out[:, o:o + s.shape[1]] += s
    t = tt(d)
    air = filt(noise(len(t)), "high", 7000) * np.sin(np.pi * np.clip(t / 0.9, 0, 1)) * 0.12
    return out + stereo(air)


def s_creak(p=1.0):
    d = 0.38
    t = tt(d)
    n = len(t)
    jit = filt(noise(n), "low", 30)
    jit /= np.abs(jit).max() + 1e-9
    f = (220 + 190 * np.sin(np.pi * t / d) ** 0.7 + 35 * jit) * p
    fr = (np.cumsum(f) / SR) % 1.0
    src = np.exp(-fr * 7.0) - 0.28
    stick = 0.55 + 0.45 * (filt(noise(n), "low", 45) > -0.1)
    y = bpf(src, 700, 6) + 0.8 * bpf(src, 1450, 7) + 0.55 * bpf(src, 2600, 8) + 0.1 * src
    return fade(y * stick * np.minimum(t / 0.03, 1), 0.001, 0.07)


def _clank(t, parts, dmul=1.0):
    y = np.zeros(len(t))
    for i, (f, a) in enumerate(parts):
        y += a * np.sin(2 * np.pi * f * t + i * 1.3) * np.exp(-t / (dmul * 0.9 / (8 + f / 180)))
    return y


def s_clunk(p=1.0, big=False):
    d = 1.1 if big else 0.7
    t = tt(d)
    f0 = 44 if big else 58
    thump = np.sin(phase(f0 + 90 * np.exp(-t * 26))) * np.exp(-t / (0.22 if big else 0.13))
    thump += 0.5 * np.sin(phase(2 * f0 + 120 * np.exp(-t * 30))) * np.exp(-t / 0.08)
    parts = [(410, 1.0), (938, 0.8), (1523, 0.55), (2215, 0.35), (3180, 0.2)]
    if big:
        parts = [(f * 0.78, a) for f, a in parts] + [(305, 1.0)]
    clank = _clank(t, parts, 1.4 if big else 1.0)
    tr = filt(noise(len(t)), "band", [700, 5000]) * np.exp(-t / 0.008)
    y = 1.1 * thump + 0.45 * clank + 0.5 * tr
    reb = T(0.085 if not big else 0.11)          # the "咯" rebound knock
    rb = (0.35 * _clank(t, [(f * 1.18, a) for f, a in parts[:4]], 0.5) + 0.3 * tr) * (0.7 if big else 1)
    y[reb:] += rb[:len(y) - reb]
    if big:
        rat = np.zeros(len(t))
        for k in range(7):
            o = T(0.18 + k * 0.055)
            g = _clank(t, [(1830 + 210 * k, 1), (2710, 0.5)], 0.25) * 0.25 * (1 - k / 8)
            rat[o:] += g[:len(t) - o]
        y += rat
    return fade(np.tanh(1.3 * y), 0.0003, 0.08)


def s_clunkbig(p=1.0):
    return s_clunk(p, big=True)


def s_boing(p=1.0, up=False, d=0.6):
    t = tt(d)
    base = 170 * p
    rise = 1 + 0.55 * (1 - np.exp(-t * 28))
    wob = 1 + 0.22 * np.exp(-t * 4.5) * np.sin(2 * np.pi * 12.5 * t)
    climb = 2 ** (1.1 * t / d) if up else 1.0
    f = base * rise * wob * climb
    x = np.tanh(2.2 * np.sin(phase(f)))
    x = tvf(x, 900 + 2500 * np.exp(-t * 5), "low", 2.5)
    return fade(x * np.minimum(t / 0.004, 1) * np.exp(-t / 0.22), 0.0005, 0.06)


def s_boingup(p=1.0):
    return s_boing(1.25 * p, up=True, d=0.55)


def s_whistle_glide(f0, f1, d, vib=0.015, curve=1.0):
    t = tt(d)
    u = (t / d) ** curve
    f = f0 * (f1 / f0) ** u * (1 + vib * np.sin(2 * np.pi * 6.2 * t))
    y = np.sin(phase(f)) + 0.08 * np.sin(2 * phase(f)) + filt(noise(len(t)), "band", [1000, 6000]) * 0.05
    return y


def s_slideup(p=1.0):
    d = 0.42
    t = tt(d)
    y = s_whistle_glide(420 * p, 1700 * p, d, 0.02, 0.8)
    return fade(y * np.minimum(t / 0.03, 1) * np.minimum((d - t) / 0.06, 1), 0.001, 0.02)


def s_splat(p=1.0):
    d = 0.45
    t = tt(d)
    thud = np.sin(phase(50 + 70 * np.exp(-t * 30))) * np.exp(-t / 0.06)
    sq = tvf(noise(len(t)), 2800 * np.exp(-t * 7) + 250, "low", 1.8) * np.exp(-t / 0.11)
    y = 0.9 * thud + 0.9 * sq
    for o, f in ((0.02, 900), (0.06, 650), (0.11, 520), (0.17, 380)):
        i = T(o)
        tb = tt(0.06)
        b = np.sin(phase(f * (1 - 0.5 * tb / 0.06))) * np.sin(np.pi * tb / 0.06) * 0.45
        y[i:i + len(b)] += b[:len(y) - i]
    return fade(y, 0.0003, 0.05)


def s_pop(p=1.0):
    t = tt(0.14)
    f = (320 + 1300 * (1 - np.exp(-t * 70))) * p
    y = np.sin(phase(f)) * np.exp(-t / 0.035)
    y += filt(noise(len(t)), "high", 2000) * np.exp(-t / 0.002) * 0.5
    return fade(y, 0.0002, 0.02)


def _whoosh(d, fc, env, p0=-0.6, p1=0.6, q=1.2):
    t = tt(d)
    x = tvf(noise(len(t)), fc(t), "band", q) * env(t)
    x += tvf(noise(len(t)), fc(t) * 1.9, "band", q * 1.5) * env(t) * 0.4
    return fade(pan_move(x, p0, p1), 0.002, 0.03)


def s_whooshin(p=1.0):
    d = 0.7
    return _whoosh(d, lambda t: 350 * (8 ** np.sin(np.pi * t / d)), lambda t: np.sin(np.pi * t / d) ** 2, -0.7, 0.7)


def s_whooshup(p=1.0):
    d = 0.95
    return _whoosh(d, lambda t: 300 * 25 ** (t / d), lambda t: (t / d) ** 1.5 * np.minimum((d - t) / 0.08, 1), 0.0, 0.0)


def s_whooshdown(p=1.0):
    d = 0.75
    return _whoosh(d, lambda t: 5500 * (1 / 18) ** (t / d), lambda t: np.minimum(t / 0.12, 1) * np.exp(-np.maximum(t - 0.12, 0) / 0.2), 0.5, -0.5)


def s_whip(p=1.0):
    d = 0.22
    out = _whoosh(d, lambda t: 7000 * (1 / 7) ** (t / d), lambda t: np.minimum(t / 0.03, 1) * np.exp(-np.maximum(t - 0.03, 0) / 0.05), -0.8, 0.8, 1.6)
    t = tt(d)
    crack = filt(noise(len(t)), "high", 2500) * np.exp(-np.maximum(t - 0.035, 0) / 0.004) * (t > 0.035) * 0.6
    return out + stereo(crack, 0.3)


def s_crane(p=1.0):
    d = 1.1
    t = tt(d)
    y = np.zeros(len(t))
    c = s_clunk(1.0)
    y[:len(c)] += c[:len(t)] * 0.8
    for k in range(38):
        o = T(0.05 + rng.random() * 0.95)
        f = 1900 + rng.random() * 3200
        tg = tt(0.05)
        g = (np.sin(2 * np.pi * f * tg) + 0.6 * np.sin(2 * np.pi * f * 1.47 * tg)) * np.exp(-tg / 0.012)
        y[o:o + len(g)] += g[:len(y) - o] * (0.25 + 0.3 * rng.random())
    mot = filt(saw_blep(np.full(len(t), 95.0)), "low", 600) * (0.5 + 0.5 * (np.sin(2 * np.pi * 13 * t) > 0.6))
    y += mot * 0.15 * np.minimum(t / 0.2, 1)
    return fade(y, 0.0003, 0.1)


def s_squash(p=1.0):
    d = 0.8
    t = tt(d)
    y = np.sin(phase(40 + 90 * np.exp(-t * 18))) * np.exp(-t / 0.18) * 1.2
    for k in range(45):
        o = T(rng.random() ** 1.6 * 0.3)
        tg = tt(0.02)
        g = filt(noise(len(tg)), "band", [700 + 2500 * rng.random(), 6000]) * np.exp(-tg / 0.005)
        y[o:o + len(g)] += g[:len(y) - o] * 0.5 * (1 - o / len(y))
    crumple = _clank(t, [(260, 1), (590, 0.8), (870, 0.6), (1340, 0.4)], 1.6)
    crumple *= 1 - 0.3 * t
    y += 0.45 * crumple
    sq = tvf(noise(len(t)), 1800 * np.exp(-t * 6) + 200, "low", 3.0) * np.exp(-t / 0.15) * 0.8
    y += sq
    return fade(np.tanh(1.4 * y), 0.0003, 0.1)


def s_riffle(p=1.0):
    d = 0.65
    y = np.zeros(T(d))
    tt_ = 0.0
    k = 0
    while tt_ < d - 0.04:
        tg = tt(0.03)
        g = filt(noise(len(tg)), "band", [1400, 7500]) * np.sin(np.pi * tg / 0.03) ** 2
        g += np.sin(2 * np.pi * 320 * tg) * np.sin(np.pi * tg / 0.03) * 0.15
        o = T(tt_)
        y[o:o + len(g)] += g[:len(y) - o] * (0.7 + 0.3 * (k % 2))
        tt_ += 0.048 - 0.012 * (tt_ / d)
        k += 1
    return fade(pan_move(y, -0.4, 0.4), 0.001, 0.03)


def s_coins(p=1.0):
    d = 1.3
    out = np.zeros((2, T(d)))
    tg = tt(0.7)
    bell = (np.sin(2 * np.pi * 1320 * tg) + 0.6 * np.sin(2 * np.pi * 1980 * tg)) * np.exp(-tg / 0.18)
    out += np.pad(stereo(bell * 0.5, 0.0), ((0, 0), (0, out.shape[1] - len(tg))))
    for i, (o, f) in enumerate(((0.05, 2637), (0.15, 3136), (0.26, 2794), (0.38, 3520), (0.5, 2960))):
        fd = f * (1 - 0.01 * i)
        c = (np.sin(2 * np.pi * fd * tg) + 0.5 * np.sin(2 * np.pi * fd * 2.32 * tg)
             + 0.25 * np.sin(2 * np.pi * fd * 4.25 * tg)) * np.exp(-tg / 0.14)
        s = stereo(c * (1 - 0.13 * i), -0.2 + 0.25 * i)
        j = T(o)
        out[:, j:j + s.shape[1]] += s[:, :out.shape[1] - j]
    return fade(out, 0.0003, 0.05)


def s_sadtrombone(p=1.0):
    notes = [(0.0, 0.17, 58), (0.19, 0.17, 57), (0.38, 0.17, 56), (0.57, 0.8, 55)]
    d = 1.4
    y = np.zeros(T(d))
    for k, (o, dur, m) in enumerate(notes):
        t = tt(dur)
        last = k == 3
        semis = (0.35 * np.sin(2 * np.pi * 6 * t) * np.clip((t - 0.1) / 0.1, 0, 1) - 0.8 * (t / dur) ** 2) if last else -0.15 * t / dur
        f = hz(m) * 2 ** (semis / 12)
        src = saw_blep(f)
        wah = 380 + 1300 * (np.minimum(t / 0.09, 1) if not last else (0.55 + 0.45 * np.sin(2 * np.pi * 3 * t - np.pi / 2)))
        x = tvf(src, wah, "low", 2.2)
        env = np.minimum(t / 0.02, 1) * np.minimum((dur - t) / 0.04, 1)
        if last:
            env *= np.exp(-t / 0.9)
        i = T(o)
        y[i:i + len(x)] += np.tanh(1.8 * x) * env
    return fade(filt(y, "high", 90), 0.001, 0.05)


def s_fallwhistle(p=1.0):
    d = 1.0
    t = tt(d)
    y = s_whistle_glide(2600, 520, d, 0.006, 1.25)
    env = (0.3 + 0.7 * (t / d) ** 1.5) * np.minimum(t / 0.05, 1)
    return fade(y * env, 0.001, 0.012)


def s_impact(p=1.0):
    d = 2.0
    t = tt(d)
    boom = np.sin(phase(36 + 100 * np.exp(-t * 12))) * np.exp(-t / 0.45)
    crack = filt(noise(len(t)), "band", [180, 3000]) * np.exp(-t / 0.03)
    wood = _clank(t, [(180, 1), (420, 0.7), (760, 0.5)], 0.8)
    y = stereo(np.tanh(1.5 * (1.3 * boom + 0.9 * crack + 0.4 * wood)))
    y += crash(1.3, d)
    for k in range(10):
        o = T(0.08 + 0.5 * rng.random())
        tg = tt(0.04)
        g = bpf(noise(len(tg)), 600 + 1500 * rng.random(), 5) * np.exp(-tg / 0.01) * 0.3
        s = stereo(g, rng.uniform(-0.8, 0.8))
        y[:, o:o + s.shape[1]] += s[:, :y.shape[1] - o]
    return fade(y, 0.0003, 0.2)


def s_rattle(p=1.0):
    d = 2.0
    y = np.zeros((2, T(d)))
    tcur, k = 0.0, 0
    while True:
        rate = 5.0 * 4.6 ** (tcur / d)
        tcur += 1.0 / rate
        if tcur > d - 0.03:
            break
        tg = tt(0.06)
        f1 = 300 + 60 * (k % 3)
        g = (np.sin(2 * np.pi * f1 * tg) + 0.6 * np.sin(2 * np.pi * 2.3 * f1 * tg)) * np.exp(-tg / 0.012)
        g += bpf(noise(len(tg)), 1200, 2) * np.exp(-tg / 0.004) * 0.8
        s = stereo(g * (0.4 + 0.6 * tcur / d), 0.3 if k % 2 else -0.3)
        o = T(tcur)
        y[:, o:o + s.shape[1]] += s[:, :y.shape[1] - o]
        k += 1
    return fade(y, 0.001, 0.01)


def s_peek(p=1.0):
    y = np.zeros(T(0.3))
    for o, sc in ((0.0, 1.0), (0.1, 1.35)):
        t = tt(0.13)
        f = (480 + 600 * np.sin(np.pi * np.minimum(t / 0.09, 1) * 0.5)) * sc
        b = np.sin(phase(f)) * np.minimum(t / 0.004, 1) * np.exp(-t / 0.04) * (1.0 if o == 0 else 0.55)
        i = T(o)
        y[i:i + len(b)] += b
    return fade(y, 0.0003, 0.02)


def s_burst(p=1.0):
    d = 1.4
    t = tt(d)
    out = stereo(s_pop(0.7), 0) * 0.9
    out = np.pad(out, ((0, 0), (0, T(d) - out.shape[1])))
    boom = np.sin(phase(45 + 150 * np.exp(-t * 20))) * np.exp(-t / 0.18)
    out += stereo(boom * 0.8)
    pent = [89, 91, 93, 96, 98, 101, 103, 105]
    for k in range(12):
        o = T(0.03 + k * 0.045)
        s = stereo(glock(pent[(k * 5) % 8], 0.7, 0.45), rng.uniform(-0.8, 0.8))
        out[:, o:o + s.shape[1]] += s[:, :out.shape[1] - o]
    conf = np.zeros((2, len(t)))
    for k in range(260):
        o = int(len(t) * rng.random() ** 1.8)
        tg = tt(0.006)
        g = filt(noise(len(tg)), "high", 4000) * np.exp(-tg / 0.0015)
        s = stereo(g * (1 - o / len(t)), rng.uniform(-1, 1))
        conf[:, o:o + s.shape[1]] += s[:, :len(t) - o]
    return fade(out + conf * 0.6, 0.0003, 0.1)


def s_jump(p=1.0):
    d = 0.17
    t = tt(d)
    f = 330 * 4 ** (t / d)
    y = np.sin(phase(f)) + 0.2 * np.sign(np.sin(phase(f)))
    return fade(filt(y, "low", 4000) * np.minimum(t / 0.01, 1), 0.0005, 0.03)


def s_landboing(p=1.0):
    t = tt(0.2)
    th = np.sin(phase(55 + 60 * np.exp(-t * 30))) * np.exp(-t / 0.06)
    b = s_boing(0.85, d=0.55) * 0.8
    b[:len(th)] += th
    return b


def s_patter(p=1.0):
    d = 1.05
    y = np.zeros((2, T(d)))
    for k in range(13):
        tg = tt(0.05)
        g = filt(noise(len(tg)), "low", 1600) * np.exp(-tg / 0.008)
        g += np.sin(2 * np.pi * (230 if k % 2 else 270) * tg) * np.exp(-tg / 0.015) * 0.8
        s = stereo(g * (0.8 + 0.2 * (k % 2)), -0.25 if k % 2 else 0.25)
        o = T(k * 0.08)
        y[:, o:o + s.shape[1]] += s[:, :y.shape[1] - o]
    return y


def s_clickmag(p=1.0):
    t = tt(0.25)
    y = filt(noise(len(t)), "high", 3000) * np.exp(-t / 0.0015)
    y += np.sin(2 * np.pi * 160 * t) * np.exp(-t / 0.02) * 0.8
    y += (np.sin(2 * np.pi * 4200 * t) + 0.5 * np.sin(2 * np.pi * 6150 * t)) * np.exp(-t / 0.035) * 0.35
    return fade(y, 0.0002, 0.02)


def s_wobble(p=1.0):
    d = 1.1
    t = tt(d)
    f = 520 * (1 + 0.13 * np.exp(-t * 2.2) * np.sin(2 * np.pi * 7 * t))
    x = filt(np.tanh(1.8 * np.sin(phase(f))), "low", 2500)
    a = np.exp(-t / 0.4) * (0.55 + 0.45 * np.abs(np.sin(2 * np.pi * 3.5 * t + 0.4)))
    return fade(x * a * np.minimum(t / 0.005, 1), 0.0005, 0.05)


def bell(f, d=1.4, bright=1.0):
    t = tt(d)
    y = np.zeros(len(t))
    for r, a, dc in ((1, 1, 0.6), (2.0, 0.5 * bright, 0.35), (3.0, 0.25 * bright, 0.2), (4.2, 0.2 * bright, 0.12), (5.4, 0.12 * bright, 0.08)):
        if f * r < SR * 0.45:
            y += a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / dc)
    return fade(y * np.minimum(t / 0.0008, 1), 0.0002, 0.05)


def s_ding(p=1.0):
    y = bell(1568 * p, 1.5)
    y[:T(1.0)] += 0.4 * bell(2349 * p, 1.0)
    return y


def s_rollin(p=1.0):
    d = 0.55
    t = tt(d)
    rum = filt(noise(len(t)), "low", 500) * 1.2
    seam = (np.sin(2 * np.pi * 17 * t) > 0.85) * filt(noise(len(t)), "band", [800, 3000]) * 0.8
    whine = np.sin(phase(180 + 60 * t / d)) * 0.25
    y = (rum + seam + whine) * np.minimum(t / 0.25, 1) * np.minimum((d - t) / 0.06, 1)
    return fade(pan_move(y, -0.8, 0.1), 0.001, 0.02)


def s_cut(p=1.0):
    d = 0.42
    t = tt(d)
    fz = 900 * (1 - 0.15 * t / d) * (1 + 0.08 * np.sin(2 * np.pi * 110 * t))
    zap = filt(saw_blep(fz), "band", [700, 6000]) * 0.7
    hiss = filt(noise(len(t)), "high", 4500) * 0.5
    crk = filt(noise(len(t)) * (rng.random(len(t)) > 0.985), "high", 2500) * 2.0
    env = np.minimum(t / 0.006, 1) * np.exp(-t / 0.2)
    y = (zap + hiss) * env + crk * np.exp(-t / 0.3)
    return fade(pan_move(y, 0.35, 0.55), 0.0003, 0.04)


def s_sproing(p=1.0):
    b = s_boing(1.7, up=True, d=0.6)
    t = tt(0.6)
    tw = np.sin(phase(1150 * (1 + 0.1 * np.sin(2 * np.pi * 15 * t)))) * np.exp(-t / 0.15) * 0.3
    return b + tw[:len(b)]


def s_gleam(p=1.0):
    d = 0.6
    t = tt(d)
    shing = filt(noise(len(t)), "band", [6500, 15000]) * np.sin(np.pi * np.clip(t / 0.35, 0, 1)) ** 2 * 0.5
    y = shing + 0.5 * bell(2637, d, 0.4) + 0.35 * np.pad(bell(3951, d - 0.06, 0.3), (T(0.06), 0))[:len(t)]
    return fade(pan_move(y, -0.3, 0.5), 0.001, 0.05)


def s_shades(p=1.0):
    d = 0.8
    y = np.zeros(T(d))
    tg = tt(0.04)
    y[:len(tg)] += filt(noise(len(tg)), "band", [1600, 3800]) * np.exp(-tg / 0.006) * 1.2
    tg = tt(0.08)
    i = T(0.12)
    y[i:i + len(tg)] += filt(noise(len(tg)), "band", [3000, 9000]) * np.exp(-tg / 0.02) * 0.8
    i = T(0.2)
    ch = bell(2800, d - 0.2, 0.9) + 0.6 * bell(4130, d - 0.2, 0.5)
    ch += filt(noise(len(ch)), "high", 6000) * np.exp(-tt(d - 0.2)[:len(ch)] / 0.03) * 0.5
    y[i:i + len(ch)] += ch * 0.8
    return fade(y, 0.0002, 0.05)


def s_grind(p=1.0):
    d = 1.5
    t = tt(d)
    spin = 150 + 90 * (1 - np.exp(-t / 0.12)) - 40 * np.clip((t - 1.2) / 0.3, 0, 1)
    mot = filt(saw_blep(spin) + 0.5 * saw_blep(spin * 2.01), "low", 2200) * (0.8 + 0.2 * np.sin(2 * np.pi * 27 * t))
    grit = filt(noise(len(t)), "band", [2500, 8000]) * (0.5 + 0.5 * np.abs(filt(noise(len(t)), "low", 40)) * 3)
    sp = filt(noise(len(t)) * (rng.random(len(t)) > 0.992), "high", 3000) * 2.5
    env = np.minimum(t / 0.1, 1) * np.minimum((d - t) / 0.25, 1)
    return fade((0.5 * mot + 0.6 * grit + sp) * env, 0.001, 0.03)


def s_weld(p=1.0):
    d = 0.9
    t = tt(d)
    g = np.repeat(rng.random(int(d * 80) + 2) > 0.35, SR // 80)[:len(t)].astype(float)
    g = uniform_filter1d(g, 40)
    siz = filt(noise(len(t)), "high", 2200) * (0.35 + 0.65 * g)
    crk = filt(noise(len(t)) * (rng.random(len(t)) > 0.99), "high", 1500) * 2.2
    hum = filt(np.sign(np.sin(2 * np.pi * 120 * t)), "low", 900) * 0.15
    env = np.minimum(t / 0.02, 1) * np.minimum((d - t) / 0.1, 1)
    return fade((siz + crk + hum) * env, 0.001, 0.02)


def s_chomp(p=1.0):
    d = 0.7
    t = tt(d)
    y = filt(noise(len(t)), "band", [1800, 5500]) * np.exp(-t / 0.012) * 0.7
    i = T(0.03)
    t2 = t[:len(t) - i]
    omp = np.sin(phase(55 + 120 * np.exp(-t2 * 22))) * np.exp(-t2 / 0.12) * 1.2
    growl = filt(saw_blep(110 * 2 ** (-t2 / 0.18)), "low", 900) * np.exp(-t2 / 0.09) * 0.6
    clang = _clank(t2, [(182, 1), (413, 0.8), (694, 0.6), (1131, 0.45), (1780, 0.3)], 1.8) * 0.6
    y[i:] += omp + growl + clang
    return fade(np.tanh(1.5 * y), 0.0002, 0.08)


def s_scratch(p=1.0):
    d = 0.5
    t = tt(d)
    sp = np.where(t < 0.1, 1.6 * np.sin(np.pi * t / 0.1),
                  np.where(t < 0.2, -1.3 * np.sin(np.pi * (t - 0.1) / 0.1),
                           1.4 * np.exp(-(t - 0.2) / 0.08) * np.sin(np.pi * np.clip((t - 0.2) / 0.3, 0, 1) * 0.5 + 0.5)))
    pos = np.cumsum(sp) / SR
    src_t = np.arange(T(0.5)) / SR
    content = saw_blep(np.full(len(src_t), 330.0)) + saw_blep(np.full(len(src_t), 415.0)) + noise(len(src_t)) * 0.4
    content = filt(content, "band", [250, 4000])
    idx = np.clip((pos - pos.min()) * SR + 100, 0, len(content) - 2)
    y = np.interp(idx, np.arange(len(content)), content) * np.abs(sp)
    y += filt(noise(len(t)), "band", [900, 3500]) * np.abs(sp) * 0.5
    return fade(y, 0.0005, 0.03)


def s_tick(p=1.0):
    t = tt(0.07)
    y = filt(noise(len(t)), "band", [2500, 6000]) * np.exp(-t / 0.0025)
    y += np.sin(2 * np.pi * 1900 * t) * np.exp(-t / 0.012) * 0.6 + np.sin(2 * np.pi * 950 * t) * np.exp(-t / 0.015) * 0.4
    return fade(y, 0.0002, 0.01)


def s_ting(p=1.0):
    t = tt(1.3)
    y = (np.sin(2 * np.pi * 2637 * t) + 0.35 * np.sin(2 * np.pi * 2637 * 2.76 * t) * np.exp(-t / 0.1)) * np.exp(-t / 0.45)
    return fade(y * np.minimum(t / 0.001, 1), 0.0002, 0.05)


def formants(src, fs, t=None):
    y = np.zeros_like(src)
    for f, q, a in fs:
        y += a * bpf(src, f, q)
    return y


def s_burp(p=1.0):
    d = 0.55
    t = tt(d)
    f0 = 118 * (1 + 0.15 * np.sin(np.pi * t / d)) * (1 - 0.25 * (t / d) ** 2)
    jit = 1 + 0.06 * filt(noise(len(t)), "low", 70) / 0.3
    src = saw_blep(f0 * jit)
    src *= 0.7 + 0.3 * np.sin(2 * np.pi * 34 * t)
    vow = formants(src, [(520, 5, 1.0), (900, 6, 0.7), (2400, 8, 0.2)])
    vow = tvf(vow, 2200 - 1200 * t / d, "low", 0.8)
    env = np.minimum(t / 0.03, 1) * np.minimum((d - 0.05 - t) / 0.08, 1).clip(0, 1)
    y = vow * env
    i = T(d - 0.06)
    pp = s_pop(1.3)[:len(y) - i] * 0.35
    y[i:i + len(pp)] += pp
    return fade(y, 0.001, 0.02)


def s_aww(p=1.0):
    d = 1.0
    t = tt(d)
    out = np.zeros((2, len(t)))
    for m, pn, dt in ((72, -0.4, -0.06), (76, 0.4, 0.05), (79, 0.0, 0.0)):
        semis = -4.0 * (1 - np.exp(-t / 0.4)) + dt + 0.12 * np.sin(2 * np.pi * 5.3 * t) * np.clip((t - 0.2) / 0.2, 0, 1)
        src = saw_blep(hz(m) * 2 ** (semis / 12))
        v = formants(src, [(720, 5, 1.0), (1100, 6, 0.6), (2650, 8, 0.15)])
        out += stereo(v, pn)
    env = np.minimum(t / 0.09, 1) * np.exp(-np.maximum(t - 0.3, 0) / 0.35)
    return fade(out * env, 0.001, 0.05)


def s_slap(p=1.0):
    t = tt(0.3)
    e = np.zeros(len(t))
    for o in (0.0, 0.005, 0.011):
        e += (t >= o) * np.exp(-np.maximum(t - o, 0) / 0.004)
    y = filt(noise(len(t)), "band", [900, 5000]) * (e + 0.3 * np.exp(-t / 0.04))
    y += filt(noise(len(t)), "band", [150, 900]) * np.exp(-t / 0.025) * 0.8
    y += np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.03) * 0.5
    return fade(y, 0.0002, 0.03)


def s_pophi(p=1.0):
    d = 1.0
    y = np.zeros(T(d))
    pp = s_pop(1.5 * p) * 0.7
    y[:len(pp)] += pp
    pl = ks_string(77 + 12 * np.log2(p), d, t60=0.7, bright=0.75)
    y += filt(pl, "low", 7000) * 0.7
    y += glock(89 + 12 * np.log2(p), d, 0.45)
    return y


def s_counter(p=1.0):
    d = 1.5
    y = np.zeros(T(d))
    tc, k = 0.0, 0
    while tc < d - 0.02:
        tg = tt(0.018)
        f = 1500 * (1 + 0.7 * tc / d)
        g = filt(np.sign(np.sin(2 * np.pi * f * tg)), "low", 6000) * np.exp(-tg / 0.006)
        o = T(tc)
        y[o:o + len(g)] += g[:len(y) - o] * (0.6 + 0.4 * tc / d)
        tc += 1.0 / (9.0 * 5.0 ** (tc / d))
        k += 1
    return pan_move(fade(y, 0.0002, 0.01), -0.2, 0.2)


def s_tada(p=1.0):
    d = 1.3
    out = np.zeros((2, T(d)))
    a = brass(BRASS["C"], 0.12, 0.8, 1.1)
    out[:, :len(a)] += stereo(a)
    b = brass(BRASS["F"] + [81], d - S16, 1.0, 1.25, vibr=True)
    i = T(S16)
    out[:, i:i + len(b)] += stereo(b)
    out += crash(0.5, d) * np.minimum(tt(d) / 0.25, 1)[None, :len(tt(d))]
    for k, m in enumerate((89, 93, 96, 101)):
        s = stereo(glock(m, 0.8, 0.35), -0.5 + k * 0.33)
        j = T(S16 + 0.03 * k)
        out[:, j:j + s.shape[1]] += s[:, :out.shape[1] - j]
    return fade(out, 0.0005, 0.1)


def s_slam(p=1.0):
    d = 2.0
    t = tt(d)
    boom = np.sin(phase(38 + 110 * np.exp(-t * 14))) * np.exp(-t / 0.5)
    hit = filt(noise(len(t)), "band", [150, 3500]) * np.exp(-t / 0.025)
    y = stereo(np.tanh(1.4 * (1.2 * boom + 0.9 * hit)))
    y += crash(1.1, d)
    for k, m in enumerate((89, 93, 96, 101, 105)):
        s = stereo(glock(m, 1.0, 0.4), -0.6 + 0.3 * k)
        j = T(0.05 + 0.035 * k)
        y[:, j:j + s.shape[1]] += s[:, :y.shape[1] - j]
    return fade(y, 0.0003, 0.2)


def s_wink(p=1.0):
    d = 0.7
    t = tt(d)
    y = bell(3520, d, 0.3) * 0.8
    y2 = bell(5274, d - 0.07, 0.2) * 0.5
    y[T(0.07):] += y2[:len(y) - T(0.07)]
    y += filt(noise(len(t)), "high", 8000) * np.exp(-t / 0.08) * 0.25
    return fade(pan_move(y, 0.2, 0.5), 0.0002, 0.05)


def s_button(p=1.0):
    d = 0.5
    t = tt(d)
    y = stereo(np.sin(phase(40 + 110 * np.exp(-t * 16))) * np.exp(-t / 0.3) * 1.2)
    y += stereo(filt(noise(len(t)), "band", [200, 4000]) * np.exp(-t / 0.02) * 0.6)
    for k, m in enumerate((89, 93, 96, 101)):
        s = stereo(glock(m, d, 0.45), -0.45 + 0.3 * k)
        y[:, :s.shape[1]] += s
    return y


# kind: (fn, level, reverb send). level = loudest-50ms RMS in dBFS at the mix reference
# (chorus music sits at -18 dBFS RMS), so SFX land above the band without being peak-normalised.
SFX = {
    "shimmer": (s_shimmer, -21, 0.5), "creak": (s_creak, -22, 0.15), "clunk": (s_clunk, -12.5, 0.12),
    "clunkBig": (s_clunkbig, -9.5, 0.15), "boing": (s_boing, -16, 0.1), "slideUp": (s_slideup, -19, 0.15),
    "splat": (s_splat, -14, 0.1), "pop": (s_pop, -16, 0.15), "whooshIn": (s_whooshin, -17, 0.2),
    "whooshUp": (s_whooshup, -17, 0.25), "whooshDown": (s_whooshdown, -16, 0.2), "whip": (s_whip, -15, 0.15),
    "crane": (s_crane, -15, 0.15), "squash": (s_squash, -10.5, 0.15), "riffle": (s_riffle, -18, 0.1),
    "coins": (s_coins, -18, 0.25), "sadTrombone": (s_sadtrombone, -14, 0.2), "fallWhistle": (s_fallwhistle, -19, 0.2),
    "impact": (s_impact, -10, 0.2), "rattle": (s_rattle, -19, 0.1), "peek": (s_peek, -15, 0.2),
    "burst": (s_burst, -11, 0.25), "jump": (s_jump, -17, 0.1), "landBoing": (s_landboing, -15, 0.1),
    "patter": (s_patter, -19, 0.08), "clickMag": (s_clickmag, -16, 0.1), "wobble": (s_wobble, -18, 0.15),
    "ding": (s_ding, -17, 0.3), "rollIn": (s_rollin, -18, 0.1), "cut": (s_cut, -17, 0.12),
    "sproing": (s_sproing, -15, 0.15), "gleam": (s_gleam, -18, 0.3), "shades": (s_shades, -15, 0.2),
    "grind": (s_grind, -19, 0.1), "weld": (s_weld, -19, 0.1), "chomp": (s_chomp, -10, 0.15),
    "boingUp": (s_boingup, -15, 0.1), "scratch": (s_scratch, -13, 0.1), "tick": (s_tick, -25, 0.35),
    "ting": (s_ting, -23, 0.4), "burp": (s_burp, -16, 0.15), "aww": (s_aww, -21, 0.3),
    "slap": (s_slap, -13, 0.2), "popHi": (s_pophi, -16, 0.25), "counter": (s_counter, -20, 0.12),
    "tada": (s_tada, -12.5, 0.25), "slam": (s_slam, -10, 0.25), "wink": (s_wink, -18, 0.3),
    "button": (s_button, -11, 0.2),
}
SFX_PAN = {"creak": -0.25, "clunk": 0.0, "splat": 0.3, "coins": 0.0, "peek": 0.1, "jump": -0.1, "cut": 0.4,
           "chomp": 0.15, "burp": 0.0, "wink": 0.2, "slap": 0.0, "ding": 0.2, "clickMag": -0.2}


def st_level(x, win=0.05):
    """loudest short-window RMS (linear) of a mono or stereo signal."""
    m = x if np.ndim(x) == 1 else x.mean(axis=0) * np.sqrt(2)
    return np.sqrt(uniform_filter1d(m ** 2, T(win)).max()) + 1e-12


def render_sfx():
    missing = sorted({e["k"] for e in CUE["sfx"]} - set(SFX))
    if missing:
        raise SystemExit("unimplemented sfx kinds: %s" % missing)
    for e in CUE["sfx"]:
        fn, lev, rev = SFX[e["k"]]
        s = filt(fn(float(e.get("p", 1.0))), "high", 35)   # DC / rumble guard
        lev += SFX_TRIM
        s = s * (10 ** (lev / 20) / st_level(s))
        lim = 10 ** ((lev + 11) / 20)          # cap crest factor at ~11 dB (tames crackle spikes)
        s = lim * np.tanh(s / lim)
        add("sfx", s, float(e["t"]), 1.0, SFX_PAN.get(e["k"], 0.0), rev)


# ============================================================ arrangement
def eighths(bar_t, pat):
    return [(bar_t + p * E8, v) for p, v in pat]


def approach(nxt):
    if (nxt - 1) % 12 in SCALE_F:
        return nxt - 1
    if (nxt + 2) % 12 in SCALE_F:
        return nxt + 2
    return nxt


def hook_notes(bar_t, motif, vel=1.0):
    out = []
    for pos, m, ln in motif:
        d = ln * E8 * (0.82 if ln == 1 else 0.94)
        v = vel * (1.0 if ln > 1 or pos in (0, 4) else 0.86)
        out.append((bar_t + pos * E8, d, m, v))
    return out


def harmony_of(m, ch):
    sc = sorted({p for p in range(m - 12, m) if p % 12 in SCALE_F})
    cand = sc[-2] if len(sc) >= 2 else m - 4  # diatonic third below
    if cand % 12 not in PCS[ch]:
        below = [p for p in range(m - 9, m - 2) if p % 12 in PCS[ch]]
        cand = below[-1] if below else cand
    return cand


H1 = [(0, 84, 1), (1, 81, 1), (2, 84, 1), (3, 86, 2), (5, 84, 1), (6, 81, 2)]
H2 = [(0, 79, 1), (1, 81, 1), (2, 79, 1), (3, 77, 1), (4, 79, 3)]
H3 = [(0, 84, 1), (1, 81, 1), (2, 84, 1), (3, 86, 2), (5, 89, 1), (6, 86, 2)]
H4 = [(0, 84, 2), (2, 81, 1), (3, 79, 1), (4, 77, 2), (6, 79, 1), (7, 81, 1)]
H6 = [(0, 79, 1), (1, 81, 1), (2, 79, 1), (3, 77, 1), (4, 79, 1), (5, 81, 1), (6, 84, 2)]
H4B = [(0, 84, 2), (2, 86, 1), (3, 88, 1), (4, 89, 2)]
HOUT = [(0, 84, 1), (1, 81, 1), (2, 79, 1), (3, 81, 1), (4, 77, 4)]


def uke_pattern(bar_t, chords, pat, vel=1.0, t_end=None):
    """chords: callable t->chord. pat: list of (pos8, down, v)."""
    hits = [(bar_t + p * E8, dn, v) for p, dn, v in pat]
    for k, (t0, dn, v) in enumerate(hits):
        nxt = hits[k + 1][0] if k + 1 < len(hits) else bar_t + BAR
        if t_end is not None:
            nxt = min(nxt, t_end)
        d = max(nxt - t0 + 0.015, 0.08)
        add("keys", uke_strum(chords(t0), d, dn, vel * v), t0, 1.0, 0.0, 0.18)


STRUM_CH = [(0, True, 1.0), (2, True, 0.8), (3, False, 0.75), (5, False, 0.75), (6, True, 0.85), (7, False, 0.7)]


def chorus_bar(bar_t, ch, motif, big=False, next_root=None, crash_on=False, glock_all=False, harm=False, last=False):
    R = ROOT[ch]
    # drums
    for b in range(4):
        tb = bar_t + b * BEAT
        place_kick(tb, 1.0)
        if b in (1, 3):
            add("drums", clap(1.0), tb, 0.9, 0.05, 0.18)
            add("drums", snare(0.6), tb, 0.55, 0.0, 0.1)
        add("drums", hat(True, 0.8), tb + E8, 0.55, 0.25)
        for s in range(4):
            if s == 2:
                continue
            acc = 0.75 if s == 0 else 0.45
            if big or s == 0:
                add("drums", hat(False, acc), tb + s * S16, 0.55, -0.3)
        if big:
            for s in range(4):
                add("drums", tamb(0.55 if s % 2 else 0.35), tb + s * S16, 0.5, 0.45)
    if crash_on:
        add("drums", crash(1.0), bar_t, 1.0, 0.0, 0.1)
    # bass
    nr = next_root if next_root is not None else R
    pat = [(0, R, 0.34, 1.0), (2, R + 7, 0.2, 0.75), (3, R, 0.14, 0.6), (4, R + 12, 0.2, 0.85),
           (6, R + 7, 0.2, 0.75), (7, approach(nr), 0.2, 0.7)]
    if last:
        pat = pat[:5]
    for p, m, d, v in pat:
        add("bass", tuba(m, d, v), bar_t + p * E8, 1.0)
        if big:
            add("bass", tuba(m + 12, d, v * 0.25), bar_t + p * E8, 1.0)
    # uke
    uke_pattern(bar_t, lambda t: ch, STRUM_CH, 0.8 if not big else 0.9)
    # pad
    add("keys", pad(ch, BAR), bar_t, 0.55 if big else 0.4, 0.0, 0.25)
    # whistle hook is rendered as a whole line elsewhere; glock sparkle here
    for pos, m, ln in motif:
        if glock_all or ln > 1 or pos == 0:
            add("lead", glock(m + 12, 1.0, 0.8 if (ln > 1 or pos == 0) else 0.5), bar_t + pos * E8, 0.55, 0.35, 0.35)


def build_arrangement():
    i0, i1 = SEC["intro"]
    v0, v1 = SEC["verse"]
    n0, n1 = SEC["nightmare"]
    b0, b1 = SEC["build"]
    c0, c1e = SEC["chorus1"]
    k0, k1 = SEC["break"]
    d0, d1 = SEC["chorus2"]
    o0, o1 = SEC["outro"]
    gap, drop = EV["gap"], EV["drop"]

    # ---------------- intro: groggy uke vamp (rendered to its own buffer, then warped)
    intro = np.zeros((2, T(i1 - i0) + T(1.5)))
    prog = ["F", "CE", "Dm", "C"]

    def put(buf, sig, t, g=1.0, pan=0.0):
        s = stereo(sig, pan) * g
        j = T(t - i0)
        n = min(s.shape[1], buf.shape[1] - j)
        buf[:, j:j + n] += s[:, :n]

    for k, ch in enumerate(prog):
        tc = i0 + k * 2 * BEAT
        put(intro, uke_strum(ch, 1.2, True, 0.8, spread=0.045, t60=1.3, bright=0.45), tc)
        put(intro, ks_string(UKE[ch][3], 0.6, 0.9, 0.5) * 0.18, tc + E8, 1.0, 0.35)
        put(intro, uke_strum(ch, 0.4, False, 0.45, t60=0.8, strings=(1, 2, 3)), tc + 3 * E8)
        put(intro, tuba(ROOT[ch] + (12 if ROOT[ch] < 38 else 0), 0.7, 0.55), tc)
    # wow: zero-mean pitch wobble (sags then recovers once per chord), stays locked to the grid
    tn = np.arange(intro.shape[1]) / SR
    dev = 0.011 * np.sin(2 * np.pi * tn / (2 * BEAT)) + 0.004 * np.sin(2 * np.pi * tn / (0.5 * BEAT) + 1.0)
    pos = np.cumsum(1.0 - dev)
    for c in (0, 1):
        intro[c] = np.interp(pos, np.arange(intro.shape[1]), intro[c])
    j = T(i0)
    B["keys"][:, j:j + intro.shape[1]] += intro[:, :N - j] * 0.9
    SEND["music"][:, j:j + intro.shape[1]] += intro[:, :N - j] * 0.2
    for k in range(int(round((i1 - i0) / E8))):
        add("drums", shaker(0.5 if k % 2 else 0.3), i0 + k * E8, 0.5, 0.35)

    # ---------------- verse: light drums, bouncy tuba, offbeat uke skank
    vprog = ["F", "Bb", "F", "C"]
    for k, ch in enumerate(vprog):
        tc = v0 + k * 2 * BEAT
        place_kick(tc, 0.85, sc=False)
        add("drums", clap(0.8), tc + BEAT, 0.6, 0.05, 0.2)
        R = ROOT[ch]
        add("bass", tuba(R, 0.3, 0.95), tc)
        add("bass", tuba(R + 7, 0.18, 0.7), tc + BEAT)
        add("bass", tuba(R + 12, 0.12, 0.55), tc + BEAT + E8)
        for b in range(2):
            add("keys", uke_strum(ch, 0.2, True, 1.2, t60=0.7), tc + b * BEAT + E8, 1.0, 0.0, 0.15)
            add("drums", hat(False, 0.5), tc + b * BEAT + E8, 0.45, -0.3)
        for s in range(4):
            add("drums", shaker(0.6 if s % 2 else 0.35), tc + s * E8, 0.5, 0.35)
    add("drums", tom(170, 0.7), v1 - E8, 0.6, -0.2)
    add("drums", tom(120, 0.8), v1 - S16, 0.6, 0.2)

    # ---------------- nightmare: Dm oom-pah, pizz, minor glock music-box
    nprog = ["Dm", "Bb", "Gm", "A"]
    PZ = {"Dm": [62, 65, 69], "Bb": [62, 65, 70], "Gm": [62, 67, 70], "A": [61, 64, 69]}
    t_sad = next(e["t"] for e in CUE["sfx"] if e["k"] == "sadTrombone")
    for k, ch in enumerate(nprog):
        tc = n0 + k * 2 * BEAT
        R = ROOT[ch]
        for b in range(2):
            tb = tc + b * BEAT
            if tb >= t_sad - 1e-6:
                continue
            add("bass", tuba(R if b == 0 else R + 7, 0.26, 1.0), tb)
            for m in PZ[ch]:
                add("keys", pizz(m, 0.22, 0.4), tb + E8, 1.0, (m - 65) / 12, 0.2)
            add("drums", kick(0.6), tb, 0.55 if b == 0 else 0.35)
            add("drums", hat(False, 0.35), tb + E8, 0.3, -0.3)
    mbox = [(0.0, 86, 0.5), (0.5, 89, 0.25), (0.75, 93, 0.25), (1.0, 94, 0.5), (1.5, 93, 0.25), (1.75, 89, 0.25),
            (2.0, 91, 0.5), (2.5, 94, 0.25), (2.75, 91, 0.25), (3.0, 85, 0.25), (3.25, 88, 0.25)]
    for o, m, d in mbox:
        add("lead", glock(m, 1.2, 0.7), n0 + o, 0.33, 0.3, 0.4)
        add("lead", glock(m - 12, 0.8, 0.3), n0 + o, 0.3, -0.3, 0.3)

    # ---------------- build: impact hit, C pedal, accelerating snare, riser, dead stop at the gap
    land, roll = EV["crateLand"], EV["rollStart"]
    place_kick(land, 1.1, sc=False)
    add("bass", tuba(ROOT["F"], 0.45, 1.0), land)
    add("keys", uke_strum("F", roll - land, True, 1.0, t60=1.0), land, 1.0, 0.0, 0.2)
    t = roll
    hits = []
    while t < gap - BEAT / 2 - 1e-6:
        hits.append(t)
        step = E8 if t < roll + 2 * BEAT - 1e-6 else (S16 if t < roll + 3 * BEAT - 1e-6 else S16 / 2)
        t += step
    last_hit = gap - BEAT / 2
    for h in hits:
        u = (h - roll) / (last_hit - roll)
        add("drums", snare(1.0), h, 0.25 + 0.45 * u, 0.1 * np.sin(h * 9), 0.15)
        if abs((h - roll) / E8 - round((h - roll) / E8)) < 1e-6:
            add("bass", tuba(ROOT["C"], 0.14, 0.5 + 0.5 * u), h)
        if abs((h - roll) / S16 - round((h - roll) / S16)) < 1e-6:
            dn = abs((h - roll) / E8 - round((h - roll) / E8)) < 1e-6
            add("keys", uke_strum("C", 0.12 if u > 0.4 else 0.24, dn, 0.5 + 0.5 * u, t60=0.6), h, 1.0, 0.0, 0.1)
    place_kick(last_hit, 1.0, sc=False)
    add("drums", snare(1.0), last_hit, 0.8)
    add("drums", crash(0.8, gap - last_hit + 0.05), last_hit, 0.9)
    add("bass", tuba(ROOT["C"], gap - last_hit, 1.0), last_hit)
    add("keys", brass(BRASS["C7"], gap - last_hit, 0.8, 1.0), last_hit, 0.5, 0.0, 0.2)
    add("keys", uke_strum("C7", gap - last_hit, True, 1.0), last_hit)
    dr = gap - roll
    tr = tt(dr)
    riser = np.zeros(len(tr))
    for m, amp in ((48, 1.0), (55, 0.7), (60, 0.5)):
        riser += amp * saw_blep(hz(m) * 4 ** (tr / dr) * (1 + 0.004 * np.sin(2 * np.pi * 5 * tr)))
    riser = tvf(riser, 300 * 20 ** (tr / dr), "low", 2.0) * (0.15 + 0.85 * (tr / dr) ** 2)
    add("keys", fade(riser, 0.05, 0.004), roll, 0.14, 0.0, 0.25)
    sweep = tvf(noise(len(tr)), 400 * 22 ** (tr / dr), "band", 1.5) * (tr / dr) ** 2.2
    add("drums", fade(pan_move(sweep, -0.5, 0.5), 0.05, 0.004), roll, 0.35, 0.0, 0.2)

    # ---------------- chorus 1
    c1 = [("F", H1), ("C", H2), ("Dm", H3), ("Bb", H4), ("F", H1), ("C", H6)]
    wnotes = []
    for k, (ch, mot) in enumerate(c1):
        bt = c0 + k * BAR
        nr = ROOT[c1[(k + 1) % len(c1)][0]]
        chorus_bar(bt, ch, mot, big=k >= 2, next_root=nr, crash_on=(k in (0, 4)))
        wnotes += hook_notes(bt, mot)
    # fill into bar 5 (crash at 24)
    for s, (f, g) in enumerate(((0, 0.6), (0, 0.7), (200, 0.8), (140, 0.9))):
        tf = c0 + 4 * BAR - BEAT + s * S16
        add("drums", snare(1.0) if f == 0 else tom(f, 1.0), tf, g * 0.8, 0.2 * (s - 1.5))
    c1_end = c0 + len(c1) * BAR
    for s, f in enumerate((230, 190, 150, 115)):
        add("drums", tom(f, 1.0), c1_end - BEAT + s * S16, 0.45 + 0.05 * s, -0.3 + 0.2 * s, 0.12)
    wl = whistle_line(wnotes, c0, c1e + 0.5)
    add("lead", whistle_echo(wl), c0, 0.34, 0.0, 0.22)

    # ---------------- break: only the drum fill that leads back in
    fill = k1 - BEAT
    for s, (kind, g) in enumerate((("sn", 0.6), ("sn", 0.75), ("t1", 0.85), ("t2", 1.0))):
        tf = fill + s * S16
        sig = snare(1.0) if kind == "sn" else tom(210 if kind == "t1" else 140, 1.0)
        add("drums", sig, tf, g * 0.8, (s - 1.5) * 0.2, 0.15)
    add("bass", tuba(ROOT["C"] + 12, 0.12, 0.6), fill + 2 * S16)
    add("bass", tuba(ROOT["C"] + 7, 0.12, 0.7), fill + 3 * S16)

    # ---------------- chorus 2: biggest; harmony whistle, glock doubling, brass on the islands
    c2 = [("F", H1), ("C", H2), ("Dm", H3), ("Bb", H4B)]
    wnotes, hnotes = [], []
    tada = EV["tada"]
    count = EV["count"]
    for k, (ch, mot) in enumerate(c2):
        bt = d0 + k * BAR
        last = k == 3
        if not last:
            nr = ROOT[c2[k + 1][0]]
            chorus_bar(bt, ch, mot, big=True, next_root=nr, crash_on=(k == 0), glock_all=True)
        wnotes += hook_notes(bt, mot, 1.0)
        for pos, m, ln in mot:
            hnotes.append((bt + pos * E8, ln * E8 * (0.82 if ln == 1 else 0.94), harmony_of(m, ch), 0.85))
    # last bar (count-up): Bb then C, drums build, everything stops at the ta-da
    lb = d0 + 3 * BAR
    for b in range(4):
        tb = lb + b * BEAT
        if tb >= tada - 1e-6:
            continue
        ch = "Bb" if tb < lb + 2 * BEAT - 1e-6 else "C"
        place_kick(tb, 1.0)
        add("drums", clap(1.0), tb + BEAT / 2 if b >= 2 else tb, 0.5 if b < 2 else 0.7, 0.05, 0.15)
        for s in range(4):
            add("drums", snare(1.0), tb + s * S16, 0.18 + 0.12 * b + 0.04 * s, 0.1, 0.1)
            add("drums", hat(False, 0.6), tb + s * S16, 0.45, -0.3)
        add("bass", tuba(ROOT[ch], 0.2, 1.0), tb)
        add("bass", tuba(ROOT[ch] + 12, 0.15, 0.8), tb + E8)
        add("keys", uke_strum(ch, E8 + 0.01, True, 1.0), tb, 1.0, 0.0, 0.15)
        add("keys", uke_strum(ch, E8 + 0.01, False, 0.9), tb + E8, 1.0, 0.0, 0.15)
        add("keys", pad(ch if ch in PAD else "C", BEAT), tb, 0.8, 0.0, 0.25)
    for e in CUE["sfx"]:
        if e["k"] == "popHi" and d0 <= e["t"] < d1:
            ch = c2[int((e["t"] - d0) // BAR)][0]
            ch = "C" if e["t"] >= lb + 2 * BEAT else ch
            add("keys", brass(BRASS[ch], 0.3, 1.0, 1.1, fall=False), e["t"], 0.55, 0.0, 0.2)
            add("keys", brass(BRASS[ch], 0.14, 0.7, 0.9), e["t"] + E8 + S16, 0.35, 0.0, 0.2)
    wl = whistle_line(wnotes, d0, tada + 0.02)
    hl = whistle_line(hnotes, d0, tada + 0.02, vib=0.005, breath=0.03)
    w2 = whistle_echo(wl)
    w2 += stereo(hl, -0.45) * 0.55 + stereo(hl, 0.45) * 0.15
    add("lead", fade(w2, 0.002, 0.02), d0, 0.34, 0.0, 0.25)
    add("drums", crash(0.7), tada, 0.6, 0.0, 0.15)

    # ---------------- outro
    card, lastc, wink, button = EV["card"], EV["lastClunk"], EV["wink"], EV["button"]
    wl = whistle_line(hook_notes(o0, HOUT), o0, o0 + BAR + 0.05)
    add("lead", whistle_echo(wl), o0, 0.3, 0.0, 0.25)
    for pos, m, ln in HOUT:
        if ln > 1:
            add("lead", glock(m + 12, 1.4, 0.8), o0 + pos * E8, 0.55, 0.3, 0.35)
    place_kick(o0, 0.9)
    add("bass", tuba(ROOT["F"], 0.3, 0.9), o0)
    add("bass", tuba(ROOT["F"] + 7, 0.2, 0.7), o0 + BEAT)
    uke_pattern(o0, lambda t: "F", [(0, True, 0.9), (2, True, 0.7), (3, False, 0.6)], 0.9, t_end=card)
    for s in range(4):
        add("drums", hat(False, 0.5), o0 + s * E8, 0.4, -0.3)
    # slam on the end card
    place_kick(card, 1.1)
    add("keys", brass(BRASS["F"], 0.6, 1.0, 1.2, vibr=True), card, 0.6, 0.0, 0.25)
    add("drums", crash(1.0), card, 0.9)
    oprog = [(card, "F"), (card + 2 * BEAT, "Dm"), (card + 4 * BEAT, "Bb")]
    for tc, ch in oprog:
        R = ROOT[ch]
        add("bass", tuba(R, 0.3, 0.85), tc)
        add("bass", tuba(R + 7, 0.18, 0.65), tc + BEAT)
        add("bass", tuba(R + 12, 0.12, 0.5), tc + BEAT + E8)
        if tc > card:
            place_kick(tc, 0.8)
        add("drums", clap(0.7), tc + BEAT, 0.55, 0.05, 0.2)
        for s in range(4):
            add("drums", shaker(0.6 if s % 2 else 0.35), tc + s * E8, 0.5, 0.35)
            if s % 2:
                add("drums", hat(False, 0.45), tc + s * E8, 0.4, -0.3)
        for b in range(2):
            add("keys", uke_strum(ch, E8 + 0.01, True, 0.75), tc + b * BEAT, 1.0, 0.0, 0.15)
            add("keys", uke_strum(ch, E8 + 0.01, False, 0.6), tc + b * BEAT + E8, 1.0, 0.0, 0.15)
        add("keys", pad(ch, 2 * BEAT), tc, 0.5, 0.0, 0.25)
    for o, m in ((0, 84), (0.5, 81), (1.0, 86), (1.5, 84), (2.0, 81), (2.5, 77)):
        add("lead", glock(m + 12, 1.0, 0.5), card + 2 * BEAT + o, 0.4, 0.3, 0.35)
    # last clunk: stop-time on C, then the cadence
    add("keys", uke_strum("C", wink - lastc, True, 0.8, spread=0.03, t60=1.2), lastc, 1.0, 0.0, 0.25)
    add("bass", tuba(ROOT["C"], 0.5, 0.8), lastc)
    add("keys", uke_strum("C7", button - wink, True, 0.7, t60=0.8), wink)
    add("keys", uke_strum("C7", button - wink - E8, False, 0.6, t60=0.8), wink + E8)
    add("bass", tuba(ROOT["C"] + 7, 0.2, 0.7), wink + E8)
    # button: F major, let it ring
    ring = DUR - button
    place_kick(button, 1.1, sc=False)
    add("keys", brass(BRASS["F"] + [81], ring, 1.0, 1.3), button, 0.6, 0.0, 0.3)
    add("keys", uke_strum("F", ring, True, 1.1, spread=0.02, t60=1.5), button, 1.0, 0.0, 0.3)
    add("bass", tuba(ROOT["F"], ring, 1.0), button)
    add("bass", tuba(ROOT["F"] + 12, ring, 0.4), button)
    add("drums", crash(0.8), button, 0.8)


# ============================================================ mixing / mastering
def sidechain(depth, rel=0.11):
    g = np.ones(N)
    tr = tt(0.35)
    curve = np.minimum(tr / 0.003, 1) * np.exp(-tr / rel)
    for tk in KICKS:
        i = T(tk)
        n = min(len(curve), N - i)
        g[i:i + n] = np.minimum(g[i:i + n], 1 - depth * curve[:n])
    return g


def make_ir(d=1.7, t60=(1.9, 1.35, 0.55), pre=0.014, seed=7):
    r = np.random.default_rng(seed)
    n = T(d)
    t = np.arange(n) / SR
    ir = np.zeros((2, n + T(pre)))
    for c in (0, 1):
        w = r.standard_normal(n)
        lo = filt(w, "low", 450)
        mi = filt(w, "band", [450, 4000])
        hi = filt(w, "high", 4000)
        e = lambda x: 10 ** (-3 * t / x)
        x = lo * e(t60[0]) + mi * e(t60[1]) + 0.6 * hi * e(t60[2])
        x *= np.minimum(t / 0.01, 1)
        for k, (dl, a) in enumerate(((0.007, 0.5), (0.013, 0.35), (0.021, 0.3), (0.029, 0.22), (0.037, 0.18))):
            x[T(dl + 0.003 * c)] += a * (1 if (k + c) % 2 else -1) * 6
        ir[c, T(pre):] = x
    ir /= np.sqrt(np.sum(ir ** 2) / 2)
    return ir


def reverb(send, ir):
    return np.vstack([oaconvolve(send[c], ir[c])[:N] for c in (0, 1)])


def block_env(x, blk, kind="rms"):
    nb = int(np.ceil(x.shape[-1] / blk))
    pad_ = nb * blk - x.shape[-1]
    y = np.pad(np.abs(x) if kind == "peak" else x ** 2, ((0, 0), (0, pad_))).reshape(2, nb, blk)
    if kind == "peak":
        return y.max(axis=(0, 2))
    return np.sqrt(y.mean(axis=(0, 2)))


def smooth_blocks(v, att, rel, blk):
    a_a = np.exp(-blk / (att * SR))
    a_r = np.exp(-blk / (rel * SR))
    out = np.empty_like(v)
    s = v[0]
    for i, x in enumerate(v):
        a = a_a if x > s else a_r
        s = a * s + (1 - a) * x
        out[i] = s
    return out


def blocks_to_samples(v, blk, n):
    centers = (np.arange(len(v)) + 0.5) * blk
    return np.interp(np.arange(n), centers, v)


def compressor(x, thr_db=-20.0, ratio=2.5, att=0.012, rel=0.18, blk=128):
    lev = 20 * np.log10(block_env(x, blk) + 1e-9)
    gr = np.minimum(0.0, (thr_db - lev) * (1 - 1 / ratio))
    gr = -smooth_blocks(-gr, att, rel, blk)
    return x * 10 ** (blocks_to_samples(gr, blk, x.shape[1]) / 20)


def true_peak_env(x):
    up = resample_poly(x, 4, 1, axis=1)
    n = x.shape[1]
    return np.abs(up[:, :4 * n]).reshape(2, n, 4).max(axis=(0, 2))


def limiter(x, ceil_db=-1.3, look=0.0025):
    ceil = 10 ** (ceil_db / 20)
    pk = np.maximum(true_peak_env(x), 1e-9)
    need = np.minimum(1.0, ceil / pk)
    w = 2 * T(look) + 1
    g = minimum_filter1d(need, w)
    g = uniform_filter1d(g, w)
    g = minimum_filter1d(g, 3)
    # slower release so the gain does not flutter
    blk = 64
    gb = g[: (len(g) // blk) * blk].reshape(-1, blk).min(axis=1)
    gb = -smooth_blocks(-gb, 0.0001, 0.08, blk)
    slow = blocks_to_samples(gb, blk, len(g))
    g = np.minimum(g, slow)
    return x * g


def k_weight(x):
    f0, G, Q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
    K = np.tan(np.pi * f0 / SR)
    Vh = 10 ** (G / 20)
    Vb = Vh ** 0.4996667741545416
    a0 = 1 + K / Q + K * K
    b1 = np.array([(Vh + Vb * K / Q + K * K) / a0, 2 * (K * K - Vh) / a0, (Vh - Vb * K / Q + K * K) / a0])
    a1 = np.array([1.0, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0])
    f0, Q = 38.13547087602444, 0.5003270373238773
    K = np.tan(np.pi * f0 / SR)
    a2 = np.array([1.0, 2 * (K * K - 1) / (1 + K / Q + K * K), (1 - K / Q + K * K) / (1 + K / Q + K * K)])
    b2 = np.array([1.0, -2.0, 1.0])
    return lfilter(b2, a2, lfilter(b1, a1, x, axis=-1), axis=-1)


def lufs(x):
    y = k_weight(x)
    blk, hop = T(0.4), T(0.1)
    cs = np.concatenate([np.zeros((2, 1)), np.cumsum(y ** 2, axis=1)], axis=1)
    starts = np.arange(0, y.shape[1] - blk + 1, hop)
    z = (cs[:, starts + blk] - cs[:, starts]) / blk
    zs = z.sum(axis=0)
    l = -0.691 + 10 * np.log10(zs + 1e-20)
    g1 = l > -70
    rel = -0.691 + 10 * np.log10(zs[g1].mean()) - 10
    g2 = g1 & (l > rel)
    return -0.691 + 10 * np.log10(zs[g2].mean())


def tape_stop(x, t0, d):
    i0, n = T(t0), T(d)
    u = np.arange(n) / n
    rate = (1 - u) ** 1.6
    pos = i0 + np.cumsum(rate)
    seg = np.vstack([np.interp(pos, np.arange(x.shape[1]), x[c]) for c in (0, 1)])
    seg *= np.minimum(1, (1 - u) / 0.25)[None, :]
    x[:, i0:i0 + n] = seg
    return i0 + n


def gate(x, t0, t1, fo=0.004, fi=0.0):
    i0, i1 = T(t0), T(t1)
    k = T(fo)
    if k:
        x[:, max(0, i0 - k):i0] *= np.linspace(1, 0, min(k, i0))[None, :]
    x[:, i0:i1] = 0.0
    if fi:
        k = T(fi)
        x[:, i1:i1 + k] *= np.linspace(0, 1, k)[None, :]


def write_wav(path, x):
    pcm = np.clip(np.round(x.T * 32767), -32768, 32767).astype(np.int16)
    wavfile.write(path, SR, pcm)


SFX_TRIM = -2.5   # global SFX fader (dB)
SECTION_DB = {"intro": -2.5, "verse": -1.0, "nightmare": -1.0, "build": 0.0, "chorus1": 0.0,
              "break": 0.0, "chorus2": 1.8, "outro": 0.0}


def section_automation():
    """music fader rides per section (smoothed 15 ms) -> clear energy contour."""
    g = np.ones(N)
    for name, (a, b) in SEC.items():
        g[T(a):T(b)] = 10 ** (SECTION_DB.get(name, 0.0) / 20)
    return uniform_filter1d(g, T(0.015))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out")
    ap.add_argument("--stems", default=None)
    args = ap.parse_args()

    build_arrangement()
    render_sfx()

    gap, drop = EV["gap"], EV["drop"]
    scratch = SEC["break"][0]
    fill_t = SEC["break"][1] - BEAT

    # sidechain pumping (only the four-on-the-floor kicks are in KICKS)
    B["bass"] *= sidechain(0.45, 0.09)[None, :]
    B["keys"] *= sidechain(0.35, 0.13)[None, :]
    B["lead"] *= sidechain(0.12, 0.08)[None, :]

    B["drums"] = filt(B["drums"], "high", 30)
    B["bass"] = filt(B["bass"], "low", 3500)
    B["keys"] = filt(B["keys"], "high", 120)
    B["lead"] = filt(B["lead"], "high", 250)

    ir_m = make_ir()
    ir_s = make_ir(1.2, (1.3, 0.9, 0.4), 0.01, seed=11)
    rev_m = filt(reverb(SEND["music"], ir_m), "high", 250) * 0.35
    rev_s = filt(reverb(SEND["sfx"], ir_s), "high", 300) * 0.3

    stems = {k: B[k] for k in ("drums", "bass", "keys", "lead")}
    stems["reverb"] = rev_m
    # record-scratch: music winds down like a stopped turntable, then silence until the fill
    for k in stems:
        end = tape_stop(stems[k], scratch, 0.32)
        gate(stems[k], end / SR, fill_t, fo=0.0)
    # reference level: chorus-1 music at -18 dBFS RMS, so bus gains / SFX gains are absolute
    c0, c1e = SEC["chorus1"]
    ref = np.sqrt(np.mean(sum(stems.values())[:, T(c0):T(c1e)] ** 2))
    auto = section_automation()
    for k in stems:
        stems[k] *= (10 ** (-18 / 20) / ref) * auto[None, :]
    music = sum(stems.values())
    music = compressor(music, -20.5, 2.0, 0.015, 0.2)

    sfx = B["sfx"] + rev_s
    # SFX carry the jokes: gently duck the music under them (max ~ -4 dB)
    senv = block_env(sfx, 128, "peak")
    senv = smooth_blocks(senv, 0.004, 0.2, 128)
    senv = blocks_to_samples(senv, 128, N)
    duck = 1.0 / (1.0 + 0.45 * np.clip(senv / 0.35, 0, 1.0))
    music *= duck[None, :]

    mix = music + sfx
    mix = filt(mix, "high", 25)

    def finish(y):
        gate(y, gap, drop, fo=0.004)
        f = T(0.3)
        y[:, N - f:] *= np.linspace(1, 0, f) ** 1.5
        return y

    mix = finish(mix)
    g = 10 ** ((-14 - lufs(mix)) / 20)
    for _ in range(5):
        pre = mix * g
        y = finish(limiter(pre, -1.4))
        L = lufs(y)
        if abs(L + 14) < 0.05:
            break
        g *= 10 ** ((-14 - L) / 20)
    tp = 20 * np.log10(true_peak_env(y).max())
    if os.environ.get("MUSIC_DEBUG"):
        r = np.abs(y).max(axis=0) / np.maximum(np.abs(pre).max(axis=0), 1e-9)
        gr = -20 * np.log10(np.clip(r, 1e-6, 1))
        for a in range(0, int(DUR), 2):
            seg = gr[T(a):T(a + 2)]
            print("  limiter %2d-%2d  max GR %.1f dB  mean GR %.2f dB" % (a, a + 2, seg.max(), seg[np.abs(pre).max(axis=0)[T(a):T(a + 2)] > 0.05].mean() if (np.abs(pre).max(axis=0)[T(a):T(a + 2)] > 0.05).any() else 0))
    write_wav(args.out, y)
    print("wrote %s  %.3fs  LUFS(internal)=%.2f  TP(4x)=%.2f dBTP  gain=%.2f dB" % (args.out, y.shape[1] / SR, L, tp, 20 * np.log10(g)))

    if args.stems:
        os.makedirs(args.stems, exist_ok=True)
        stems["sfx"] = sfx
        for k, s in stems.items():
            s = s.copy()
            if k != "sfx":
                s *= duck[None, :]
            write_wav(os.path.join(args.stems, k + ".wav"), np.clip(finish(s * g), -1, 1))
        print("stems ->", args.stems)


if __name__ == "__main__":
    main()
