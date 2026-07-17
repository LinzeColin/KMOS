#!/usr/bin/env python3
"""对账共用规范化层（银行轴/费用轴匹配前置）。

- normalize_voucher_no：凭证号书写差异归一（全半角、空格、连字符变体：「记 - 12」「记-12」「记—12」→「记-12」）
- normalize_party：对方名归一（全半角、空白、常见公司后缀截断可选）
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


def _selftest() -> int:
    assert normalize_voucher_no("记 - 12") == "记-12"
    assert normalize_voucher_no("记-12") == "记-12"
    assert normalize_voucher_no("记 — 12") == "记-12"
    assert normalize_voucher_no("  记- 7 ") == "记-7"
    assert normalize_voucher_no(None) is None
    assert normalize_party("武汉开明 高新") == "武汉开明高新"
    assert normalize_party("武汉开明高新科技有限公司", strip_suffix=True) == "武汉开明高新科技"
    print("selftest: 全部通过")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_selftest() if "--selftest" in sys.argv else 0)
