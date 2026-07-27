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
    missing = scheduled - set(main.SCHEDULE_CONTRACT)
    assert not missing, f"这些技能在排程表里跑，却不在健康面里，无人看得见：{sorted(missing)}"
    orphan = set(main.SCHEDULE_CONTRACT) - scheduled
    assert not orphan, f"这些技能登记了健康面却没有排程，会永远显示『从未跑过』：{sorted(orphan)}"


def test_every_scheduled_skill_has_a_module():
    missing = set(main.SCHEDULE_CONTRACT) - set(main.SKILL_MODULE)
    assert not missing, f"这些技能没有业务模块归属，战报里会掉队：{sorted(missing)}"
