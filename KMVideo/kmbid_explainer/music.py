"""KMBID 讲解片原创配乐（62 秒，120 BPM，C 大调），numpy 合成，无版权依赖。

  python3 music.py out/bgm.wav

段落与画面同一张秒点表（见 STORYBOARD.md）：
  A 0–7 纸堆：拨弦紧张感 + 秒针     B 7–14 网站登场：琶音亮起
  C 14–23 聚合：完整律动            D 23–30 夜晚：八音盒，28 秒日出和弦
  E 30–40.5 反馈：律动回归 + 盖章/射箭音效    F 40.5–51 收益：最大段落 + 金币叮当
  G 51–62 片尾：温暖收束，61 秒长和弦淡出
"""
import sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR, BPM, DUR = 44100, 120, 62.0
BEAT = 60 / BPM
N = int(SR * DUR)
out = np.zeros((N, 2))
rng = np.random.default_rng(7)


def midi(n): return 440 * 2 ** ((n - 69) / 12)


def add(sig, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= N: return
    sig = sig[: N - i] * gain
    out[i:i + len(sig), 0] += sig * (1 - pan) ** .5
    out[i:i + len(sig), 1] += sig * (1 + pan) ** .5


def env(n, a=.004, d=.3):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / d)


def marimba(f, dur=.45):
    n = int(SR * dur); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + .25 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t / .05)) * env(n, .002, .18)


def glock(f, dur=1.2):
    n = int(SR * dur); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + .35 * np.sin(2 * np.pi * f * 2.76 * t) + .15 * np.sin(2 * np.pi * f * 5.4 * t)) * env(n, .001, .5)


def pluck(f, dur=.3):
    n = int(SR * dur); t = np.arange(n) / SR
    return np.sign(np.sin(2 * np.pi * f * t)) * .3 * env(n, .002, .07) + np.sin(2 * np.pi * f * t) * env(n, .002, .12)


def bass(f, dur=.45):
    n = int(SR * dur); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + .3 * np.sin(4 * np.pi * f * t)) * env(n, .005, .25)


def pad(fs, dur):
    n = int(SR * dur); t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * t) + .2 * np.sin(2 * np.pi * f * 2.003 * t) for f in fs) / len(fs)
    return s * np.minimum(1, t / .6) * np.minimum(1, (dur - t) / .8)


def hp(x, fc): return sosfilt(butter(2, fc / (SR / 2), 'high', output='sos'), x)
def lp(x, fc): return sosfilt(butter(2, fc / (SR / 2), 'low', output='sos'), x)


def kick():
    n = int(SR * .35); t = np.arange(n) / SR
    return np.sin(2 * np.pi * (50 * t + 70 * .04 * (1 - np.exp(-t / .04)))) * np.exp(-t / .12)


def clap():
    n = int(SR * .2); x = rng.standard_normal(n) * np.exp(-np.arange(n) / SR / .05)
    return lp(hp(x, 900), 5000) * .6


def shaker():
    n = int(SR * .06); return hp(rng.standard_normal(n), 6000) * np.exp(-np.arange(n) / SR / .015) * .3


def whoosh(dur=.6):
    n = int(SR * dur); t = np.arange(n) / SR; x = rng.standard_normal(n)
    return lp(hp(x, 400), 3000) * np.sin(np.pi * t / dur) ** 2 * .5


def thud():
    n = int(SR * .25); t = np.arange(n) / SR
    return np.sin(2 * np.pi * (90 * t - 120 * t * t)) * np.exp(-t / .06) + lp(rng.standard_normal(n), 800) * np.exp(-t / .02) * .5


def thwip():
    n = int(SR * .18); t = np.arange(n) / SR
    return np.sin(2 * np.pi * (1800 * t - 3500 * t * t)) * np.exp(-t / .05) * .4


# C G Am F，每和弦一小节（4 拍 = 2 秒）
CH = [[48, 52, 55], [43, 47, 50], [45, 48, 52], [41, 45, 48]]
HOOK = [76, 79, 81, 79, 76, 74, 72, 74, 76, 79, 84, 81, 79, 76, 74, 72]   # 八分音符 × 16 = 两小节


def bar_of(t): return int(t / (4 * BEAT)) % 4


