# -*- coding: utf-8 -*-
"""公开技能健康端点的边界测试。

这个端点存在的唯一理由，是让「技能到底跑没跑」这件事**不需要凭据也能验证**
（Coolify 的 exec 404、logs 空、/api 在 Access 后面，而 Owner 明令不登录）。
所以要钉死两头：
  · 真的公开 —— 不在私有面后头，否则等于没做；
  · 只出运行事实 —— 一旦漏出业务数据或目录结构，公开就成了泄露。
"""
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import main
from app.main import app

client = TestClient(app)
# 仓内 KMFA 根：测试文件在 KMFA/app/backend/tests/ 下
ROOT_REPO = Path(__file__).resolve().parents[3]
URL = "/public-api/技能健康"


def _write_ledger(tmp_path: Path, rows: list[dict], monkeypatch) -> Path:
    p = tmp_path / "ledger.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                 encoding="utf-8")
    monkeypatch.setattr(main, "SKILL_LEDGER_PATH", p)
    return p


def test_is_publicly_reachable_not_behind_private_prefix():
    """路径必须落在公开命名空间；/api* 与 /ops* 在 Cloudflare Access 后面。"""
    assert URL.startswith("/public-api/")
    assert client.get(URL).status_code == 200


def test_missing_ledger_says_so_instead_of_pretending_healthy(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "SKILL_LEDGER_PATH", tmp_path / "nope.jsonl")
    body = client.get(URL).json()
    assert body["台账可读"] is False
    assert body["技能"] == []
    assert "原因" in body


def test_reports_last_run_and_exit_code(tmp_path, monkeypatch):
    skill = sorted(main.SCHEDULE_CONTRACT)[0]
    _write_ledger(tmp_path, [
        {"ts": "2026-07-27T08:00:00+08:00", "skill": skill, "rc": 1,
         "log": "/var/log/kmfa/x/1.log", "delivery_enabled": "0"},
        {"ts": "2026-07-27T09:00:00+08:00", "skill": skill, "rc": 0,
         "log": "/var/log/kmfa/x/2.log", "delivery_enabled": "1"},
    ], monkeypatch)
    row = next(r for r in client.get(URL).json()["技能"] if r["技能"] == skill)
    assert row["最近一次"] == "2026-07-27T09:00:00+08:00", "必须取最新一次，不是台账里的最后一行顺序"
    assert row["退出码"] == 0 and row["成功"] is True
    assert row["运行次数"] == 2


def test_never_leaks_log_paths_or_delivery_switch(tmp_path, monkeypatch):
    """日志路径会暴露目录结构，投递开关属运行策略——公开面都不能出。"""
    skill = sorted(main.SCHEDULE_CONTRACT)[0]
    _write_ledger(tmp_path, [
        {"ts": "2026-07-27T09:00:00+08:00", "skill": skill, "rc": 0,
         "log": "/var/log/kmfa/绝密目录/1.log", "delivery_enabled": "1"},
    ], monkeypatch)
    raw = client.get(URL).text
    assert "绝密目录" not in raw and "/var/log" not in raw
    assert "delivery" not in raw and "投递开关" not in raw


def test_never_run_skill_is_not_reported_as_healthy(tmp_path, monkeypatch):
    """零运行必须看得出来。历史上踩过『日志新鲜、退出码 0，但一个文件都没归档』的假绿。"""
    _write_ledger(tmp_path, [
        {"ts": "2026-07-27T09:00:00+08:00", "skill": sorted(main.SCHEDULE_CONTRACT)[0], "rc": 0},
    ], monkeypatch)
    body = client.get(URL).json()
    never = [r for r in body["技能"] if r["运行次数"] == 0]
    assert never, "样本失效：应有从未跑过的技能"
    assert all(r["成功"] is None and r["最近一次"] is None for r in never)


def test_response_is_not_cached():
    assert client.get(URL).headers.get("cache-control") == "no-store"


