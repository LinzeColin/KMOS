# -*- coding: utf-8 -*-
"""dws 数据授权请求做成自愈：卡住了自己去请求，静默期内不连发。

**这是同一件事的第二版，第一版线上没生效。**

第一版做成环境变量 `KMFA_DWS_DATA_AUTH_REQUEST`。排查到最后：开关在 Coolify
里、compose 里也声明了、部署用的确实是含改动的提交，但技能从没进过台账——
变量看着设了、实际没到容器。**这正是 `KMFA_BOOT_SWEEP` 那次的重演。**
仓里那条「开关必须声明进 compose」的门禁只能验仓里写没写，
验不了「Coolify 有没有重新读 compose」。

也没做成 App 上的按钮：那个面匿名可达，而「给 Owner 的钉钉弹窗」被反复触发
就是骚扰——**不该为了省事开一个陌生人能按的门。**

所以判据回到系统自己身上：upstream-archive 红着 = 授权断了 = 去请求一次；
外加静默期，防止技能一直红就一直弹。
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "KMFA/tools/should_request_dws_auth.py"
sys.path.insert(0, str(REPO / "KMFA/tools"))

import should_request_dws_auth as decider  # noqa: E402

NOW = "2026-07-29T16:00:00+08:00"


def _ledger(tmp_path: Path, rows: list[dict]) -> Path:
    p = tmp_path / "ledger.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                 encoding="utf-8")
    return p


def _decide(tmp_path, rows, *, state_ts: str | None = None, now: str = NOW):
    ledger = _ledger(tmp_path, rows)
    state = tmp_path / "last_request"
    if state_ts:
        state.write_text(state_ts, encoding="utf-8")
    return decider.decide(ledger=ledger, state=state, now=datetime.fromisoformat(now))


BLOCKED = {"skill": "upstream-archive", "rc": 1, "ts": "2026-07-29T15:00:00+08:00"}
HEALTHY = {"skill": "upstream-archive", "rc": 0, "ts": "2026-07-29T15:00:00+08:00"}


def test_it_asks_when_the_chain_is_actually_blocked(tmp_path):
    ok, why = _decide(tmp_path, [BLOCKED])
    assert ok, why


def test_it_stays_quiet_when_auth_is_working(tmp_path):
    """授权通着还弹窗 = 纯骚扰。"""
    ok, why = _decide(tmp_path, [HEALTHY])
    assert not ok
    assert "成功" in why, why


def test_it_does_not_ask_before_the_skill_has_ever_run(tmp_path):
    """没有「卡住」的证据就不打扰 Owner——沉默不等于故障。"""
    ok, why = _decide(tmp_path, [{"skill": "dws-keepalive", "rc": 0, "ts": NOW}])
    assert not ok
    assert "还没跑过" in why, why


def test_the_quiet_period_stops_it_from_spamming(tmp_path):
    """**本文件的正主。** 技能会一直红；不能因此每 10 分钟弹一次。"""
    ok, why = _decide(tmp_path, [BLOCKED], state_ts="2026-07-29T14:00:00+08:00")
    assert not ok, "静默期内又弹了一次"
    assert "静默" in why or "间隔" in why, why


def test_after_the_quiet_period_it_asks_again(tmp_path):
    """授权是会过期的。静默期一过就该再问一次，不能问一次就永远闭嘴。"""
    ok, why = _decide(tmp_path, [BLOCKED], state_ts="2026-07-29T05:00:00+08:00")
    assert ok, why


def test_a_corrupt_state_file_does_not_wedge_it_shut(tmp_path):
    """状态文件坏了不能变成「永远不再请求」——那会让整条链无声地卡死。"""
    ok, why = _decide(tmp_path, [BLOCKED], state_ts="不是时间")
    assert ok, why


def test_the_quiet_period_has_a_lower_bound():
    """没有下界 = 技能红着就一直弹，那是骚扰。"""
    assert 1.0 <= decider.MIN_INTERVAL_HOURS <= 24.0


def test_the_reason_is_always_printed(tmp_path):
    """「没请求」和「请求了但没反应」在日志里长得一样——理由必须写出来。"""
    ledger = _ledger(tmp_path, [HEALTHY])
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--ledger", str(ledger),
         "--state", str(tmp_path / "s"), "--now", NOW],
        capture_output=True, text=True, check=False)
    assert proc.returncode == 1
    assert proc.stderr.strip(), "拒绝了却没说为什么"


def test_mark_only_writes_when_it_actually_decides_to_ask(tmp_path):
    """判成「不请求」却写下时间戳，会把下一次真该请求的时机推掉。"""
    ledger = _ledger(tmp_path, [HEALTHY])
    state = tmp_path / "s"
    subprocess.run(
        [sys.executable, str(TOOL), "--ledger", str(ledger), "--state", str(state),
         "--now", NOW, "--mark"], capture_output=True, text=True, check=False)
    assert not state.exists(), "没请求却盖了时间戳——把下一次真请求推掉了"


def test_the_dead_env_switch_is_gone():
    """**不管用的开关比没有更糟**——真出事时会去按它。

    KMFA_DWS_DATA_AUTH_REQUEST 线上实证不生效，整条路必须删干净，
    不许在 entrypoint 或 compose 里留下半截。
    """
    entry = (REPO / "KMFA/deploy/skills-runtime/entrypoint.sh").read_text(encoding="utf-8")
    compose = (REPO / "KMFA/deploy/coolify/docker-compose.yml").read_text(encoding="utf-8")
    assert 'if [ "${KMFA_DWS_DATA_AUTH_REQUEST:-0}" = "1" ]' not in entry, \
        "entrypoint 里还留着那个不生效的开关"
    assert "KMFA_DWS_DATA_AUTH_REQUEST:" not in compose, "compose 里还留着它"


def test_the_entrypoint_actually_uses_the_decider():
    entry = (REPO / "KMFA/deploy/skills-runtime/entrypoint.sh").read_text(encoding="utf-8")
    assert "should_request_dws_auth.py" in entry, "判据没接进 entrypoint"
    assert "--mark" in entry, "没带 --mark，静默期永远不会生效——会变成每次部署都弹"
    assert "run_skill.sh dws-data-auth" in entry, "判成该请求了却没真去跑技能"
