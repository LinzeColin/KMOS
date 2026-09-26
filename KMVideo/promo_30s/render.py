"""把 render.html 逐帧渲染成 PNG 流并交给 ffmpeg 编码，最后混入 music.py 生成的 BGM。

浏览器：环境变量 CHROME_PATH；未设置时用 Playwright 自带 Chromium。
用法：python3 render.py OUT.mp4 [--frames 0,90,300] [--fps 30]
--frames 只导出指定帧为 PNG（目视检查用）。
"""
import argparse, base64, os, pathlib, subprocess, sys, time
from playwright.sync_api import sync_playwright
import imageio_ffmpeg

HERE = pathlib.Path(__file__).resolve().parent
DUR = 30.0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--frames", default="")
    ap.add_argument("--audio", default="")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    with sync_playwright() as p:
        kw = {"executable_path": os.environ["CHROME_PATH"]} if os.environ.get("CHROME_PATH") else {}
        b = p.chromium.launch(args=["--allow-file-access-from-files"], **kw)
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto((HERE / "render.html").as_uri())
        pg.evaluate("window.ready")
        grab = lambda t: base64.b64decode(pg.evaluate(
            "([t,f]) => { renderAt(t,f); return document.getElementById('c').toDataURL('image/png').split(',')[1]; }", [t, a.fps]))
        if a.frames:
            out.mkdir(parents=True, exist_ok=True)
            for f in [float(x) for x in a.frames.split(",")]:
                (out / f"t{f:05.2f}.png").write_bytes(grab(f))
            b.close(); return
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [ff, "-y", "-f", "image2pipe", "-c:v", "png", "-framerate", str(a.fps), "-i", "-"]
        if a.audio: cmd += ["-i", a.audio, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "44100", "-c:a", "aac", "-b:a", "256k", "-shortest"]
        cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
                "-profile:v", "high", "-movflags", "+faststart", str(out)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        n = int(DUR * a.fps); t0 = time.time()
        for i in range(n):
            proc.stdin.write(grab(i / a.fps))
            if i % 90 == 0: print(f"frame {i}/{n}  {time.time()-t0:.0f}s", flush=True)
        proc.stdin.close(); rc = proc.wait(); b.close()
        sys.exit(rc)

if __name__ == "__main__":
    main()
