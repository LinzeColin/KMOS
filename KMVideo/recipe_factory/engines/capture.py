"""通用逐帧采集器：任何网页引擎（canvas2d / p5brush / threejs / svg_gsap）都用它出片。

页面契约（制作 agent 写 HTML 时必须满足）：
  window.ready      Promise，字体/贴图/模型加载完成后 resolve
  window.renderAt(t, fps)  纯函数：把画面画成第 t 秒的样子，任意 t 可独立重算
  window.DURATION   片长（秒）
  可选 <canvas id="c">：有就用 toDataURL 取帧（快）；没有就截整页（SVG/DOM 页面）

用法：
  python3 capture.py page.html out.mp4 [--fps 30] [--audio bgm.wav]
  python3 capture.py page.html out_dir --frames 0,1.5,3        # 导出单帧 PNG
  python3 capture.py page.html sheet.png --sheet 20             # 均匀抽 20 帧拼接触表
  python3 capture.py 成片.mp4 sheet.png --sheet 20              # 对成片拼接触表（质检用）
环境变量 CHROME_PATH 指定浏览器；未设置时用 Playwright 自带的 Chromium。
本机有独显时加 --gpu，WebGL 走硬件；无独显加 --soft-gl（SwiftShader，慢但可用）。
"""
import argparse, base64, io, os, pathlib, subprocess, sys, time

import imageio_ffmpeg
from PIL import Image
from playwright.sync_api import sync_playwright

FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H = 1080, 1920


def open_page(p, html, gpu, soft_gl):
    args = ["--allow-file-access-from-files", "--autoplay-policy=no-user-gesture-required"]
    if soft_gl:
        args += ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"]
    if gpu:
        args += ["--enable-gpu", "--ignore-gpu-blocklist"]
    kw = {"args": args}
    if os.environ.get("CHROME_PATH"):
        kw["executable_path"] = os.environ["CHROME_PATH"]
    b = p.chromium.launch(**kw)
    pg = b.new_page(viewport={"width": W, "height": H})
    pg.goto(pathlib.Path(html).resolve().as_uri())
    pg.evaluate("window.ready")
    has_canvas = pg.evaluate("!!document.getElementById('c')")
    dur = pg.evaluate("window.DURATION || 30")

    def grab(t, fps):
        if has_canvas:
            return base64.b64decode(pg.evaluate(
                "([t,f]) => { renderAt(t,f); return document.getElementById('c').toDataURL('image/png').split(',')[1]; }",
                [t, fps]))
        pg.evaluate("([t,f]) => renderAt(t,f)", [t, fps])
        return pg.screenshot(type="png")
    return b, grab, dur


def sheet(frames, times, out, cols=5):
    thumbs = [Image.open(io.BytesIO(f)).convert("RGB").resize((216, 384)) for f in frames]
    rows = (len(thumbs) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * 224, rows * 404), (20, 20, 20))
    from PIL import ImageDraw
    d = ImageDraw.Draw(canvas)
    for i, (im, t) in enumerate(zip(thumbs, times)):
        x, y = (i % cols) * 224 + 4, (i // cols) * 404 + 4
        canvas.paste(im, (x, y))
        d.text((x + 4, y + 386), f"{t:05.2f}s", fill=(255, 220, 120))
    canvas.save(out)


def video_frames(mp4, n):
    probe = subprocess.run([FF, "-i", mp4], capture_output=True, text=True).stderr
    hh, mm, ss = probe.split("Duration: ")[1].split(",")[0].split(":")
    dur = int(hh) * 3600 + int(mm) * 60 + float(ss)
    times = [dur * (i + 0.5) / n for i in range(n)]
    frames = [subprocess.run([FF, "-ss", f"{t:.3f}", "-i", mp4, "-frames:v", "1", "-f", "image2pipe",
                              "-c:v", "png", "-"], capture_output=True).stdout for t in times]
    return frames, times


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--frames", default="")
    ap.add_argument("--sheet", type=int, default=0)
    ap.add_argument("--audio", default="")
    ap.add_argument("--gpu", action="store_true")
    ap.add_argument("--soft-gl", action="store_true")
    a = ap.parse_args()
    out = pathlib.Path(a.out)

    if a.src.endswith(".mp4"):
        frames, times = video_frames(a.src, a.sheet or 20)
        sheet(frames, times, out)
        return

    with sync_playwright() as p:
        b, grab, dur = open_page(p, a.src, a.gpu, a.soft_gl)
        if a.frames:
            out.mkdir(parents=True, exist_ok=True)
            for t in [float(x) for x in a.frames.split(",")]:
                (out / f"t{t:05.2f}.png").write_bytes(grab(t, a.fps))
            b.close(); return
        if a.sheet:
            times = [dur * (i + 0.5) / a.sheet for i in range(a.sheet)]
            sheet([grab(t, a.fps) for t in times], times, out)
            b.close(); return
        cmd = [FF, "-y", "-f", "image2pipe", "-c:v", "png", "-framerate", str(a.fps), "-i", "-"]
        if a.audio:
            cmd += ["-i", a.audio, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "44100",
                    "-c:a", "aac", "-b:a", "256k", "-shortest"]
        cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
                "-profile:v", "high", "-movflags", "+faststart", str(out)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        n = int(round(dur * a.fps)); t0 = time.time()
        for i in range(n):
            proc.stdin.write(grab(i / a.fps, a.fps))
            if i % 90 == 0:
                print(f"frame {i}/{n}  {time.time() - t0:.0f}s", flush=True)
        proc.stdin.close(); rc = proc.wait(); b.close()
        sys.exit(rc)


if __name__ == "__main__":
    main()
