# -*- coding: utf-8 -*-
"""TEST-DL-003 —— S07/P7.3 · T-S07-03 受控导出任务（AC-DL-003）。

AC-DL-003
  输入：同一幂等键、并发导出、取消、失败、超时、过期制品
  过程：创建 job、轮询状态、下载制品；重复和故障注入；观察预算和生命周期
  阈值：**同幂等键只产生一个业务结果；无界并发=0；取消/失败/过期状态确定；制品可验证**

T-S07-03
  pass_gate：有副作用 GET=0（见 TEST-DL-004）；同幂等键唯一结果；任务资源有上限
  stop_condition：无法区分旧 GET 是否已触发不可逆财务操作

## stop_condition 的处置，先说清楚

旧 `GET /api/报告中心/导出` 的副作用是往**只追加**的导出登记册写一条记录，
外加一条审计事件。它不动钱、不改财务事实，而且登记册每条都带 sha256——
**哪些导出发生过、内容是什么，逐条可查**。所以「无法区分是否已触发不可逆财务操作」
这个停止条件不成立，迁移可以进行。

如果它当初改的是财务事实，正确做法是先停在这里，而不是先迁移再对账。

## 「同幂等键只产生一个业务结果」要测两个方向

一个方向人人会测：同键同请求 ⇒ 不重复干活。
另一个方向常被漏掉：**同键不同请求 ⇒ 必须拒绝**。
漏掉它，幂等键就成了摆设——客户端复用一个键去要另一份报告，
系统「幂等地」返回上一份，它拿到一个**自己没要过的东西**，而且看不出异常。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import export_jobs as EJ
from app import main
from app.main import app

ORIGIN = "https://kmfa.test"
client = TestClient(app, base_url=ORIGIN, headers={"Origin": ORIGIN})

KEY_A = "export-job-key-alpha-0001"
KEY_B = "export-job-key-bravo-0002"


@pytest.fixture
def app_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """把状态目录指向临时目录。改模块常量而非环境变量：
    它们在 import 时就被读成常量了，改环境变量已经晚了。"""
    state = tmp_path / "app-state"
    state.mkdir(parents=True, exist_ok=True)
    for attribute, target in (
        ("APP_STATE_DIR", state),
        ("APP_DB_PATH", state / "kmfa_app_state.sqlite3"),
        ("EXPORT_REGISTRY_PATH", state / "report_export_records.jsonl"),
        ("APP_AUDIT_PATH", state / "audit_events.jsonl"),
    ):
        monkeypatch.setattr(main, attribute, target, raising=False)
    monkeypatch.delenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", raising=False)
    client.cookies.clear()
    return state


def _create(key: str | None, payload: dict, expect: int | None = 200):
    headers = {"Idempotency-Key": key} if key else {}
    response = client.post("/api/导出任务", headers=headers, json=payload)
    if expect is not None:
        assert response.status_code == expect, response.text
    return response


# ═════════ 阈值一：同幂等键只产生一个业务结果 ═════════

def test_same_key_same_request_does_no_work_twice(app_state):
    """重试不该花第二份 CPU，也不该多出第二条导出登记。"""
    first = _create(KEY_A, {"报告": 1, "格式": "html"})
    second = _create(KEY_A, {"报告": 1, "格式": "html"})

    assert first.json()["复用"] is False
    assert second.json()["复用"] is True, "同键同请求却重新干了一遍"
    assert first.json()["任务"]["job_id"] == second.json()["任务"]["job_id"]

    from app import app_state as st
    records = st.read(main.APP_DB_PATH, "export_records")
    assert len(records) == 1, f"同一个幂等键产生了 {len(records)} 条导出登记"


def test_same_key_different_request_is_refused_not_silently_reused(app_state):
    """**最重要的一条。**

    复用同一个键去要别的东西，绝不能「幂等地」返回上一份——
    那样客户端拿到的是它没要过的东西，而且一切看起来正常。
    """
    _create(KEY_A, {"报告": 1, "格式": "html"})
    conflict = _create(KEY_A, {"报告": 2, "格式": "html"}, expect=409)
    assert conflict.json()["detail"]["code"] == "idempotency_key_reused"

    # 格式不同同样算不同请求——同一份报告的 csv 和 html 是两个业务结果。
    other = _create(KEY_A, {"报告": 1, "格式": "csv"}, expect=409)
    assert other.json()["detail"]["code"] == "idempotency_key_reused"


def test_missing_or_short_idempotency_key_is_refused(app_state):
    """键太短会在不同客户端之间意外相撞，撞了的后果是有人拿到别人的导出。"""
    assert _create(None, {"报告": 1}, expect=422).json()["detail"]["code"] \
        == "idempotency_key_invalid"
    assert _create("short", {"报告": 1}, expect=422).json()["detail"]["code"] \
        == "idempotency_key_invalid"
    # 空格不合规。**用 ASCII 造这条**——HTTP 头本身就不允许非 ASCII，
    # 拿中文当输入测的是 httpx 的编码，不是本仓的校验。
    assert _create("has spaces here 0001", {"报告": 1}, expect=422).status_code == 422


def test_fingerprint_ignores_key_order(app_state):
    """字段顺序不同不算不同请求——否则正当重试会变成 409。"""
    a = EJ.request_fingerprint({"报告": 1, "格式": "html"})
    b = EJ.request_fingerprint({"格式": "html", "报告": 1})
    assert a == b
    assert a != EJ.request_fingerprint({"报告": 2, "格式": "html"})


def test_job_id_is_derived_not_random(app_state):
    """id 由 (owner, 键) 决定，不含随机数：
    「同键返回同一任务」因此不依赖任何查表是否成功。"""
    assert EJ.job_id_for("a", KEY_A) == EJ.job_id_for("a", KEY_A)
    assert EJ.job_id_for("a", KEY_A) != EJ.job_id_for("b", KEY_A), (
        "两个 owner 用同一个键就撞了——幂等键是客户端自己取的，不能假设全局唯一")
    assert EJ.job_id_for("a", KEY_A) != EJ.job_id_for("a", KEY_B)


# ═════════ 阈值二：无界并发 = 0 ═════════

def test_concurrency_is_bounded(app_state, monkeypatch):
    """导出要渲染报告，无上限时几个并发就能吃满 CPU。
    HTTP worker 数不算上限——它不区分请求贵不贵。"""
    monkeypatch.setattr(EJ, "MAX_CONCURRENT_JOBS", 0)
    refused = _create(KEY_A, {"报告": 1, "格式": "html"}, expect=429)
    assert refused.json()["detail"]["code"] == "export_concurrency_limit"


def test_job_quota_is_bounded(app_state, monkeypatch):
    monkeypatch.setattr(EJ, "MAX_JOBS_PER_OWNER", 0)
    refused = _create(KEY_A, {"报告": 1, "格式": "html"}, expect=429)
    assert refused.json()["detail"]["code"] == "export_job_quota_exhausted"


def test_limits_are_not_merely_declared(app_state):
    """守卫：上限被改成 0 或天文数字都等于没有上限。"""
    assert 0 < EJ.MAX_CONCURRENT_JOBS <= 16
    assert 0 < EJ.MAX_JOBS_PER_OWNER <= 10_000
    assert 0 < EJ.MAX_ARTIFACT_BYTES <= 512 * 1024 * 1024
    assert 0 < EJ.ARTIFACT_TTL_SECONDS <= 30 * 24 * 3600


# ═════════ 阈值三：取消 / 失败 / 过期状态确定 ═════════

def test_cancelling_a_finished_job_says_what_state_it_is_in(app_state):
    """只回「不能取消」而不说现在是什么，调用方只能猜——
    而猜错的方向通常是「再试一次」，把一次误操作变成一串。"""
    job_id = _create(KEY_A, {"报告": 1, "格式": "html"}).json()["任务"]["job_id"]
    response = client.post(f"/api/导出任务/{job_id}/取消")
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "export_job_already_terminal"
    assert "succeeded" in detail["message"], "没说清当前是什么状态"


def test_cancelling_a_missing_job_is_404_not_409(app_state):
    """「不存在」和「已终态」是两回事，混在一起会让人去查一个从未存在的任务。"""
    response = client.post("/api/导出任务/exp_no_such_job/取消")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "export_job_not_found"


def test_failed_job_records_why(app_state):
    """失败要落成事件。失败的任务和不存在的任务对调用方意味着完全不同的下一步。"""
    response = _create(KEY_A, {"报告": 1, "格式": "不存在的格式"}, expect=400)
    assert "格式须为" in str(response.json()["detail"])

    job_id = EJ.job_id_for("management", KEY_A)
    status = client.get(f"/api/导出任务/{job_id}")
    assert status.status_code == 200
    body = status.json()
    assert body["state"] == "failed"
    assert body["failure"], "失败了却没记原因——那正是排查时唯一有用的东西"


def test_artifact_of_a_failed_job_is_409_with_the_reason(app_state):
    _create(KEY_A, {"报告": 1, "格式": "不存在的格式"}, expect=400)
    job_id = EJ.job_id_for("management", KEY_A)
    response = client.get(f"/api/导出任务/{job_id}/制品")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "export_job_failed"


def test_expiry_is_computed_at_read_time_not_written_by_a_cron():
    """靠定时任务改状态的话，定时任务没跑的那段时间里，
    系统会拿着过期制品当有效的发。所以过期在读的时候算。"""
    job = {
        "job_id": "exp_x", "state": "succeeded",
        "artifact": {"produced_at_epoch": 1_000_000, "path": "/tmp/x"},
    }
    fresh = EJ.project(job, 1_000_000 + 10)
    assert fresh["state"] == "succeeded"
    assert fresh["artifact"]["available"] is True

    stale = EJ.project(job, 1_000_000 + EJ.ARTIFACT_TTL_SECONDS + 1)
    assert stale["state"] == "expired"
    assert stale["artifact"]["available"] is False


def test_a_failed_job_never_becomes_expired():
    """把失败也标成 expired 会掩盖失败原因。"""
    job = {"job_id": "exp_y", "state": "failed", "failure": "渲染炸了",
           "artifact": None}
    assert EJ.is_expired(job, 10**12) is False
    assert EJ.project(job, 10**12)["state"] == "failed"


def test_expired_artifact_download_is_410_not_404(app_state, monkeypatch):
    """410 说的是「曾经有、已经没了」，404 说的是「从来没有」。
    两者对调用方意味着不同的下一步:重新创建 vs 检查自己的 id。"""
    job_id = _create(KEY_A, {"报告": 1, "格式": "html"}).json()["任务"]["job_id"]
    monkeypatch.setattr(EJ, "ARTIFACT_TTL_SECONDS", -1)
    response = client.get(f"/api/导出任务/{job_id}/制品")
    assert response.status_code == 410
    assert response.json()["detail"]["code"] == "export_artifact_expired"


def test_terminal_state_is_terminal(app_state):
    """终态之后的事件必须被忽略而不是报错：重复取消、worker 崩溃后的迟到回报
    都会产生这种事件。抛异常会把一个已完成的任务变成读不出来的任务。"""
    events = [
        {"event": "created", "job_id": "j", "owner": "o", "idempotency_key": KEY_A,
         "fingerprint": "f", "request": {}, "at": "t0"},
        {"event": "started", "job_id": "j", "at": "t1"},
        {"event": "succeeded", "job_id": "j", "at": "t2", "artifact": {"sha256": "x"}},
        {"event": "cancelled", "job_id": "j", "at": "t3"},
        {"event": "failed", "job_id": "j", "at": "t4", "failure": "迟到的回报"},
    ]
    job = EJ.fold_job(events)
    assert job["state"] == "succeeded"
    assert job["artifact"] == {"sha256": "x"}
    assert job["failure"] is None


# ═════════ 阈值四：制品可验证 ═════════

def test_artifact_bytes_match_the_registered_hash(app_state):
    """自报 sha256 必须与实发字节对得上，否则登记册证明不了任何事。"""
    created = _create(KEY_A, {"报告": 1, "格式": "html"}).json()["任务"]
    job_id = created["job_id"]

    response = client.get(f"/api/导出任务/{job_id}/制品")
    assert response.status_code == 200, response.text
    actual = "sha256:" + hashlib.sha256(response.content).hexdigest()
    assert response.headers["X-KMFA-Sha256"] == actual
    assert created["artifact"]["sha256"] == actual


def test_artifact_is_always_an_attachment_and_never_cached(app_state):
    """与 T-S07-01 的下载侧同向：两个模块各判各的，某天一边放宽了另一边不知道。"""
    job_id = _create(KEY_A, {"报告": 1, "格式": "html"}).json()["任务"]["job_id"]
    response = client.get(f"/api/导出任务/{job_id}/制品")
    assert response.headers["Content-Disposition"].startswith("attachment")
    # 断言**性质**而不是精确字符串:中间件会追加 no-transform 之类更严的指令,
    # 精确匹配会在有人正确地把它变严时炸掉——那是把测试变成收紧的阻力。
    cache = response.headers["Cache-Control"]
    assert "no-store" in cache and "private" in cache, cache
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_watermark_and_grades_survive_to_the_artifact(app_state):
    """水印是给「这份报告能不能对外」下的结论。
    它必须跟着制品走——只在创建时算、下载时不带，等于没有。"""
    created = _create(KEY_A, {"报告": 1, "格式": "html"}).json()["任务"]
    response = client.get(f"/api/导出任务/{created['job_id']}/制品")
    assert response.headers["X-KMFA-Report-Grade"] == created["artifact"]["报告等级"]
    assert response.headers["X-KMFA-Quality-Grade"] == created["artifact"]["质量等级"]
    assert response.headers["X-KMFA-Watermark"] in {"applied", "none"}


def test_fingerprint_is_not_leaked_to_clients(app_state):
    """指纹是内部判据。露出去等于告诉别人怎么构造一次命中。"""
    body = _create(KEY_A, {"报告": 1, "格式": "html"}).json()["任务"]
    assert "fingerprint" not in body
    status = client.get(f"/api/导出任务/{body['job_id']}").json()
    assert "fingerprint" not in status


# ═════════ 兼容弃用：旧 GET 必须响亮地停用 ═════════

def test_the_old_get_export_is_retired_loudly(app_state):
    """迁移的已知风险是「旧客户端无提示失败」。
    410 是响亮的失败,且响应体直说替代路径怎么调。"""
    response = client.get("/api/报告中心/导出", params={"报告": 1, "格式": "html"})
    assert response.status_code == 410
    detail = response.json()["detail"]
    assert detail["code"] == "export_get_retired"
    replacement = detail["replacement"]
    assert "POST /api/导出任务" in replacement["创建"]
    assert "Idempotency-Key" in replacement["创建"], "没说清还要带幂等键"
    assert "/api/导出任务/{job_id}/制品" in replacement["取制品"]


def test_the_retired_get_writes_nothing(app_state):
    """停用的端点必须**真的**什么都不写——
    留一半副作用比留全部更难查。"""
    from app import app_state as st
    before = len(st.read(main.APP_DB_PATH, "export_records"))
    for _ in range(5):
        client.get("/api/报告中心/导出", params={"报告": 1, "格式": "html"})
    assert len(st.read(main.APP_DB_PATH, "export_records")) == before
