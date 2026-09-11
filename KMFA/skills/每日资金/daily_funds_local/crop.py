"""把余额表截图裁成「只剩我要的那几行」再交给 Vision。

为什么需要这一步：整张表有四十多行账户明细，我要的 12 个数只在底部三行
（橙色 所有银行存款合计 / 橙色 所有汇票合计 / 粉色 合计），日期在顶部一格。
把中间无关的几十行送进模型，只会挤占分辨率，让小数字变糊。

实测证据：全量回填里 13 个候选硬门不过，逐张调原图核对后确认**全部是模型误读，
源表分毫不差**。而且误读是确定性的——2026-07-11 那张里汇票余额的万位「6」被读成
「0」，同一字形连读三次错三次，所以重试救不了。汇票余额多日不动时，
同一个错会在 07-09/07-13/07-14 上重复出现。

裁剪框按版式写死像素，这和版式识别本身一样可靠——版式就是按精确尺寸认出来的。
尺寸对不上就整张图原样送，绝不猜。

安全性：万一哪天裁错切掉了汇总行，模型会读出垃圾，然后被 gate 的硬门拦下。
失败模式是「这天丢弃」，不是「写进一个错数」。
"""

from __future__ import annotations

import os
import tempfile
from typing import Dict, Optional, Tuple

# 版式 -> (顶部条高度, 底部块高度)。顶部条要含日期格和列头，底部块要含三行汇总。
FOCUS: Dict[str, Tuple[int, int]] = {
    "A": (120, 460),   # 719x1391  旧版，总计块下面还有 3 行尾巴
    "B": (100, 300),   # 1218x1256
    "C": (100, 300),   # 1218x1396
}

# 与 smb_source.LAYOUTS 互为反查，用来确认这张图确实是它自称的版式
EXPECTED: Dict[str, Tuple[int, int]] = {
    "A": (719, 1391),
    "B": (1218, 1256),
    "C": (1218, 1396),
}

GAP = 8       # 顶部条与底部块之间留一条白缝，避免模型把两段接成一行
SCALE = 2     # 放大倍数：数字在模型视野里的高度翻倍


def focus(image_path: str, layout: str, out_path: Optional[str] = None) -> str:
    """裁出聚焦图并返回路径。任何一步不确定就返回原图路径。"""
    try:
        from PIL import Image
    except ImportError:
        return image_path

    box = FOCUS.get(layout)
    if not box:
        return image_path

    try:
        im = Image.open(image_path).convert("RGB")
    except Exception:
        return image_path

    if EXPECTED.get(layout) and im.size != EXPECTED[layout]:
        return image_path      # 尺寸与版式不符，不敢裁

    top_h, bot_h = box
    if im.height <= top_h + bot_h:
        return image_path      # 图本来就不比裁剪框高，裁了没意义

    top = im.crop((0, 0, im.width, top_h))
    bot = im.crop((0, im.height - bot_h, im.width, im.height))

    out = Image.new("RGB", (im.width, top_h + GAP + bot_h), "white")
    out.paste(top, (0, 0))
    out.paste(bot, (0, top_h + GAP))
    out = out.resize((out.width * SCALE, out.height * SCALE), Image.LANCZOS)

    if out_path is None:
        out_path = os.path.join(tempfile.mkdtemp(prefix="kmfa-focus-"), "focus.png")
    out.save(out_path)
    return out_path
