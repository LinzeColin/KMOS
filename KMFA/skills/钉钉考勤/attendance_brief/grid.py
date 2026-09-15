"""表格网格检测。只用 PIL + numpy，无 opencv 依赖。"""
from __future__ import annotations
import numpy as np
from PIL import Image

DARK = 170

def _peaks(proj: np.ndarray, thr_ratio: float = 0.55, gap: int = 3) -> list[int]:
    if proj.max() <= 0:
        return []
    thr = proj.max() * thr_ratio
    groups: list[list[int]] = []
    for i in np.where(proj > thr)[0]:
        if groups and i - groups[-1][-1] <= gap:
            groups[-1].append(int(i))
        else:
            groups.append([int(i)])
    return [int(np.mean(g)) for g in groups]

def load_gray(path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("L"), dtype=np.uint8)

def grid(gray: np.ndarray) -> tuple[list[int], list[int]]:
    """返回 (竖线 x 列表, 横线 y 列表)"""
    H, W = gray.shape
    d = gray < DARK
    xs = _peaks(d.sum(axis=0) / H)
    ys = _peaks(d.sum(axis=1) / W)
    if not xs or xs[0] > 4: xs = [0] + xs
    if not xs or xs[-1] < W - 5: xs = xs + [W - 1]
    if not ys or ys[0] > 4: ys = [0] + ys
    if not ys or ys[-1] < H - 5: ys = ys + [H - 1]
    return xs, ys

def has_hline(gray: np.ndarray, x0: int, x1: int, y: int,
              tol: int = 3, cover: float = 0.75) -> bool:
    """列区间 [x0,x1] 在 y 处是否存在横向边框 —— 用于判定合并单元格边界。"""
    band = gray[max(0, y - tol): y + tol + 1, x0 + 4: x1 - 4]
    if band.size == 0:
        return True
    return bool((band < DARK).sum(axis=1).max() >= (x1 - x0 - 8) * cover)
