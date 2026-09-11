"""从归档文件名或钉钉 mediaId 里解出图片尺寸——不下载图片。

余额表的唯一可靠选择器是尺寸（消息文本和业务命名都会选错，已实测）。
归档里有两种 mediaId：

  旧式 ``@lQL...``  尺寸直接写在归档文件名 ``..._<W>_<H>.png`` 里
  新式 ``$iwE...``  base64 里是一段 msgpack，字段 4 = 宽、字段 5 = 高

实测 1075 条 media 里 1053 条能解出，剩下的按 unknown 跳过。
"""

from __future__ import annotations

import base64
import re
from typing import Optional, Tuple

Dims = Tuple[int, int]

_NAME_DIMS = re.compile(r"_(\d+)_(\d+)\.[A-Za-z]+$")

# msgpack 里 0x04/0x05 键后面跟 0xd1 表示「接下来 2 字节是大端 uint16」
_W_TAG = b"\x04\xd1"
_H_TAG = b"\x05\xd1"


def _b64(raw: str) -> bytes:
    s = raw.replace("-", "+").replace("_", "/")
    s += "=" * (-len(s) % 4)
    try:
        return base64.b64decode(s)
    except Exception:
        return b""


def dims_from_filename(name: str) -> Optional[Dims]:
    m = _NAME_DIMS.search(name or "")
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def dims_from_media_id(resource_id: str) -> Optional[Dims]:
    blob = _b64((resource_id or "").lstrip("$@"))
    if not blob:
        return None
    i = blob.find(_W_TAG)
    j = blob.find(_H_TAG)
    if i < 0 or j < 0 or i + 4 > len(blob) or j + 4 > len(blob):
        return None
    w = int.from_bytes(blob[i + 2:i + 4], "big")
    h = int.from_bytes(blob[j + 2:j + 4], "big")
    if w <= 0 or h <= 0:
        return None
    return w, h


def dims_of(record: dict) -> Optional[Dims]:
    """先看文件名（最可靠），再退回解 mediaId。"""
    path = record.get("smb_relative_path") or record.get("relative_path") or ""
    found = dims_from_filename(path.split("/")[-1])
    if found:
        return found
    return dims_from_media_id(record.get("resource_id") or "")
