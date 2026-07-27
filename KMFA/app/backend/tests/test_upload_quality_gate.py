# -*- coding: utf-8 -*-
"""S06/P6.4 · T-S06-04 —— 上传并发、极限、恢复与滥用验收（S06 质量门）。

任务包原文：
  test：并发、慢速、断网、长时 soak、扫描积压、对象存储超时、配额竞争
  pass_gate：**阈值内 SLO 通过，数据不变量和隔离边界无失败**
  stop_condition：**测试显示可能损坏原件或跨 workspace 写入**

这一项和 P6.1–P6.3 的性质不同：那三项证明「功能对」，这一项证明
「**在真实失败和高负载下仍然对**」。所以每个场景都不是测功能，
而是测**在压力/故障中不变量还成不成立**。三条不变量贯穿全部场景：

  · 原件不被损坏——任何失败路径之后，既有 artifact 的摘要必须仍然对得上；
  · 隔离边界不被跨越——任何并发/竞争下，A 的字节不得进入 B 的 workspace；
  · 配额不被绕过——并发开会话时，各自看都在额度内、加起来超额，必须被挡住。

七个场景各自能击穿哪条不变量，写在各自的 docstring 里。
"""
from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from app import walking_skeleton as skeleton
from app.main import app
from app.upload_quarantine import EICAR

client = TestClient(app)
BASE = "/public-api/walking-skeleton/v1"


@pytest.fixture
def enabled_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    state = tmp_path / "walking-state"
    monkeypatch.setenv("KMFA_WALKING_SKELETON_ENABLED", "1")
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(state))
    monkeypatch.delenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", raising=False)
    return state


def _create(name="质量门"):
    response = client.post(f"{BASE}/workspaces", json={"project_name": name})
    assert response.status_code == 201, response.text
    payload = response.json()
    payload["_session_token"] = response.cookies.get(skeleton.SESSION_COOKIE_NAME)
    payload["_id"] = payload["workspace"]["workspace_id"]
    return payload


def _auth(ws):
    return {"Authorization": f"Bearer {ws['_session_token']}"}


def _open(ws, content: bytes, *, name="件.bin", media="application/octet-stream"):
    return client.post(
        f"{BASE}/workspaces/{ws['_id']}/artifact/uploads", headers=_auth(ws),
        json={"total_bytes": len(content), "content_sha256": hashlib.sha256(content).hexdigest(),
              "filename": quote(name), "media_type": media})


def _send_all(ws, upload_id, content, piece=2048):
    """按分片传完，返回最后一次响应。"""
    offset = 0
    last = None
    while offset < len(content):
        block = content[offset:offset + piece]
        last = client.patch(
            f"{BASE}/workspaces/{ws['_id']}/artifact/uploads/{upload_id}",
            headers={**_auth(ws), "Upload-Offset": str(offset),
                     "Chunk-SHA256": hashlib.sha256(block).hexdigest()},
            content=block)
        if last.status_code != 200:
            return last
        offset = last.json()["received_bytes"]
    return last


def _complete(ws, upload_id, key):
    return client.post(
        f"{BASE}/workspaces/{ws['_id']}/artifact/uploads/{upload_id}/complete",
        headers={**_auth(ws), "Idempotency-Key": key})


def _artifact(ws):
    return client.get(f"{BASE}/workspaces/{ws['_id']}", headers=_auth(ws)).json()["artifact"]


def _upload_one(ws, content, key, name="件.bin", media="application/octet-stream"):
    opened = _open(ws, content, name=name, media=media)
    if opened.status_code != 201:
        return opened
    body = opened.json()
    if not body.get("accept_bytes"):
        return opened
    sent = _send_all(ws, body["upload_id"], content)
    if sent is not None and sent.status_code != 200:
        return sent
    return _complete(ws, body["upload_id"], key)


# ─────────────── 场景①：并发 ───────────────

def test_concurrent_uploads_to_one_workspace_never_produce_a_corrupt_artifact(enabled_store):
    """并发能击穿的是「原件不被损坏」：多个请求同时写同一个 workspace，
    如果落库不是原子的，会留下一个摘要对不上的 artifact。

    这里不要求全部成功——artifact 上限本来就是 1，多数会被 409 挡住。
    要求的是：**成功的那个必须完好，失败的一个字节都不许留下。**
    """
    ws = _create()
    payloads = [bytes([i]) * 4096 for i in range(6)]
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(
            lambda t: _upload_one(ws, t[1], f"concurrent-upload-key-{t[0]:02d}"),
            enumerate(payloads)))
    codes = [r.status_code for r in results]
    assert any(c == 200 for c in codes), f"并发下一个都没成功不正常：{codes}"

    artifact = _artifact(ws)
    assert artifact is not None
    assert artifact["sha256"] in {hashlib.sha256(p).hexdigest() for p in payloads}, \
        "落库的摘要不属于任何一个真实上传——原件被损坏了"
    assert artifact["size_bytes"] == 4096


