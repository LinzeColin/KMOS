# -*- coding: utf-8 -*-
"""TEST-UP-002 的 HTTP 层：真走接口的断点续传流程。

模块级单测证明的是**判定逻辑**对；这一份证明**接线**也对——
路由、鉴权、会话持久化、偏移回报串起来确实能续传。
两层都要有：判定对而接线错，产品照样不能用，而这种错只有走接口才暴露。
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from app import walking_skeleton as skeleton
from app.main import app

client = TestClient(app)
BASE = "/public-api/walking-skeleton/v1"


@pytest.fixture
def enabled_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    state = tmp_path / "walking-state"
    monkeypatch.setenv("KMFA_WALKING_SKELETON_ENABLED", "1")
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(state))
    monkeypatch.delenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", raising=False)
    return state


def _create() -> dict:
    response = client.post(f"{BASE}/workspaces", json={"project_name": "续传验收"})
    assert response.status_code == 201, response.text
    payload = response.json()
    payload["_session_token"] = response.cookies.get(skeleton.SESSION_COOKIE_NAME)
    return payload


def _auth(created: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {created['_session_token']}"}


def _open(created, *, content: bytes, name: str = "样本.bin", media: str = "application/octet-stream"):
    return client.post(
        f"{BASE}/workspaces/{created['workspace']['workspace_id']}/artifact/uploads",
        headers=_auth(created),
        json={"total_bytes": len(content), "content_sha256": hashlib.sha256(content).hexdigest(),
              "filename": quote(name), "media_type": media},
    )


def test_open_then_resume_from_the_reported_offset(enabled_store):
    """AC-UP-002 恢复 100%：断在中间，用服务端报的偏移续上，最终字节一致。"""
    created = _create()
    content = bytes((i * 31 + 7) % 251 for i in range(9000))
    opened = _open(created, content=content)
    assert opened.status_code == 201, opened.text
    upload_id = opened.json()["upload_id"]
    assert opened.json()["accept_bytes"] is True

    piece = 3000
    first = content[:piece]
    sent = client.patch(
        f"{BASE}/workspaces/{created['workspace']['workspace_id']}/artifact/uploads/{upload_id}",
        headers={**_auth(created), "Upload-Offset": "0",
                 "Chunk-SHA256": hashlib.sha256(first).hexdigest()},
        content=first)
    assert sent.status_code == 200, sent.text
    assert sent.json()["received_bytes"] == piece

    # 模拟断线：客户端什么都不记得了，只能问服务端
    status = client.get(
        f"{BASE}/workspaces/{created['workspace']['workspace_id']}/artifact/uploads/{upload_id}",
        headers=_auth(created))
    assert status.status_code == 200
    offset = status.json()["received_bytes"]
    assert offset == piece, "服务端必须如实报出已收字节，否则续传无从谈起"

    while offset < len(content):
        block = content[offset:offset + piece]
        sent = client.patch(
            f"{BASE}/workspaces/{created['workspace']['workspace_id']}/artifact/uploads/{upload_id}",
            headers={**_auth(created), "Upload-Offset": str(offset),
                     "Chunk-SHA256": hashlib.sha256(block).hexdigest()},
            content=block)
        assert sent.status_code == 200, sent.text
        offset = sent.json()["received_bytes"]
    assert offset == len(content)


def test_a_tampered_chunk_is_refused_over_http(enabled_store):
    """AC-UP-002 篡改漏检=0——接线层也必须拦住，不能只有模块里拦。"""
    created = _create()
    content = b"x" * 512
    upload_id = _open(created, content=content).json()["upload_id"]
    honest = content[:256]
    sent = client.patch(
        f"{BASE}/workspaces/{created['workspace']['workspace_id']}/artifact/uploads/{upload_id}",
        headers={**_auth(created), "Upload-Offset": "0",
                 "Chunk-SHA256": hashlib.sha256(b"y" * 256).hexdigest()},
        content=honest)
    assert sent.status_code == 422 and sent.json()["detail"] == "chunk_checksum_mismatch"

    status = client.get(
        f"{BASE}/workspaces/{created['workspace']['workspace_id']}/artifact/uploads/{upload_id}",
        headers=_auth(created))
    assert status.json()["received_bytes"] == 0, "被拒的片不许推进进度"


def test_oversize_is_refused_at_open_not_mid_stream(enabled_store):
    """AC-UP-002 超限在写入预算前拒绝——开会话就 413，不必先传一半。"""
    created = _create()
    opened = client.post(
        f"{BASE}/workspaces/{created['workspace']['workspace_id']}/artifact/uploads",
        headers=_auth(created),
        json={"total_bytes": 9 * 1024 * 1024, "content_sha256": "a" * 64,
              "filename": quote("大.bin"), "media_type": "application/octet-stream"})
    assert opened.status_code == 413 and opened.json()["detail"] == "artifact_too_large"


def test_offset_conflict_is_reported_so_the_client_can_resync(enabled_store):
    created = _create()
    content = b"z" * 400
    upload_id = _open(created, content=content).json()["upload_id"]
    block = content[:100]
    sent = client.patch(
        f"{BASE}/workspaces/{created['workspace']['workspace_id']}/artifact/uploads/{upload_id}",
        headers={**_auth(created), "Upload-Offset": "50",
                 "Chunk-SHA256": hashlib.sha256(block).hexdigest()},
        content=block)
    assert sent.status_code == 409 and sent.json()["detail"] == "upload_offset_conflict"


def test_another_workspace_cannot_touch_the_session(enabled_store):
    """跨 workspace 读会话是跨租户泄露——按不存在处理，不透露它存在。"""
    owner = _create()
    intruder = _create()
    upload_id = _open(owner, content=b"secret bytes").json()["upload_id"]
    probe = client.get(
        f"{BASE}/workspaces/{intruder['workspace']['workspace_id']}/artifact/uploads/{upload_id}",
        headers=_auth(intruder))
    assert probe.status_code == 404 and probe.json()["detail"] == "upload_session_not_found"


def test_session_requires_authorization(enabled_store):
    """无凭据必须拿不到会话。

    这里断言的是 **404 而不是 401/403**，而且 404 才是更强的那个：
    401/403 等于确认「这个 workspace 存在，只是你没权限」——
    未认证的人连这一点都不该知道。既有 `_authorize` 就是这么设计的，
    本端点复用它而不另起一套，正是为了不在新路由上开一个存在性泄露的口子。
    """
    created = _create()
    upload_id = _open(created, content=b"abc").json()["upload_id"]
    probe = client.get(
        f"{BASE}/workspaces/{created['workspace']['workspace_id']}/artifact/uploads/{upload_id}")
    assert probe.status_code == 404 and probe.json()["detail"] == "workspace_not_found"


# ─────────────── T-S06-01 的 pass_gate：完成 → 真产出 artifact ───────────────

def test_resumable_upload_completes_into_a_real_artifact(enabled_store):
    """端到端：分片传完 → complete → workspace 上真的出现这个 artifact。

    这一条是 T-S06-01 的过关判据。前面那些证明「传得进来」，
    只有这一条证明「传进来的东西变成了产品里的对象」——
    少了它，续传就是一条通往暂存目录的死路。
    """
    created = _create()
    workspace_id = created["workspace"]["workspace_id"]
    content = bytes((i * 17 + 3) % 251 for i in range(7000))
    digest = hashlib.sha256(content).hexdigest()
    upload_id = _open(created, content=content, name="成品.bin").json()["upload_id"]

    offset = 0
    while offset < len(content):
        block = content[offset:offset + 2500]
        sent = client.patch(
            f"{BASE}/workspaces/{workspace_id}/artifact/uploads/{upload_id}",
            headers={**_auth(created), "Upload-Offset": str(offset),
                     "Chunk-SHA256": hashlib.sha256(block).hexdigest()},
            content=block)
        assert sent.status_code == 200, sent.text
        offset = sent.json()["received_bytes"]

    done = client.post(
        f"{BASE}/workspaces/{workspace_id}/artifact/uploads/{upload_id}/complete",
        headers={**_auth(created), "Idempotency-Key": "resumable-complete-1"})
    assert done.status_code == 200, done.text

    # GET 直接返回 workspace 本体（POST 才嵌一层 "workspace"），别读错层
    workspace = client.get(f"{BASE}/workspaces/{workspace_id}",
                           headers=_auth(created)).json()
    artifact = workspace["artifact"]
    assert artifact is not None, "完成后 workspace 上必须真的出现 artifact"
    assert artifact["sha256"] == digest
    assert artifact["size_bytes"] == len(content)


def test_completing_a_half_sent_upload_produces_no_artifact(enabled_store):
    """没传完就完成，不能产出一个「看起来成功」的残缺对象。"""
    created = _create()
    workspace_id = created["workspace"]["workspace_id"]
    content = b"q" * 900
    upload_id = _open(created, content=content).json()["upload_id"]
    block = content[:300]
    client.patch(
        f"{BASE}/workspaces/{workspace_id}/artifact/uploads/{upload_id}",
        headers={**_auth(created), "Upload-Offset": "0",
                 "Chunk-SHA256": hashlib.sha256(block).hexdigest()},
        content=block)
    done = client.post(
        f"{BASE}/workspaces/{workspace_id}/artifact/uploads/{upload_id}/complete",
        headers={**_auth(created), "Idempotency-Key": "half-sent-upload-key"})
    assert done.status_code == 409 and done.json()["detail"] == "upload_incomplete"

    workspace = client.get(f"{BASE}/workspaces/{workspace_id}",
                           headers=_auth(created)).json()
    assert workspace["artifact"] is None, "残缺上传不许留下 artifact"


def test_duplicate_content_is_refused_bytes_at_open(enabled_store):
    """AC-UP-002 重复对象不可控增长=0——第二次传同样内容，一个字节都不收。"""
    created = _create()
    workspace_id = created["workspace"]["workspace_id"]
    content = b"duplicate me" * 40
    upload_id = _open(created, content=content).json()["upload_id"]
    client.patch(
        f"{BASE}/workspaces/{workspace_id}/artifact/uploads/{upload_id}",
        headers={**_auth(created), "Upload-Offset": "0",
                 "Chunk-SHA256": hashlib.sha256(content).hexdigest()},
        content=content)
    # 每一步都要断言。初版这里没断言，第一次 complete 因为幂等键太短而 422，
    # 于是根本没产生 artifact，去重当然查不到——**测试失败的原因和它想测的东西无关**。
    first = client.post(
        f"{BASE}/workspaces/{workspace_id}/artifact/uploads/{upload_id}/complete",
        headers={**_auth(created), "Idempotency-Key": "duplicate-first-upload"})
    assert first.status_code == 200, first.text

    again = _open(created, content=content)
    assert again.status_code == 201, again.text
    assert again.json()["accept_bytes"] is False
    assert again.json()["duplicate_of"], "必须指出复用的是哪个既有版本"
    assert again.json()["upload_id"] is None, "不开会话就等于不会收到任何字节"


# ─────────────── T-S06-02：quarantine-first 接线（AC-UP-003）───────────────

def test_a_malicious_upload_never_becomes_an_artifact(enabled_store):
    """AC-UP-003「恶意/畸形逃逸=0」的接线证明。

    quarantine-first 的含义是**判不干净就不进持久化链**，
    而不是「先存起来再打标记」——存下来的那一刻它就已经在系统里了。
    """
    from app.upload_quarantine import EICAR
    created = _create()
    workspace_id = created["workspace"]["workspace_id"]
    payload = EICAR
    digest = hashlib.sha256(payload).hexdigest()
    upload_id = _open(created, content=payload, name="样本.txt", media="text/plain").json()["upload_id"]
    sent = client.patch(
        f"{BASE}/workspaces/{workspace_id}/artifact/uploads/{upload_id}",
        headers={**_auth(created), "Upload-Offset": "0",
                 "Chunk-SHA256": digest},
        content=payload)
    assert sent.status_code == 200, "传输层不负责判恶意——它只管字节对不对"

    done = client.post(
        f"{BASE}/workspaces/{workspace_id}/artifact/uploads/{upload_id}/complete",
        headers={**_auth(created), "Idempotency-Key": "eicar-must-not-land"})
    assert done.status_code == 422 and done.json()["detail"] == "artifact_quarantined"

    workspace = client.get(f"{BASE}/workspaces/{workspace_id}",
                           headers=_auth(created)).json()
    assert workspace["artifact"] is None, "隔离的文件一个都不许出现在 workspace 上"


def test_mime_spoofed_upload_is_quarantined_over_http(enabled_store):
    """声明 png、内容是 PE 可执行——传输能过，落库不能过。"""
    created = _create()
    workspace_id = created["workspace"]["workspace_id"]
    payload = b"MZ\x90\x00" + b"\x00" * 200
    digest = hashlib.sha256(payload).hexdigest()
    upload_id = _open(created, content=payload, name="图.png", media="image/png").json()["upload_id"]
    client.patch(
        f"{BASE}/workspaces/{workspace_id}/artifact/uploads/{upload_id}",
        headers={**_auth(created), "Upload-Offset": "0", "Chunk-SHA256": digest},
        content=payload)
    done = client.post(
        f"{BASE}/workspaces/{workspace_id}/artifact/uploads/{upload_id}/complete",
        headers={**_auth(created), "Idempotency-Key": "spoofed-png-must-not-land"})
    assert done.status_code == 422 and done.json()["detail"] == "artifact_quarantined"
    assert client.get(f"{BASE}/workspaces/{workspace_id}",
                      headers=_auth(created)).json()["artifact"] is None