def test_every_scheduled_skill_is_visible():
    """排程表里有、健康面里没有 = 看不见的排程 = 事实上的假绿。

    实测踩到：dws-bootstrap-groups 在 crontab 里每周日跑，却不在 SCHEDULE_CONTRACT 里，
    于是「群清单自举到底跑没跑」长期无人可见——而上游归档正卡在它的产出上。
    本测试把 crontab 与健康面对齐，防止再漏登记。
    """
    import re
    cron = (ROOT_REPO / "deploy" / "skills-runtime" / "crontab.txt").read_text(encoding="utf-8")
    scheduled = set(re.findall(r"run_skill\.sh\s+([a-z0-9-]+)", cron))
    # daily-funds deliberately owns an isolated container/cron and cannot use
    # the shared skills ledger (otherwise it would inherit the very DWS state
    # the task contract forbids).  Its private schedule centre reads the
    # redacted projection status instead.  Still require an actual frozen cron
    # row here so the contract cannot be declared visible without a scheduler.
    daily_cron = (ROOT_REPO / "skills" / "每日资金" / "crontab.txt").read_text(encoding="utf-8")
    assert "*/15 * * * * root /opt/daily-funds/scripts/run_daily_funds.py poll" in daily_cron
    assert "* * * * * root /opt/daily-funds/scripts/run_daily_funds.py auth-probe" in daily_cron
    assert "0 * * * * root /opt/daily-funds/scripts/run_daily_funds.py keepalive" in daily_cron
    scheduled.add("daily-funds")
    missing = scheduled - set(main.SCHEDULE_CONTRACT)
    assert not missing, f"这些技能在排程表里跑，却不在健康面里，无人看得见：{sorted(missing)}"
    orphan = set(main.SCHEDULE_CONTRACT) - scheduled
    # 没有钟点的技能只有一种正当理由：它是**冷启动自举**——缺产物时才跑，
    # 有钟点反而有害（探测目标会真发消息，反复探测＝反复真发）。
    # 所以规则不是「都必须有 cron」，而是「没 cron 就必须自称自举、并且真的接在
    # entrypoint 的前置表里」。这比原来更严：光在契约里写「自举」而没接线，照样红。
    entrypoint = (ROOT_REPO / "deploy" / "skills-runtime" / "entrypoint.sh").read_text(encoding="utf-8")
    for skill in sorted(orphan):
        assert "自举" in str(main.SCHEDULE_CONTRACT.get(skill, "")), (
            f"{skill} 没有排程也没自称自举，会永远显示『从未跑过』")
        assert f"|{skill}" in entrypoint, (
            f"{skill} 自称冷启动自举，但没接进 entrypoint 的前置产物表——那它一次都不会跑")


def test_every_scheduled_skill_has_a_module():
    missing = set(main.SCHEDULE_CONTRACT) - set(main.SKILL_MODULE)
    assert not missing, f"这些技能没有业务模块归属，战报里会掉队：{sorted(missing)}"


# ——— 失败码：rc 只说「失败了」，失败码说「哪一种失败」———

def test_failure_code_is_served_so_a_failure_is_diagnosable_without_logging_in(tmp_path, monkeypatch):
    """考勤连续多天 rc=5，而 rc=5 对应十来种原因。没有失败码就只能改一版等一天。"""
    _write_ledger(tmp_path, [
        {"ts": "2026-07-27T10:35:00+08:00", "skill": "attendance-morning", "rc": 5,
         "code": "NOT_SENT_DWS_AUTH_REQUIRED"},
    ], monkeypatch)
    row = next(s for s in client.get(URL).json()["技能"] if s["技能"] == "attendance-morning")
    assert row["失败码"] == "NOT_SENT_DWS_AUTH_REQUIRED"


def test_successful_runs_carry_no_failure_code(tmp_path, monkeypatch):
    _write_ledger(tmp_path, [
        {"ts": "2026-07-27T10:35:00+08:00", "skill": "attendance-morning", "rc": 0, "code": ""},
    ], monkeypatch)
    row = next(s for s in client.get(URL).json()["技能"] if s["技能"] == "attendance-morning")
    assert row["失败码"] is None


