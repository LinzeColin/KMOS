#!/usr/bin/env python3
# 混音体检表：逐 2 秒段的 LUFS/RMS/峰值、各分轨电平，以及每个音效 0.3s 窗口内“音效 vs 音乐”的电平对比。
# 调配乐/音效平衡时用：先 `python3 music.py out/bgm.wav --stems out/stems`，再 `python3 tools/mix_report.py out/bgm.wav out/stems`。
import numpy as np, sys, os
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEMS = sys.argv[2] if len(sys.argv) > 2 else None
from scipy.io import wavfile
SR,x=wavfile.read(sys.argv[1]); x=x.astype(float)/32768
print("sr",SR,"shape",x.shape,"dur",len(x)/SR)
def rms(a,b,y=x):
    s=y[int(a*SR):int(b*SR)]; return 20*np.log10(np.sqrt((s**2).mean())+1e-12)
def pk(a,b,y=x):
    s=y[int(a*SR):int(b*SR)]; return 20*np.log10(np.abs(s).max()+1e-12)
print("gap 15.76-15.99 rms", rms(15.76,15.99), "max", np.abs(x[int(15.76*SR):int(15.99*SR)]).max())
stems={k:wavfile.read(f"{STEMS}/{k}.wav")[1].astype(float)/32768 for k in ["drums","bass","keys","lead","reverb","sfx"]} if STEMS and os.path.isdir(STEMS) else {}
sys.path.insert(0, HERE); sys.argv = sys.argv[:1]
import music as M
kw=M.k_weight(x.T)
def st(a,b): s=kw[:,int(a*SR):int(b*SR)]; return -0.691+10*np.log10((s**2).mean(axis=1).sum()+1e-20)
print("bar  LUFS  mix   pk  | "+" ".join(f"{k:>7}" for k in stems))
for b in range(23):
    a=b*2; print(f"{a:2d}-{a+2:2d} {st(a,a+2):5.1f} {rms(a,a+2):6.1f} {pk(a,a+2):5.1f} | "+" ".join(f"{rms(a,a+2,v):7.1f}" for v in stems.values()))
if stems:
    m=sum(v for k,v in stems.items() if k!="sfx")
    print("music-only rms 28.4-31.45:", rms(28.4,31.45,m), " music 28.0-28.35:", rms(28.0,28.35,m))
import json
src=open(os.path.join(HERE, 'cues.js')).read(); cue,_=json.JSONDecoder().raw_decode(src[src.index('const CUE = ')+12:])
if stems:
    m=sum(v for k,v in stems.items() if k!="sfx")
    print("event            t    sfxPk  musPk  sfxRMS musRMS (0.3s window, dBFS)")
    for e in cue['sfx']:
        a=e['t']; b=a+0.3
        print(f"{e['k']:12s} {a:6.2f} {pk(a,b,stems['sfx']):6.1f} {pk(a,b,m):6.1f} {rms(a,b,stems['sfx']):6.1f} {rms(a,b,m):6.1f}")
