# -*- coding: utf-8 -*-
"""TEST-DL-001 —— S07/P7.1 · T-S07-01 原件、派生物和报告下载。

AC-DL-001
  输入：原件、预览、派生文件、报告，含 **Unicode/特殊字符文件名**
  过程：下载后比较字节、Content-Type、Content-Disposition、大小、checksum 和来源信息
  阈值：**可用制品 100% 下载；字节/元数据不一致 = 0；高风险格式不内联**

T-S07-01
  pass_gate：可用制品下载率 100%，**字节不一致=0，越权=0**
  stop_condition：**下载 URL 可被枚举或长期绕过 workspace/发布权限**

「字节不一致=0」这条要用**逐字节比对**证，不能只比大小或只比 checksum：
  · 只比大小 —— 换掉中间一个字节，大小不变；
  · 只比 checksum 头 —— 那是服务端自己说的，它可以和实际下发的内容不一致。
所以每个用例都拿下载回来的**实际字节**重算摘要，再和上传时的原始内容比。
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


def _create(name="下载验收"):
    response = client.post(f"{BASE}/workspaces", json={"project_name": name})
    assert response.status_code == 201, response.text
    payload = response.json()
    payload["_session_token"] = response.cookies.get(skeleton.SESSION_COOKIE_NAME)
    payload["_id"] = payload["workspace"]["workspace_id"]
    return payload


def _auth(ws):
    return {"Authorization": f"Bearer {ws['_session_token']}"}


def _upload(ws, content: bytes, *, name: str, media="application/octet-stream", key=None):
    """整份上传（走续传接口，S06 的唯一持久化入口）。"""
    opened = client.post(
        f"{BASE}/workspaces/{ws['_id']}/artifact/uploads", headers=_auth(ws),
        json={"total_bytes": len(content), "content_sha256": hashlib.sha256(content).hexdigest(),
              "filename": quote(name), "media_type": media})
    assert opened.status_code == 201, opened.text
    upload_id = opened.json()["upload_id"]
    sent = client.patch(
        f"{BASE}/workspaces/{ws['_id']}/artifact/uploads/{upload_id}",
        headers={**_auth(ws), "Upload-Offset": "0",
                 "Chunk-SHA256": hashlib.sha256(content).hexdigest()},
        content=content)
    assert sent.status_code == 200, sent.text
    done = client.post(
        f"{BASE}/workspaces/{ws['_id']}/artifact/uploads/{upload_id}/complete",
        headers={**_auth(ws), "Idempotency-Key": key or f"download-fixture-{len(content):08d}"})
    assert done.status_code == 200, done.text
    return done


def _download(ws):
    return client.post(f"{BASE}/workspaces/{ws['_id']}/artifact/download", headers=_auth(ws))


# ─────────────── 阈值：字节不一致 = 0 ───────────────

@pytest.mark.parametrize("content,name,media", [
    (b"\x00\x01\x02\xff" * 300, "二进制.bin", "application/octet-stream"),
    ("纯文本内容，含中文与换行。\n第二行。\n".encode(), "说明.txt", "text/plain"),
    (b"%PDF-1.7\n" + bytes(range(256)) * 4, "合同.pdf", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n" + bytes(range(256)) * 8, "图片.png", "image/png"),
    (b"a,b,c\n1,2,3\n" * 100, "数据.csv", "text/csv"),
])
def test_downloaded_bytes_are_identical_to_what_was_uploaded(
        enabled_store, content, name, media):
    """AC-DL-001「字节/元数据不一致=0」。

    **拿下载回来的实际字节重算摘要**，不信服务端自报的 checksum 头——
    那是服务端说的，它可以和实际下发的内容不一致；也不只比大小——
    换掉中间一个字节大小不变。
    """
    ws = _create()
    _upload(ws, content, name=name, media=media)
    response = _download(ws)
    assert response.status_code == 200, response.text
    assert response.content == content, "下载字节与上传内容不一致"
    assert hashlib.sha256(response.content).hexdigest() == \
        hashlib.sha256(content).hexdigest()


def test_the_reported_checksum_matches_the_bytes_actually_sent(enabled_store):
    """自报 checksum 与实发字节必须一致——否则「来源信息」这一列是假的。"""
    ws = _create()
    content = b"checksum-consistency" * 64
    _upload(ws, content, name="校验.bin")
    response = _download(ws)
    assert response.headers["X-KMFA-Artifact-SHA256"] == \
        hashlib.sha256(response.content).hexdigest()


def test_size_metadata_matches(enabled_store):
    ws = _create()
    content = b"m" * 4321
    _upload(ws, content, name="尺寸.bin")
    response = _download(ws)
    assert len(response.content) == 4321
    workspace = client.get(f"{BASE}/workspaces/{ws['_id']}", headers=_auth(ws)).json()
    assert workspace["artifact"]["size_bytes"] == 4321


# ─────────────── 输入：Unicode / 特殊字符文件名 ───────────────

@pytest.mark.parametrize("name", [
    "中文报表.xlsx",
    "日本語のファイル.txt",
    "한국어파일.pdf",
    "emoji 📊 报表.csv",
    "带空格 和-连字符_和.点.txt",
    "Ω≈ç√∫˜µ≤≥÷.bin",
    "very" + "长" * 60 + ".txt",
])
def test_unicode_and_special_filenames_survive_the_round_trip(enabled_store, name):
    """AC-DL-001 点名要测 Unicode/特殊字符文件名。

    非 ASCII 文件名必须走 RFC 5987 的 `filename*=UTF-8''…` 才不会在传输中变形；
    只给 `filename="…"` 的话，浏览器拿到的会是乱码或被截断的名字——
    而「元数据不一致=0」把文件名也算在内。
    """
    ws = _create()
    content = f"内容 for {name}".encode()
    _upload(ws, content, name=name)
    response = _download(ws)
    assert response.status_code == 200
    disposition = response.headers["content-disposition"]
    assert disposition.startswith("attachment"), disposition
    assert "filename*=utf-8''" in disposition.lower(), (
        f"非 ASCII 文件名必须用 RFC 5987 编码，实际：{disposition}")
    assert response.content == content


# ─────────────── 阈值：高风险格式不内联 ───────────────

@pytest.mark.parametrize("name,media", [
    ("报表.png", "image/png"),                      # 白名单内的安全类型
    ("说明.txt", "text/plain"),
    ("未知.dat", "application/octet-stream"),
])
def test_every_download_is_attachment_never_inline(enabled_store, name, media):
    """AC-DL-001「高风险格式不内联」。

    本实现**比阈值更严**：一律 attachment，连白名单内的安全类型也不内联。
    这是有意的——AC 只要求高风险不内联，没有要求安全类型必须内联；
    而「一律 attachment」不需要任何判断就成立，因此不存在「判错一次就内联了」的窗口。
    """
    ws = _create()
    _upload(ws, b"payload" * 50, name=name, media=media)
    response = _download(ws)
    assert response.headers["content-disposition"].startswith("attachment")
    assert response.headers["content-type"].startswith("application/octet-stream")
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_download_is_never_less_strict_than_the_upload_policy_says(enabled_store):
    """两处策略必须同向：上传侧判「仅附件」的，下载侧不得内联。

    这条锁的是**策略分家**——两个模块各判各的，某天一边放宽了另一边不知道。
    """
    from app.resumable_upload import disposition_for
    ws = _create()
    _upload(ws, b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, name="图.png", media="image/png")
    response = _download(ws)
    _, upload_side = disposition_for("image/png")
    download_side = response.headers["content-disposition"].split(";")[0].strip()
    assert not (upload_side == "attachment" and download_side == "inline"), \
        "上传侧判仅附件，下载侧却内联了——策略分家"
    assert download_side == "attachment", "下载侧当前一律 attachment，比上传侧更严"


# ─────────────── 阈值：越权 = 0 ───────────────

def test_another_workspace_cannot_download_your_artifact(enabled_store):
    """T-S07-01「越权=0」。"""
    owner = _create("持有者")
    intruder = _create("入侵者")
    _upload(owner, b"secret-content" * 40, name="机密.bin")
    stolen = client.post(f"{BASE}/workspaces/{owner['_id']}/artifact/download",
                         headers=_auth(intruder))
    assert stolen.status_code == 404, f"入侵者下到了别人的原件：{stolen.status_code}"


def test_download_without_credentials_is_refused(enabled_store):
    ws = _create()
    _upload(ws, b"needs-auth" * 40, name="需要凭据.bin")
    assert client.post(f"{BASE}/workspaces/{ws['_id']}/artifact/download").status_code == 404


# ─────────────── stop_condition：URL 不可枚举 ───────────────

def test_the_download_endpoint_is_not_a_guessable_get(enabled_store):
    """stop_condition：「下载 URL 可被枚举或长期绕过 workspace/发布权限」即停止。

    下载是 **POST + 凭据**，不是可以贴出去、可以被爬、可以进浏览器历史的 GET。
    这一条锁住它不被「为了方便」改成 GET。
    """
    ws = _create()
    _upload(ws, b"not-enumerable" * 40, name="不可枚举.bin")
    got = client.get(f"{BASE}/workspaces/{ws['_id']}/artifact/download", headers=_auth(ws))
    assert got.status_code == 405, f"下载不该响应 GET：{got.status_code}"


def test_a_guessed_workspace_id_yields_nothing(enabled_store):
    """枚举 workspace id 也拿不到东西——404 且不泄露存在性。"""
    ws = _create()
    _upload(ws, b"x" * 100, name="x.bin")
    for guess in ("ws_0000000000000000", "ws_1111111111111111", ws["_id"][:-2] + "zz"):
        response = client.post(f"{BASE}/workspaces/{guess}/artifact/download",
                               headers=_auth(ws))
        assert response.status_code == 404


# ─────────────── 阈值：可用制品 100% 下载 ───────────────

def test_no_artifact_yields_an_honest_404_not_an_empty_file(enabled_store):
    """还没有制品时必须说「没有」，不能下发一个 0 字节文件——
    空文件和「没有」在用户那里长得一样，意思完全不同。"""
    ws = _create()
    response = _download(ws)
    assert response.status_code == 404
    assert response.content != b"", "不许用空响应体冒充「没有制品」"


def test_repeated_downloads_are_byte_stable(enabled_store):
    """可用制品下载率 100% 意味着**每次**都能下、且每次都一样。"""
    ws = _create()
    content = bytes((i * 3) % 251 for i in range(5000))
    _upload(ws, content, name="稳定.bin")
    digests = set()
    for _ in range(5):
        response = _download(ws)
        assert response.status_code == 200
        digests.add(hashlib.sha256(response.content).hexdigest())
    assert digests == {hashlib.sha256(content).hexdigest()}, "多次下载结果不一致"


def test_cache_headers_keep_private_content_out_of_shared_caches(enabled_store):
    """「来源信息」之外还有一条隐含要求：私有内容不得被共享缓存留存。"""
    ws = _create()
    _upload(ws, b"private" * 60, name="私有.bin")
    response = _download(ws)
    assert "no-store" in response.headers["cache-control"]
    assert "private" in response.headers["cache-control"]


# ─────────────── AC-DL-001 输入清单里的「派生文件」 ───────────────

def test_a_text_derivative_can_be_downloaded_and_traces_to_its_parent(enabled_store):
    """AC-DL-001 的输入清单点名「预览、派生文件」。

    派生物必须能追回**具体那一版原件**——只给一份文本而不说它来自哪，
    就是 T-S06-03 要防的血缘断点。
    """
    ws = _create()
    content = "第一行\n第二行,含逗号\n第三行\n".encode()
    _upload(ws, content, name="台账.csv", media="text/csv")
    response = client.post(f"{BASE}/workspaces/{ws['_id']}/artifact/derivative/text",
                           headers=_auth(ws))
    assert response.status_code == 200, response.text
    assert response.content.decode("utf-8") == content.decode("utf-8")
    assert response.headers["X-KMFA-Parent-SHA256"] == hashlib.sha256(content).hexdigest()
    assert response.headers["X-KMFA-Derivative-Processor"] == "text-extract@1.0.0"
    assert response.headers["content-disposition"].startswith("attachment")


def test_the_derivative_digest_is_computed_on_the_output_not_the_input(enabled_store):
    """摘要算在输出上：用输入摘要充当输出摘要，会让两个不同的派生物看起来是同一个。"""
    ws = _create()
    content = b"hello derivative"
    _upload(ws, content, name="a.txt", media="text/plain")
    response = client.post(f"{BASE}/workspaces/{ws['_id']}/artifact/derivative/text",
                           headers=_auth(ws))
    assert response.headers["X-KMFA-Derivative-SHA256"] == \
        hashlib.sha256(response.content).hexdigest()


def test_formats_needing_a_parser_are_refused_with_the_reason_spelled_out(enabled_store):
    """缩略图/预览需要把不可信字节喂给图像或 PDF 解码器，
    而 T-S06-03 的 stop_condition 明令处理器不得执行用户文件中的内容。

    **理由必须写出来**：空着会被后来的人当成「忘了做」，于是补上它——
    把守住的边界重新打开。
    """
    ws = _create()
    _upload(ws, b"\x89PNG\r\n\x1a\n" + b"\x00" * 200, name="图.png", media="image/png")
    response = client.post(f"{BASE}/workspaces/{ws['_id']}/artifact/derivative/text",
                           headers=_auth(ws))
    assert response.status_code == 415
    assert "stop_condition" in response.json()["detail"]


def test_an_unknown_derivative_kind_is_not_silently_served(enabled_store):
    ws = _create()
    _upload(ws, b"x" * 50, name="a.txt", media="text/plain")
    for kind in ("thumbnail", "preview", "随便"):
        response = client.post(
            f"{BASE}/workspaces/{ws['_id']}/artifact/derivative/{kind}", headers=_auth(ws))
        assert response.status_code == 404


def test_derivatives_honour_the_same_authorization_as_the_original(enabled_store):
    """越权=0 对派生物同样成立——新路由复用同一条鉴权，不自建。"""
    owner = _create("持有者")
    intruder = _create("入侵者")
    _upload(owner, "机密文本".encode(), name="机密.txt", media="text/plain")
    stolen = client.post(f"{BASE}/workspaces/{owner['_id']}/artifact/derivative/text",
                         headers=_auth(intruder))
    assert stolen.status_code == 404