# ─────────────── 场景②：配额竞争 ───────────────

def test_concurrent_sessions_cannot_collectively_exceed_the_quota(enabled_store):
    """配额竞争击穿的是「配额不被绕过」。

    每个会话单看都在额度内，加起来超额——如果开会话时不把
    **未完成会话的已声明字节**算进占用，它们会全部被放行。
    """
    ws = _create()
    huge = 6 * 1024 * 1024                       # 单个合法（上限 8MiB）
    opened = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        opened = list(pool.map(
            lambda i: client.post(
                f"{BASE}/workspaces/{ws['_id']}/artifact/uploads", headers=_auth(ws),
                json={"total_bytes": huge, "content_sha256": f"{i:064x}",
                      "filename": quote(f"大{i}.bin"),
                      "media_type": "application/octet-stream"}),
            range(100)))
    admitted = [r for r in opened if r.status_code == 201 and r.json().get("accept_bytes")]
    reserved = len(admitted) * huge
    assert reserved <= skeleton.MAX_TOTAL_ARTIFACT_BYTES, (
        f"放行了 {len(admitted)} 个会话共声明 {reserved} 字节，"
        f"超过总额度 {skeleton.MAX_TOTAL_ARTIFACT_BYTES}——配额被并发绕过了")
    assert any(r.status_code == 429 for r in opened), "总该有会话被额度挡下"


# ─────────────── 场景③：断网（多点中断恢复） ───────────────

def test_interrupting_at_every_boundary_still_yields_a_byte_exact_artifact(enabled_store):
    """断网击穿的是「原件不被损坏」：续传接错位置会产出一个能完成、
    但内容不对的 artifact——而它的摘要检查会挡住，前提是摘要真的在查。
    """
    ws = _create()
    content = bytes((i * 13 + 5) % 251 for i in range(12_000))
    digest = hashlib.sha256(content).hexdigest()
    upload_id = _open(ws, content).json()["upload_id"]

    piece = 1500
    offset = 0
    while offset < len(content):
        # 每一片之后都「断线」：丢掉客户端状态，重新问服务端偏移
        status = client.get(
            f"{BASE}/workspaces/{ws['_id']}/artifact/uploads/{upload_id}", headers=_auth(ws))
        assert status.status_code == 200
        offset = status.json()["received_bytes"]
        if offset >= len(content):
            break
        block = content[offset:offset + piece]
        sent = client.patch(
            f"{BASE}/workspaces/{ws['_id']}/artifact/uploads/{upload_id}",
            headers={**_auth(ws), "Upload-Offset": str(offset),
                     "Chunk-SHA256": hashlib.sha256(block).hexdigest()},
            content=block)
        assert sent.status_code == 200, sent.text

    done = _complete(ws, upload_id, "interrupted-every-boundary")
    assert done.status_code == 200, done.text
    assert _artifact(ws)["sha256"] == digest


# ─────────────── 场景④：慢速（分片极小） ───────────────

def test_a_very_slow_upload_still_completes_and_holds_no_lock(enabled_store):
    """慢速击穿的是可用性：如果一次上传全程持锁，一个慢客户端就能拖死别人。

    这里用「极小分片、很多次请求」模拟慢速；期间另一个 workspace 必须照常可用。
    """
    slow = _create("慢速")
    other = _create("并行者")
    content = b"s" * 900
    upload_id = _open(slow, content).json()["upload_id"]

    offset = 0
    while offset < len(content):
        block = content[offset:offset + 30]        # 30 字节一片，30 次请求
        sent = client.patch(
            f"{BASE}/workspaces/{slow['_id']}/artifact/uploads/{upload_id}",
            headers={**_auth(slow), "Upload-Offset": str(offset),
                     "Chunk-SHA256": hashlib.sha256(block).hexdigest()},
            content=block)
        assert sent.status_code == 200
        offset = sent.json()["received_bytes"]
        if offset == 300:                          # 传到一半时，别人必须没被挡住
            assert client.get(f"{BASE}/workspaces/{other['_id']}",
                              headers=_auth(other)).status_code == 200

    assert _complete(slow, upload_id, "very-slow-upload-key").status_code == 200


# ─────────────── 场景⑤：扫描积压（大量恶意样本） ───────────────

