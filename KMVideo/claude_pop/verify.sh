#!/usr/bin/env bash
# 成片体检：规格 / 帧数 / 响度 / 真峰值 / 爆点前静音与准时炸开。任何一项不合格退出码 1。
# 用法：KMVideo/claude_pop/verify.sh out/KM_claude_pop.mp4      （只需要 ffmpeg + python3 + numpy）
set -euo pipefail
F="${1:?用法: verify.sh <视频.mp4>}"
python3 - "$F" <<'PY'
import re, subprocess, sys
import numpy as np
f = sys.argv[1]; bad = []
def ok(name, cond, got, want):
    print(f"{'合格  ' if cond else '不合格'} {name:<10} 实测 {got:<24} 要求 {want}")
    if not cond: bad.append(name)
info = subprocess.run(['ffmpeg', '-hide_banner', '-i', f], capture_output=True, text=True).stderr
dur = re.search(r'Duration: (\d+):(\d+):([\d.]+)', info); dur = int(dur[1]) * 3600 + int(dur[2]) * 60 + float(dur[3])
v = re.search(r'Video: (\w+).*?, (\d+)x(\d+).*?, ([\d.]+) fps', info)
ok('编码', v[1] == 'h264', v[1], 'h264')
ok('尺寸', (v[2], v[3]) == ('1080', '1920'), f'{v[2]}x{v[3]}', '1080x1920 竖屏')
ok('帧率', abs(float(v[4]) - 24) < .01, v[4], '24')
ok('时长', abs(dur - 46) < .06, f'{dur:.2f}s', '46.00s ±0.06')
n = subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-map', '0:v', '-progress', 'pipe:1', '-nostats', '-f', 'null', '-'], capture_output=True, text=True).stdout
n = int(re.findall(r'frame=(\d+)', n)[-1]); ok('帧数', n == 1104, n, '1104')
e = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', f, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
lufs = float(re.findall(r'I:\s+(-?[\d.]+) LUFS', e)[-1]); tp = float(re.findall(r'Peak:\s+(-?[\d.]+) dBFS', e)[-1])
ok('响度', abs(lufs + 14) <= .6, f'{lufs} LUFS', '-14 ±0.6 LUFS（抖音/IG/YouTube 推荐）')
ok('真峰值', tp <= -.9, f'{tp} dBTP', '≤ -0.9 dBTP（不削波）')
SR = 44100
a = subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-map', '0:a', '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'], capture_output=True).stdout
x = np.frombuffer(a, np.int16).astype(float) / 32768
db = lambda t0, t1: 20 * np.log10(np.sqrt((x[int(t0 * SR):int(t1 * SR)] ** 2).mean()) + 1e-12)
ok('爆点前静音', db(15.80, 15.97) < -50, f'{db(15.80, 15.97):.1f} dB', '15.80–15.97s < -50 dB')
ok('16s 炸开', db(16.0, 16.25) > -25, f'{db(16.0, 16.25):.1f} dB', '16.00–16.25s > -25 dB')
print('全部合格' if not bad else '不合格项：' + '、'.join(bad)); sys.exit(1 if bad else 0)
PY