def test_hostile_ledger_content_never_reaches_the_public_response(tmp_path, monkeypatch):
    """台账是**另一个容器**写的。它写坏了、被塞进业务文本，也绝不能顺着流出来。

    这不是假想：考勤日志里就有员工姓名和打卡明细，成本日志里有客户名和金额。
    """
    hostile = [
        "张霖泽 09:12 未打卡",                       # 员工姓名
        "武汉开明 合同 40960322.77",                  # 客户名 + 金额
        "/var/log/kmfa/attendance-morning/2026.log",  # 目录结构
        "ghp_AAAABBBBCCCCDDDDEEEEFFFFGGGGHHHH",       # 凭据
        "0123456789abcdef0123456789abcdef",           # 凭据
        {"不是": "字符串"},                            # 类型错乱
        None, "", "X", "a b c",
    ]
    _write_ledger(tmp_path, [
        {"ts": f"2026-07-27T10:0{i}:00+08:00", "skill": "attendance-morning", "rc": 5, "code": c}
        for i, c in enumerate(hostile)
    ], monkeypatch)
    text = client.get(URL).text
    for bad in ("张霖泽", "武汉开明", "40960322", "/var/log", "ghp_", "0123456789abcdef"):
        assert bad not in text, f"公开响应里出现了 {bad}"


def test_ledger_uplink_health_is_reported_because_it_fails_silently_by_design(tmp_path, monkeypatch):
    """回传失败绝不拖垮技能——代价是断了也没人发现。实测断了几十次无人察觉。"""
    monkeypatch.setattr(main, "LEDGER_UPLINK_STATUS_PATH", tmp_path / "nope.json")
    _write_ledger(tmp_path, [{"ts": "2026-07-27T10:35:00+08:00", "skill": "attendance-morning", "rc": 0}],
                  monkeypatch)
    assert client.get(URL).json()["台账回传"]["成功"] is False

    marker = tmp_path / "uplink.json"
    marker.write_text(json.dumps({"时间": "2026-07-27T17:00:00+08:00", "成功": True, "情况": "已回传"},
                                 ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(main, "LEDGER_UPLINK_STATUS_PATH", marker)
    assert client.get(URL).json()["台账回传"]["成功"] is True


def test_uplink_marker_is_not_echoed_wholesale(tmp_path, monkeypatch):
    """留痕文件也是别的容器写的，同样不当可信输入。"""
    marker = tmp_path / "uplink.json"
    marker.write_text(json.dumps(
        {"成功": True, "情况": "已回传", "token": "ghp_AAAABBBBCCCCDDDDEEEEFFFFGGGG",
         "客户": "武汉开明"}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(main, "LEDGER_UPLINK_STATUS_PATH", marker)
    _write_ledger(tmp_path, [{"ts": "2026-07-27T10:35:00+08:00", "skill": "attendance-morning", "rc": 0}],
                  monkeypatch)
    text = client.get(URL).text
    assert "ghp_" not in text and "武汉开明" not in text


def test_cron_only_variables_are_pinned_in_run_skill_not_only_in_compose():
    """cron **不继承容器 ENV**——只写在 compose 里的变量，定时运行时拿不到。

    2026-07-27 线上抓到的活例子：`KMFA_ATTENDANCE_RUNTIME_DIR` 只在 compose 里设，
    于是 entrypoint 触发的自举与冷启动重试都能读到持久卷、跑绿，
    而 cron 触发的定时运行退回镜像层默认路径、文件不在，报 NOTIFIER_CONFIG_MISSING。
    表现是「手动跑绿、到点跑红」，看起来像随机失败，其实是两条路径读了不同目录。

    这条锁住：凡是技能在 cron 下需要的变量，必须在 run_skill.sh 里显式 export，
    compose 只作为可覆盖的来源。少了这层，同一个坑会换个变量名再来一次。
    """
    run_skill = (ROOT_REPO / "deploy" / "skills-runtime" / "run_skill.sh").read_text(encoding="utf-8")
    for name in ("KMFA_ATTENDANCE_RUNTIME_DIR", "KMFA_FUND_VISION_OCR_COMMAND"):
        assert f'export {name}="${{{name}:-' in run_skill, (
            f"{name} 没在 run_skill.sh 里钉死——cron 跑的时候会拿不到它")
