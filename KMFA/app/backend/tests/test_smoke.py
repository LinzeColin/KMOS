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
    r = client.get("/api/技能")
    assert r.status_code == 200 and r.json()["count"] == 8


def test_skills_enriched_fields():
    rows = client.get("/api/技能").json()["skills"]
    assert all(x["名称"] and x["用途"] for x in rows)
    attendance = next(x for x in rows if x["id"] == "kmfa-dingtalk-attendance-skill")
    assert attendance["名称"] == "钉钉考勤"
    assert "kmfa-attendance-morning" in attendance["排程"]
    assert attendance["外部依赖"] and "dws" in attendance["外部依赖"][0]
    assert isinstance(attendance["本地路径硬编码"], int)


def test_index_serves_dashboard():
    r = client.get("/")
    assert r.status_code == 200 and "KMFA 经营分析" in r.text


def test_react_ui_served():
    r = client.get("/ui/")
    assert r.status_code == 200 and "root" in r.text
