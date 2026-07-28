# -*- coding: utf-8 -*-
"""上游归档不该被一个**可选**的验证步骤杀死。

2026-07-28 线上实测：`im/search_groups` 持续返回「系统繁忙」，45 次运行全撞同一个
错，重试（3 次 / 退避 5s）也全部撞上——是持续性故障，不是限流。而 `chat group
list-all` 一直正常。

关键在于 `chat search` 在 `resolve_group` 里并不是必需的：群的 openConversationId
已经由 `bootstrap_groups_cloud.sh` 用 `chat group list-all` 写进配置，search 只承担
交叉验证和补 title/memberCount。让一个可选步骤有权 abort 整条归档链，是单点。

这组测试钉死降级的边界——降级要降对地方：
  · 「查不到」→ 有配置 ID 就接着干；
  · 「查到了但和配置不一致」→ 必须停，那是真冲突，继续会往错的群里写；
  · 「查不到且没有配置 ID」→ 必须停，确实走不下去。
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]
                       / "skills" / "上游归档" / "scripts"))
import archive_dingtalk_all_files as A  # noqa: E402

BUSY = ("{\"error\": {\"category\": \"api\", \"message\": "
        "\"[UNCLASSIFIED] 系统繁忙，请稍后再试 (operation: im/search_groups)\"}}")

GROUP = {"canonical_name": "付款请示群", "aliases": ["付款请示"],
         "open_conversation_id": "cidCONFIGUREDxxxxxxxxxxxx"}


def _dws(returncode, stdout="", stderr=""):
    return lambda *a, **k: subprocess.CompletedProcess(["dws"], returncode, stdout, stderr)


def _found(conv_id, title="付款请示群", members=9):
    return json.dumps({"result": {"groups": [
        {"title": title, "openConversationId": conv_id, "memberCount": members}]}})


def test_search_outage_falls_back_to_the_configured_id(monkeypatch, capsys):
    """这就是线上那 45 次失败的形状——降级后必须能继续。"""
    monkeypatch.setattr(A, "run_dws", _dws(1, stderr=BUSY))
    resolved = A.resolve_group(GROUP)
    assert resolved["open_conversation_id"] == GROUP["open_conversation_id"]
    assert resolved["resolution_source"] == "configured_open_conversation_id"
    assert "GROUP_RESOLVE_FALLBACK" in capsys.readouterr().out


def test_fallback_leaves_member_count_unknown_not_zero(monkeypatch):
    """0 是「这个群没人」，None 是「这次没查」——两者含义相反，不能混。"""
    monkeypatch.setattr(A, "run_dws", _dws(1, stderr=BUSY))
    assert A.resolve_group(GROUP)["member_count"] is None


def test_no_configured_id_still_fails(monkeypatch):
    """没有 ID 就是真的走不下去——这时候不许放行。"""
    monkeypatch.setattr(A, "run_dws", _dws(1, stderr=BUSY))
    with pytest.raises(RuntimeError):
        A.resolve_group({"canonical_name": "某群", "aliases": []})


def test_a_working_search_still_cross_checks_the_id(monkeypatch):
    """search 能用时，交叉验证必须照旧生效——降级不等于把校验删了。"""
    monkeypatch.setattr(A, "run_dws", _dws(0, stdout=_found("cidOTHERxxxxxxxxxxxxxxxx")))
    with pytest.raises(RuntimeError, match="mismatch"):
        A.resolve_group(GROUP)


def test_a_matching_search_resolves_normally(monkeypatch):
    monkeypatch.setattr(A, "run_dws",
                        _dws(0, stdout=_found(GROUP["open_conversation_id"])))
    resolved = A.resolve_group(GROUP)
    assert resolved["resolution_source"] == "chat_search"
    assert resolved["member_count"] == 9


def test_busy_is_still_classified_as_retryable():
    """降级是兜底，不是取消重试——瞬时忙仍该先重试几次。"""
    assert A.dws_retryable_output(BUSY)
    assert not A.dws_retryable_output("permission denied")
