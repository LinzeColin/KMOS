#!/usr/bin/env python3
"""对账共用规范化层（银行轴/费用轴匹配前置）。

- normalize_voucher_no：凭证号书写差异归一（全半角、空格、连字符变体：「记 - 12」「记-12」「记—12」→「记-12」）
- normalize_party：对方名归一（全半角、空白、常见公司后缀截断可选）
- normalize_subject_code：科目编码双写法归一（报表点分式「6301.02」与金蝶紧凑式「6301002」同码 → 「6301.002」）
自带 --selftest。
"""
from __future__ import annotations

import re
import unicodedata

_DASHES = "‐-‒–—―−－"


def normalize_voucher_no(value) -> str | None:
    if value in (None, ""):
        return None
    text = unicodedata.normalize("NFKC", str(value)).strip()
    for d in _DASHES:
        text = text.replace(d, "-")
    text = re.sub(r"\s*-\s*", "-", text)
    text = re.sub(r"\s+", "", text)
    return text or None


def normalize_party(value, *, strip_suffix: bool = False) -> str | None:
    if value in (None, ""):
        return None
    text = unicodedata.normalize("NFKC", str(value))
    text = re.sub(r"\s+", "", text)
    if strip_suffix:
        text = re.sub(r"(股份)?(有限)?(责任)?公司$", "", text)
    return text or None


def normalize_subject_code(value) -> str | None:
    """科目编码双写法归一。

    报表侧点分式（子码常为两位，如「6301.02」）与金蝶侧紧凑式（子码三位，如「6301002」）
    指同一科目。归一规则：根码取前四位，其后每段子码一律左补零到三位，段间以点连接；
    紧凑式按「4 位根码 + 每 3 位一段」切分后同样补零，两种写法归一结果一致。
    """
    if value in (None, ""):
        return None
    text = unicodedata.normalize("NFKC", str(value)).strip().replace(" ", "")
    if not text:
        return None
    if "." in text:
        parts = text.split(".")
        root, subs = parts[0], [s for s in parts[1:] if s != ""]
    else:
        if not text.isdigit() or len(text) <= 4:
            return text
        root, rest = text[:4], text[4:]
        subs = [rest[i : i + 3] for i in range(0, len(rest), 3)]
    subs = [s.zfill(3) if len(s) < 3 else s for s in subs]
    return ".".join([root, *subs]) if subs else root


def _selftest() -> int:
    assert normalize_voucher_no("记 - 12") == "记-12"
    assert normalize_voucher_no("记-12") == "记-12"
    assert normalize_voucher_no("记 — 12") == "记-12"
    assert normalize_voucher_no("  记- 7 ") == "记-7"
    assert normalize_voucher_no(None) is None
    assert normalize_party("武汉开明 高新") == "武汉开明高新"
    assert normalize_party("武汉开明高新科技有限公司", strip_suffix=True) == "武汉开明高新科技"
    assert normalize_subject_code("6301.02") == "6301.002"
    assert normalize_subject_code("6301002") == "6301.002"
    assert normalize_subject_code("6602.37") == "6602.037"
    assert normalize_subject_code("6602037") == "6602.037"
    assert normalize_subject_code("222100104") == "2221.001.004"
    assert normalize_subject_code("2221.001.04") == "2221.001.004"
    assert normalize_subject_code("6602") == "6602"
    assert normalize_subject_code(None) is None
    print("selftest: 全部通过")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_selftest() if "--selftest" in sys.argv else 0)