def test_a_backlog_of_malicious_uploads_lands_nothing(enabled_store):
    """扫描积压击穿的是「恶意逃逸=0」：压力之下如果扫描被跳过或降级，
    就会有样本混进去。这里连续投递多个不同形态的恶意样本。
    """
    ws = _create()
    hostile = [
        (EICAR, "样本.txt", "text/plain"),
        (b"MZ\x90\x00" + b"\x00" * 300, "图.png", "image/png"),
        (b"\x7fELF\x02" + b"\x00" * 300, "文档.pdf", "application/pdf"),
        (b"#!/bin/sh\nrm -rf /\n" + b"x" * 200, "脚本.txt", "text/plain"),
    ]
    for index, (payload, name, media) in enumerate(hostile):
        result = _upload_one(ws, payload, f"backlog-hostile-key-{index:02d}",
                             name=name, media=media)
        assert result.status_code == 422, f"{name} 没被拦住：{result.status_code}"
        assert result.json()["detail"] == "artifact_quarantined"
    assert _artifact(ws) is None, "积压之下仍有恶意样本落库"


# ─────────────── 场景⑥：对象存储超时/不可用 ───────────────

def test_storage_failure_leaves_no_half_written_artifact(enabled_store, monkeypatch):
    """对象存储故障击穿的是「原件不被损坏」：如果失败路径留下半成品，
    下一次读取会拿到一个摘要对不上的对象。
    """
    ws = _create()
    content = b"z" * 2048
    upload_id = _open(ws, content).json()["upload_id"]
    _send_all(ws, upload_id, content)

    def boom(*args, **kwargs):
        raise skeleton.ObjectStorageUnavailableError("模拟对象存储不可用")

    monkeypatch.setattr(skeleton, "configured_write_store", boom)
    done = _complete(ws, upload_id, "storage-unavailable-key")
    assert done.status_code == 503, done.text
    assert _artifact(ws) is None, "存储失败后不许留下任何 artifact"


# ─────────────── 场景⑦：跨 workspace（stop_condition） ───────────────

def test_bytes_never_cross_into_another_workspace(enabled_store):
    """stop_condition 明写「测试显示可能跨 workspace 写入」即停止。

    这一条是硬边界：拿着 A 的会话 id 用 B 的凭据推字节，必须完全无效，
    且 A 的进度不受任何影响。
    """
    owner = _create("持有者")
    intruder = _create("入侵者")
    content = b"owner-bytes" * 100
    upload_id = _open(owner, content).json()["upload_id"]

    block = content[:512]
    for target in (intruder["_id"], owner["_id"]):
        response = client.patch(
            f"{BASE}/workspaces/{target}/artifact/uploads/{upload_id}",
            headers={**_auth(intruder), "Upload-Offset": "0",
                     "Chunk-SHA256": hashlib.sha256(block).hexdigest()},
            content=block)
        assert response.status_code == 404, (
            f"入侵者用自己的凭据推进了 {target} 的会话：{response.status_code}")

    status = client.get(f"{BASE}/workspaces/{owner['_id']}/artifact/uploads/{upload_id}",
                        headers=_auth(owner))
    assert status.json()["received_bytes"] == 0, "持有者的进度被外人改动了"
    assert _artifact(intruder) is None and _artifact(owner) is None


# ─────────────── 场景⑧：长时 soak（连续多轮不退化） ───────────────

def test_repeated_cycles_do_not_degrade_or_leak_state(enabled_store):
    """soak 击穿的是状态泄漏：会话 sidecar、暂存文件、配额预留
    如果哪一样没被回收，跑够多轮之后就会开不出新会话。

    每轮用一个独立 workspace，模拟持续使用。
    """
    for round_index in range(12):
        ws = _create(f"soak-{round_index}")
        content = bytes([round_index % 251]) * 1024
        result = _upload_one(ws, content, f"soak-cycle-key-{round_index:03d}")
        assert result.status_code == 200, f"第 {round_index} 轮就失败了：{result.text}"
        assert _artifact(ws)["sha256"] == hashlib.sha256(content).hexdigest()


def test_originals_survive_every_failure_path(enabled_store):
    """总不变量：把上面能触发的失败路径都跑一遍之后，
    先存进去的那个原件必须**仍然完好**——摘要与大小逐一对得上。
    """
    ws = _create("原件守恒")
    good = b"g" * 3000
    assert _upload_one(ws, good, "baseline-good-upload-key").status_code == 200
    before = _artifact(ws)

    _upload_one(ws, EICAR, "after-eicar-attempt-key", name="e.txt", media="text/plain")
    _upload_one(ws, b"MZ\x90\x00" * 50, "after-spoof-attempt-key",
                name="p.png", media="image/png")
    _open(ws, b"x" * (9 * 1024 * 1024))          # 超限，开会话即拒

    after = _artifact(ws)
    assert after == before, f"原件在失败路径之后被改动了：{before} → {after}"
