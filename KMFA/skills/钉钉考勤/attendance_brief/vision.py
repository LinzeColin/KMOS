"""OCR：macOS 系统 Vision 框架。离线、确定性、零模型调用、零 token。

多路交叉验证的两条独立路线：
  full()  整图多变体多参数（10 路）—— 抗单点误识别
  cells() 逐格裁剪放大（2 路）—— 抗合并单元格串行
两条路线的候选一起交给 roster 闸门仲裁。
"""
from __future__ import annotations
import os, tempfile
import numpy as np
from PIL import Image
import Quartz, Vision
from Foundation import NSURL

LANGS = ["zh-Hans", "en-US"]

def _run(path: str, correct: bool = False, level: int = 0):
    url = NSURL.fileURLWithPath_(str(path))
    src = Quartz.CGImageSourceCreateWithURL(url, None)
    if src is None:
        return [], (0, 0)
    img = Quartz.CGImageSourceCreateImageAtIndex(src, 0, None)
    W, H = Quartz.CGImageGetWidth(img), Quartz.CGImageGetHeight(img)
    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(level)
    req.setRecognitionLanguages_(LANGS)
    req.setUsesLanguageCorrection_(correct)
    h = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(img, None)
    h.performRequests_error_([req], None)
    out = []
    for o in (req.results() or []):
        c = o.topCandidates_(1)[0]
        b = o.boundingBox()
        out.append((b.origin.x * W, (1 - b.origin.y - b.size.height) * H,
                    b.size.width * W, b.size.height * H,
                    float(c.confidence()), c.string().strip()))
    return out, (W, H)

def _variants(src: str, tmp: str) -> list[tuple[str, str]]:
    im = Image.open(src).convert("RGB")
    w, h = im.size
    out = [("原图", src)]
    for tag, f in (("2x", 2), ("3x", 3)):
        p = os.path.join(tmp, f"v_{tag}.png")
        im.resize((w * f, h * f), Image.LANCZOS).save(p)
        out.append((tag, p))
    g = np.asarray(im.convert("L"), dtype=np.uint8)
    thr = int(np.mean(g))
    p = os.path.join(tmp, "v_bin.png")
    Image.fromarray(((g > thr) * 255).astype(np.uint8)).resize(
        (w * 2, h * 2), Image.LANCZOS).save(p)
    out.append(("二值", p))
    from PIL import ImageFilter
    p = os.path.join(tmp, "v_sharp.png")
    im.resize((w * 2, h * 2), Image.LANCZOS).filter(ImageFilter.SHARPEN).save(p)
    out.append(("锐化", p))
    return out

def full(src: str) -> dict[tuple[int, int], list[str]]:
    """整图多路。返回 归一化网格位置 -> 该位置出现过的所有文本（含重复，用于投票）。"""
    votes: dict[tuple[int, int], list[str]] = {}
    with tempfile.TemporaryDirectory() as tmp:
        for _tag, p in _variants(src, tmp):
            for correct in (False, True):
                res, (W, H) = _run(p, correct=correct)
                if not W:
                    continue
                for x, y, _w, _h, _c, t in res:
                    if not t:
                        continue
                    key = (round(x / W / 0.015), round(y / H / 0.012))
                    votes.setdefault(key, []).append(t)
    return votes

def cells(src: str, xs: list[int], ys: list[int], scale: int = 3
          ) -> dict[tuple[int, int], tuple[str, str]]:
    """逐格 OCR。返回 (行,列) -> (无纠错文本, 有纠错文本)。空格子不返回。"""
    im = Image.open(src).convert("RGB")
    g = np.asarray(im.convert("L"), dtype=np.uint8)
    out: dict[tuple[int, int], tuple[str, str]] = {}
    with tempfile.TemporaryDirectory() as tmp:
        for r in range(len(ys) - 1):
            for c in range(len(xs) - 1):
                y0, y1, x0, x1 = ys[r] + 2, ys[r + 1] - 2, xs[c] + 2, xs[c + 1] - 2
                if y1 - y0 < 8 or x1 - x0 < 8:
                    continue
                if g[y0:y1, x0:x1].std() < 12:      # 空格子
                    continue
                p = os.path.join(tmp, f"c{r}_{c}.png")
                im.crop((x0, y0, x1, y1)).resize(
                    ((x1 - x0) * scale, (y1 - y0) * scale), Image.LANCZOS).save(p)
                a = " ".join(t for *_r, t in _run(p, False)[0] if t)
                b = " ".join(t for *_r, t in _run(p, True)[0] if t)
                if a or b:
                    out[(r, c)] = (a, b)
    return out