def groove(t0, t1, drums=True, melody=True, arps=True, lvl=1.0):
    b = t0
    while b < t1 - 1e-6:
        beat = round(b / BEAT)
        ch = CH[bar_of(b)]
        if drums:
            if beat % 2 == 0: add(kick(), b, .55 * lvl)
            else: add(clap(), b, .35 * lvl, .1)
            add(shaker(), b + BEAT / 2, .8 * lvl, -.3)
            add(shaker(), b, .5 * lvl, .3)
        add(bass(midi(ch[0] - 12 + 12)), b, .35 * lvl)
        if arps:
            for k, n in enumerate([ch[0] + 24, ch[1] + 24]):
                add(marimba(midi(n)), b + k * BEAT / 2, .16 * lvl, -.2 + .4 * k)
        if melody:
            i = int(round(b / (BEAT / 2))) % 16
            for k in range(2):
                add(marimba(midi(HOOK[(i + k) % 16]), .5), b + k * BEAT / 2, .22 * lvl, .15)
        b += BEAT


# A 纸堆：Am 拨弦 + 秒针
for i in range(14):
    t = i * BEAT
    add(pluck(midi([57, 60, 64, 60][i % 4])), t, .25, -.2)
    add(hp(rng.standard_normal(int(SR * .02)), 3000) * .4, t + BEAT / 2, .5, .4)
add(thud(), 4.2, .6)                      # 纸砸头
add(glock(midi(84)), 5.1, .35)            # 灯泡
add(whoosh(), 6.6, .8)
# B 网站
for i in range(14):
    t = 7 + i * BEAT; ch = CH[bar_of(t)]
    add(marimba(midi(ch[i % 3] + 24)), t, .2, (-1) ** i * .2)
    if i >= 4: add(bass(midi(ch[0])), t, .3)
add(glock(midi(79)), 7.6, .3); add(glock(midi(84)), 8.2, .3)   # 窗口落下
add(thud(), 11.35, .5); add(whoosh(.5), 12.05, .6)             # 教程砸下、被踢飞
add(whoosh(.5), 13.4, .6)
# C 聚合
groove(14, 23)
add(whoosh(), 22.6, .8)
# D 夜晚：八音盒
for i in range(12):
    t = 23.2 + i * BEAT * .9
    add(glock(midi([72, 76, 79, 76, 74, 77, 81, 77, 72, 76, 79, 84][i]), 1.6), t, .22, (-1) ** i * .3)
add(pad([midi(n) for n in (60, 64, 67)], 4.6), 23.2, .12)
add(pad([midi(n) for n in (65, 69, 72, 76)], 3.0), 27.8, .2)   # 日出
add(glock(midi(88), 2), 28.6, .3)
# E 反馈
groove(30, 40.5, melody=False, lvl=.9)
for ti in (1.2, 2.5, 3.8, 5.2, 5.9): add(thud(), 30 + ti + .65, .55)
for ti in (1.0, 1.8, 2.6, 6.9, 7.6, 8.3, 8.9): add(thwip(), 30 + ti + .2, .5, .5)
add(glock(midi(91), 1.5), 38.9, .3)
add(whoosh(), 40.1, .7)
# F 收益：最大段落
groove(40.5, 51, lvl=1.1)
for i in range(16): add(glock(midi([84, 88, 91, 96][i % 4]), .6), 45.6 + i * .31, .12, (-1) ** i * .5)
add(whoosh(), 50.6, .8)
# G 片尾
groove(51, 58, drums=False, lvl=.8)
add(pad([midi(n) for n in (60, 64, 67, 72)], 4.0), 57.8, .25)
add(glock(midi(84), 2.5), 58.2, .3); add(glock(midi(88), 2.5), 58.45, .25); add(glock(midi(91), 3), 58.7, .25)
add(pad([midi(n) for n in (48, 55, 60, 64)], 3.8), 58.2, .22)

out = np.tanh(out * 1.4) * .7
fade = np.ones(N); fade[-int(SR * .8):] = np.linspace(1, 0, int(SR * .8))
out *= fade[:, None]
wavfile.write(sys.argv[1], SR, (out * 32767).astype(np.int16))
print('wrote', sys.argv[1], f'{DUR}s')
