# -*- coding: utf-8 -*-
"""私有库「够不着」的所有形态都必须归成 Unavailable。

2026-07-28 线上实测：`git checkout --quiet` 在稀疏克隆时 120s 超时，抛的是
`subprocess.TimeoutExpired`——它不是 `Unavailable`，于是一路穿过 `lineage_graph`
的 `except ManifestUnavailable` 变成裸 traceback。表现是 self-audit rc=1、失败码
`UNKNOWN`，看的人只能猜。

这件事的要害不是「超时」，是**已知状态被退化成未知故障**：调用方对「读不到」
有正经处理（如实说读不到，绝不当成「没有资产」判 FRESH），而绕开那条路等于
把设计好的降级作废。

所以两道都测：源头按类型归类，下游再兜一层任何未预期的形态。
"""
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import private_db_access as PDB  # noqa: E402
import lineage_graph as L  # noqa: E402


def test_a_git_timeout_is_reported_as_unavailable(monkeypatch):
    def boom(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["git", "checkout"], timeout=120)
    monkeypatch.setattr(PDB.subprocess, "run", boom)
    with pytest.raises(PDB.Unavailable) as caught:
        PDB._git(["checkout", "--quiet"])
    assert "超时" in str(caught.value)


def test_a_git_failure_is_still_unavailable(monkeypatch):
    monkeypatch.setattr(PDB.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(
        ["git"], 128, stdout="", stderr="fatal: could not read from remote"))
    with pytest.raises(PDB.Unavailable):
        PDB._git(["clone"])


def test_checkout_gets_a_bigger_budget_than_the_default():
    """checkout 是唯一要落盘的一步——blob 到这里才真正下载，120s 不够。"""
    assert PDB.CHECKOUT_TIMEOUT_SECONDS > 120


def test_secrets_never_reach_the_error_text(monkeypatch):
    """错误串会进台账；stderr 截断到 200 字，且不该带密钥本体。"""
    monkeypatch.setattr(PDB.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(
        ["git"], 1, stdout="", stderr="x" * 5000))
    with pytest.raises(PDB.Unavailable) as caught:
        PDB._git(["clone"])
    assert len(str(caught.value)) < 300


@pytest.mark.parametrize("error", [
    subprocess.TimeoutExpired(cmd=["git"], timeout=120),
    OSError("磁盘满"),
    RuntimeError("将来某种新形态"),
])
def test_lineage_turns_any_unreachable_form_into_manifest_unavailable(monkeypatch, error):
    """下游那道兜底：任何意外形态都表现成「读不到」，不炸掉整条自检链。"""
    import private_db_access
    monkeypatch.setattr(private_db_access, "read_text",
                        lambda *a, **k: (_ for _ in ()).throw(error))
    with pytest.raises(L.ManifestUnavailable):
        L._load_raw_from_private_db()


def test_unreachable_is_never_mistaken_for_no_assets(monkeypatch, capsys):
    """读不到绝不能判 FRESH——那是拿沉默充好消息，也是这条链最贵的一种错。"""
    monkeypatch.setattr(L, "load_raw", lambda: (_ for _ in ()).throw(
        L.ManifestUnavailable("git checkout 超时（300s）")))
    assert L.cmd_stale() == 3
    assert "MANIFEST_UNAVAILABLE" in capsys.readouterr().out
