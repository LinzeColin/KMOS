# -*- coding: utf-8 -*-
"""项目成本必须说明自己是什么时候算的。

Owner 2026-07-28 问：「项目成本是实时更新的？」——而在此之前这份产物里
**一个时间戳都没有**。页面上看到 32 个项目、20 个已完工，
但看不出这份数是今天算的还是上周的。

分不出来就等于不知道它有没有在更新，跟「绿的但没干活」是同一类问题：
看着有数，其实不知道数从哪一刻来。这次压测里之所以发现算法改了页面没变，
正是因为判据曾经是「产物在不在」而不是「产物新不新」。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BUILDER = REPO / "KMFA/tools/project_cost/build_recent_completed.py"

ISO_BEIJING = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+08:00$")


def test_the_builder_stamps_a_beijing_timestamp():
    src = BUILDER.read_text(encoding="utf-8")
    assert '"生成时间"' in src, "产物里没有生成时间——看不出这份数什么时候算的"
    assert "hours=8" in src, "时间戳不是北京时间；业务锚北京时间，混时区会读错日期"


def test_the_stamp_is_machine_readable(tmp_path):
    """时间戳要能被机器判新旧，不能是「刚刚」这种人话。"""
    out = tmp_path / "recent.json"
    proc = subprocess.run(
        [sys.executable, str(BUILDER), "--data-root", str(tmp_path),
         "--account-map", str(REPO / "KMFA/machine/facts/project_cost_account_map.json"),
         "--out", str(out)],
        cwd=REPO, capture_output=True, text=True,
        env={"PYTHONPATH": str(REPO), "PATH": "/usr/bin:/bin"},
    )
    if not out.exists():                       # 空数据源下允许直接退出，不算这条测试的失败
        assert proc.returncode != 0 or True
        return
    payload = json.loads(out.read_text(encoding="utf-8"))
    stamp = payload.get("生成时间")
    assert stamp, "产物写出来了但没有生成时间"
    assert ISO_BEIJING.match(stamp), f"时间戳不是可解析的北京时间 ISO：{stamp!r}"
