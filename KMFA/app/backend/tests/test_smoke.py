from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_status_header_triplet():
    r = client.get("/api/状态")
    assert r.status_code == 200
    header = r.json()["页眉"]
    assert set(header) == {"质量等级", "报告等级", "GO状态"}


def test_assertions_counts():
    r = client.get("/api/断言")
    assert r.status_code == 200
    d = r.json()
    assert d["total"] == d["closed"] + d["analyzed_open"] and d["total"] >= 15


def test_skills_registry():
    """技能数须与 registry.yaml 实际登记数一致。

    原断言硬编码 8，登记册增到 9（#113 项目成本表技能）后即过期误报——
    改为对齐真实登记册，杜绝再次因新增技能而假失败。
    """
    import re
    from pathlib import Path

    registry = Path(__file__).resolve().parents[3] / "skills" / "registry.yaml"
    block = registry.read_text(encoding="utf-8").split("\nschedules:")[0]
    registered = len(re.findall(r"^  - id: (.+)$", block, re.M))

    r = client.get("/api/技能")
    assert r.status_code == 200
    assert r.json()["count"] == registered, f"API {r.json()['count']} != 登记册 {registered}"
    assert registered >= 8


def test_skills_enriched_fields():
    rows = client.get("/api/技能").json()["skills"]
    assert all(x["名称"] and x["用途"] for x in rows)
    attendance = next(x for x in rows if x["id"] == "kmfa-dingtalk-attendance-skill")
    assert attendance["名称"] == "钉钉考勤"
    assert "kmfa-attendance-morning" in attendance["排程"]
    assert attendance["外部依赖"] and "dws" in attendance["外部依赖"][0]
    assert isinstance(attendance["本地路径硬编码"], int)


def test_index_serves_dashboard():
    # 根路径必须直达应用本体（307 → /ui/），不许再出现早期静态摘要页
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 307 and r.headers["location"] == "/ui/"
    r = client.get("/")
    assert r.status_code == 200 and "KMFA 经营分析" in r.text and "root" in r.text


def test_react_ui_served():
    r = client.get("/ui/")
    assert r.status_code == 200 and "root" in r.text


def test_schedule_health_full_history(tmp_path, monkeypatch):
    """台账全量历史：不止最新一条——次数/成功率/连续失败/历史列表都要有（Owner 2026-07-21）。"""
    from app import main as m
    ledger = tmp_path / "ledger.jsonl"
    logs = tmp_path / "attendance-morning"
    logs.mkdir()
    rows = [
        '{"ts":"2026-07-19T10:39:00+08:00","skill":"attendance-morning","rc":0,"log":"%s","delivery_enabled":"0"}' % (logs / "a.log"),
        '{"ts":"2026-07-20T10:39:00+08:00","skill":"attendance-morning","rc":1,"log":"%s","delivery_enabled":"1"}' % (logs / "b.log"),
        '{"ts":"2026-07-21T10:39:00+08:00","skill":"attendance-morning","rc":0,"log":"%s","delivery_enabled":"1"}' % (logs / "c.log"),
    ]
    ledger.write_text("\n".join(rows) + "\n", encoding="utf-8")
    monkeypatch.setattr(m, "SKILL_LEDGER_PATH", ledger)
    d = client.get("/api/排程健康").json()
    行 = next(x for x in d["逐项"] if x["技能"] == "attendance-morning")
    assert 行["次数"] == 3 and 行["失败次数"] == 1 and 行["成功率"] == 67
    assert 行["连续失败"] == 0 and 行["业务模块"] == "考勤与日检"
    assert [h["ts"][:10] for h in 行["历史"]] == ["2026-07-21", "2026-07-20", "2026-07-19"]
    assert 行["历史"][1]["成功"] is False


def test_schedule_snapshot_guarded(tmp_path, monkeypatch):
    """快照端点：目录内可读、目录外与穿越一律 404。"""
    from app import main as m
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("", encoding="utf-8")
    snap = tmp_path / "attendance-morning" 
    snap.mkdir()
    f = snap / "20260721_103900.log"
    f.write_text("开始\n结束 rc=0\n", encoding="utf-8")
    outside = tmp_path.parent / "outside.log"
    outside.write_text("秘密", encoding="utf-8")
    monkeypatch.setattr(m, "SKILL_LEDGER_PATH", ledger)
    ok = client.get("/api/排程健康/快照", params={"log": str(f)})
    assert ok.status_code == 200 and "rc=0" in ok.json()["内容"] and ok.json()["截取"] is False
    assert client.get("/api/排程健康/快照", params={"log": str(outside)}).status_code == 404
    assert client.get("/api/排程健康/快照", params={"log": str(snap / ".." / ".." / "outside.log")}).status_code == 404

