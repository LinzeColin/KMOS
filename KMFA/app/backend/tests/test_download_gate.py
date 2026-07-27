# -*- coding: utf-8 -*-
"""S07/P7.4 · T-S07-04 —— 下载与导出门禁：越权、泄露、负载、恢复。

T-S07-04
  test：IDOR、签名 URL 重放/过期、公共缓存、并发大下载、导出洪泛、worker 故障恢复
  risk：公共 CDN 缓存未公开文件，或异常出网费用
  stop_condition：**发现任何跨 workspace 文件可读，或公开缓存不可撤销**

本任务在任务包里没有绑定 AC——它是 S07 的出口门禁：把 P7.1–P7.3 建起来的东西
放在一起，问「这套下载能力会不会变成数据泄露或出网费用黑洞」。

## 授权矩阵从路由表派生，不手写

手写矩阵会和路由表脱节，而脱节的方向永远是「新端点没进矩阵」——
于是新加的端点是唯一没被越权测试覆盖的那个，而它恰恰是最可能忘了鉴权的那个。

这里枚举**全部** workspace 作用域路由（含 `include_router` 挂进来的），
逐条 × 三种身份实测。新端点自动进矩阵，不需要谁记得来加。

## 422 不算通过

请求体校验不过会以 422 挡在门外，鉴权代码一行都没跑。
把 422 当「拒绝了，很好」是本线踩过的坑（TEST-DL-004 第一版）：
**一盏覆盖为零的绿灯，比一个红灯危险得多。**
所以每条路由都给足能过校验的请求体，422 一律判失败并指出该补什么。

## 「签名 URL 重放/过期」为什么是不适用而不是漏测

本仓的下载**没有签名 URL 这个东西**：制品一律 POST + 凭据取。
没有可分发的 URL，就没有 URL 被转发、被日志记录、被重放的窗口，
过期策略也就无处可谈。

这不是省事——签名 URL 的整个风险面（泄露即长期可用、撤销要等过期、
CDN 会缓存）本仓通过**不引入它**来消除。下面有一条用例把这件事钉住：
一旦哪天有人加了签名 URL 参数，它会红，逼着补齐重放与过期测试。
"""
from __future__ import annotations

import hashlib
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent))
from test_read_has_no_side_effects import _walk_routes  # noqa: E402

from app import batch_archive as BA  # noqa: E402
from app import export_jobs as EJ  # noqa: E402
from app import walking_skeleton as skeleton  # noqa: E402
from app.main import app  # noqa: E402

BASE = "/public-api/walking-skeleton/v1"
ORIGIN = "https://kmfa.test"
client = TestClient(app, base_url=ORIGIN, headers={"Origin": ORIGIN})


def _workspace_routes() -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for route in _walk_routes(app):
        path = getattr(route, "path", "")
        if "{workspace_id}" not in path:
            continue
        for method in sorted(getattr(route, "methods", None) or []):
            if method in {"HEAD", "OPTIONS"}:
                continue
            rows.append((method, path))
    return sorted(set(rows), key=lambda item: (item[1], item[0]))


WORKSPACE_ROUTES = _workspace_routes()

#: 每条路由一份**能过请求体校验**的最小载荷。缺了它请求会以 422 挡在门外，
#: 鉴权一行没跑——那不是「拒绝了」，那是没测。
_PAYLOAD = hashlib.sha256(b"gate").hexdigest()
#: 键用**路由后缀**匹配，不写全路径——全路径要跟着 API_PREFIX 走，
#: 前缀哪天变了这里会整体失配，而失配的表现是所有路由退回 422 空跑。
BODY_FOR: dict[str, dict] = {
    "PATCH /workspaces/{workspace_id}": {"json": {"progress": 10}},
    # 删除要确认词 + secret。入侵者当然不知道真 secret，
    # 这里给一个**形状合法**的假值：目的是让请求过掉体校验、走到鉴权，
    # 然后由鉴权以 404 拒掉。若它先校验 secret 再校验归属，也仍是拒绝。
    "DELETE /workspaces/{workspace_id}": {
        "json": {"confirmation": "DELETE", "workspace_secret": "x" * 43},
        "headers": {"Idempotency-Key": "gate-idor-delete-00001"}},
    "POST /workspaces/{workspace_id}/recovery-file": {
        "json": {"workspace_secret": "x" * 43}},
    "POST /workspaces/{workspace_id}/artifact/uploads": {
        "json": {"total_bytes": 4, "content_sha256": _PAYLOAD,
                 "filename": quote("越权探测.txt"), "media_type": "text/plain"}},
    "PATCH /workspaces/{workspace_id}/artifact/uploads/{upload_id}": {
        "content": b"gate", "headers": {"Upload-Offset": "0", "Chunk-SHA256": _PAYLOAD}},
    "POST /workspaces/{workspace_id}/artifact/uploads/{upload_id}/complete": {
        "headers": {"Idempotency-Key": "gate-idor-probe-000001"}},
    "PUT /workspaces/{workspace_id}/artifact": {
        "content": b"gate",
        "headers": {"Content-Type": "application/octet-stream",
                    "X-KMFA-Filename": quote("越权探测.bin"),
                    "Idempotency-Key": "gate-idor-put-000001"}},
}

FILLERS = {"{upload_id}": "up_no_such_upload_0001", "{kind}": "text"}


def _spec_for(method: str, path: str) -> dict:
    suffix = path.split("/v1", 1)[-1]
    return dict(BODY_FOR.get(f"{method} {suffix}", {}))


def _url(path: str, workspace_id: str) -> str:
    url = path.replace("{workspace_id}", workspace_id)
    for token, value in FILLERS.items():
        url = url.replace(token, value)
    return url


def _call(method: str, path: str, workspace_id: str, headers: dict | None = None):
    spec = _spec_for(method, path)
    merged = {**spec.pop("headers", {}), **(headers or {})}
    return client.request(method, _url(path, workspace_id), headers=merged, **spec)


@pytest.fixture
def enabled_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    state = tmp_path / "walking-state"
    monkeypatch.setenv("KMFA_WALKING_SKELETON_ENABLED", "1")
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(state))
    monkeypatch.delenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", raising=False)
    client.cookies.clear()
    return state


def _create(name="门禁"):
    response = client.post(f"{BASE}/workspaces", json={"project_name": name})
    assert response.status_code == 201, response.text
    payload = response.json()
    payload["_session_token"] = response.cookies.get(skeleton.SESSION_COOKIE_NAME)
    payload["_id"] = payload["workspace"]["workspace_id"]
    return payload


def _auth(ws):
    return {"Authorization": f"Bearer {ws['_session_token']}"}


# ═══════════ 授权矩阵：IDOR ═══════════

def test_the_matrix_covers_every_workspace_route():
    """守卫：矩阵是从路由表派生的，派生失效时下面每条用例都会空转。"""
    assert len(WORKSPACE_ROUTES) >= 12, f"只枚举到 {len(WORKSPACE_ROUTES)} 条"
    paths = {p for _, p in WORKSPACE_ROUTES}
    for required in ("artifact/download", "artifact/batch", "audit-events",
                     "artifact/uploads", "recovery-file"):
        assert any(required in p for p in paths), f"矩阵里少了 {required}"


@pytest.mark.parametrize("method,path", WORKSPACE_ROUTES,
                         ids=lambda v: str(v).replace("/", "_"))
def test_another_workspace_cannot_touch_this_one(method, path, enabled_store):
    """**stop_condition 的正面测法**：跨 workspace 一律 404。

    404 而不是 403：403 会确认「这个 workspace 存在」，
    把一个存在性探测器免费送给攻击者——他可以据此枚举出哪些 id 是真的。
    """
    owner = _create("门禁本体")
    owner_id = owner["_id"]
    intruder = _create("门禁入侵者")

    response = _call(method, path, owner_id, headers=_auth(intruder))
    assert response.status_code != 422, (
        f"{method} {path} 返回 422——请求体没过校验，鉴权一行都没跑。"
        f"这不是「拒绝了」，是没测。给 BODY_FOR 补上它的载荷。\n{response.text[:200]}")
    assert response.status_code == 404, (
        f"{method} {path} 用别的 workspace 的凭据拿到了 {response.status_code}")
    assert response.status_code != 403, "403 会确认该 workspace 存在"


@pytest.mark.parametrize("method,path", WORKSPACE_ROUTES,
                         ids=lambda v: str(v).replace("/", "_"))
def test_anonymous_cannot_touch_any_workspace(method, path, enabled_store):
    """匿名身份必须**结构上**没有凭据——用全新客户端，不靠某一步记得清 cookie。"""
    owner = _create()
    stranger = TestClient(app, base_url=ORIGIN, headers={"Origin": ORIGIN})
    spec = _spec_for(method, path)
    headers = spec.pop("headers", {})
    response = stranger.request(method, _url(path, owner["_id"]),
                                headers=headers, **spec)
    assert response.status_code != 422, (
        f"{method} {path} 匿名请求返回 422——没进到鉴权。给 BODY_FOR 补载荷。")
    assert response.status_code == 404, f"{method} {path} → {response.status_code}"


def test_a_forged_bearer_token_gets_nothing(enabled_store):
    """伪造凭据与无凭据必须**同样**是 404：两者若给出不同回应，
    差异本身就是一个可用来判断「token 格式对不对」的预言机。"""
    owner = _create()
    for forged in ("Bearer forged", "Bearer " + "a" * 43, "Bearer ", "NotEvenBearer x"):
        response = client.post(f"{BASE}/workspaces/{owner['_id']}/artifact/download",
                               headers={"Authorization": forged})
        assert response.status_code == 404, f"{forged!r} → {response.status_code}"


# ═══════════ 泄露：公共缓存（stop_condition） ═══════════

def _private_responses(ws):
    return [
        ("状态", client.get(f"{BASE}/workspaces/{ws['_id']}", headers=_auth(ws))),
        ("审计", client.get(f"{BASE}/workspaces/{ws['_id']}/audit-events",
                            headers=_auth(ws))),
        ("下载", client.post(f"{BASE}/workspaces/{ws['_id']}/artifact/download",
                             headers=_auth(ws))),
        ("批量", client.post(f"{BASE}/workspaces/{ws['_id']}/artifact/batch",
                             headers=_auth(ws))),
    ]


def test_no_private_response_is_publicly_cacheable(enabled_store):
    """**stop_condition 的另一半：公开缓存不可撤销。**

    一旦某个私有响应带上 `public` 或 `max-age`，路上的 CDN / 代理就会存下它，
    而**你撤不回来**——删了源文件、改了权限、吊销了会话都没用，
    缓存里那份还在，直到它自己过期。所以这条不是「最好加上」，是硬门禁。
    """
    ws = _create()
    for name, response in _private_responses(ws):
        cache = response.headers.get("Cache-Control", "")
        assert "no-store" in cache, f"{name} 缺 no-store：{cache!r}"
        assert "private" in cache, f"{name} 缺 private：{cache!r}"
        assert "public" not in cache, f"{name} 带了 public——CDN 会存下它：{cache!r}"
        assert "max-age" not in cache or "max-age=0" in cache, (
            f"{name} 带了正的 max-age：{cache!r}")


def test_private_responses_are_not_indexable_and_do_not_sniff(enabled_store):
    ws = _create()
    for name, response in _private_responses(ws):
        assert response.headers.get("X-Content-Type-Options") == "nosniff", name
        robots = response.headers.get("X-Robots-Tag", "")
        if robots:
            assert "noindex" in robots, f"{name} 的 X-Robots-Tag 不含 noindex"


def test_error_bodies_do_not_leak_paths_or_ids(enabled_store):
    """报错不能把内部路径或别人的标识吐出来——
    「找不到」这件事本身不该附带一张系统地图。"""
    owner = _create()
    intruder = _create()
    body = client.post(f"{BASE}/workspaces/{owner['_id']}/artifact/download",
                       headers=_auth(intruder)).text
    assert owner["_id"] not in body, "报错回显了目标 workspace id"
    for token in ("/var/lib", "/opt/", "Traceback", "sqlite3", ".py\", line"):
        assert token not in body, f"报错泄露了内部细节：{token}"


# ═══════════ 「签名 URL」不存在，且要保持不存在 ═══════════

def test_there_is_no_signed_url_surface_to_replay(enabled_store):
    """签名 URL 的整个风险面——泄露即长期可用、撤销要等过期、CDN 会缓存——
    本仓通过**不引入它**来消除。

    这条用例把「不存在」钉住：哪天有人加了签名参数，它会红，
    逼着补齐重放与过期测试，而不是让一条无人测过的 URL 悄悄上线。
    """
    ws = _create()
    for _, response in _private_responses(ws):
        for header in ("Location", "X-Signed-Url", "X-Presigned-Url"):
            assert header not in response.headers, f"冒出了 {header}"
    # 下载不接受任何签名类 query 参数（接受即意味着存在一条免凭据路径）
    for probe in ("?signature=x", "?token=x", "?expires=9999999999", "?sig=x&exp=1"):
        response = client.post(
            f"{BASE}/workspaces/{ws['_id']}/artifact/download{probe}")
        assert response.status_code == 404, f"{probe} → {response.status_code}"


# ═══════════ 负载：并发大下载与导出洪泛 ═══════════

def test_concurrent_downloads_do_not_cross_wires(enabled_store):
    """并发大下载：十个请求同时打，每个都必须拿到**自己那份**。

    并发下最典型的缺陷不是慢，是串台——共享的缓冲区或路径变量
    让 A 拿到 B 的字节。所以逐个校验内容，不只看状态码。
    """
    # **每个 workspace 一个客户端。** 共用一个客户端时，cookie jar 只留最后一个会话，
    # 前面几个的 Bearer 与 cookie 不一致，会被判成越权而 404——
    # 那样测出来的不是并发，是我自己的夹具串了台。
    workspaces = []
    for index in range(4):
        own = TestClient(app, base_url=ORIGIN, headers={"Origin": ORIGIN})
        created = own.post(f"{BASE}/workspaces", json={"project_name": f"并发-{index}"})
        assert created.status_code == 201, created.text
        ws = created.json()
        ws["_session_token"] = created.cookies.get(skeleton.SESSION_COOKIE_NAME)
        ws["_id"] = ws["workspace"]["workspace_id"]
        ws["_client"] = own
        payload = bytes([index]) * 4096
        digest = hashlib.sha256(payload).hexdigest()
        opened = own.post(
            f"{BASE}/workspaces/{ws['_id']}/artifact/uploads", headers=_auth(ws),
            json={"total_bytes": len(payload), "content_sha256": digest,
                  "filename": quote(f"并发-{index}.bin"),
                  "media_type": "application/octet-stream"})
        assert opened.status_code == 201, opened.text
        upload_id = opened.json()["upload_id"]
        own.patch(f"{BASE}/workspaces/{ws['_id']}/artifact/uploads/{upload_id}",
                  headers={**_auth(ws), "Upload-Offset": "0",
                           "Chunk-SHA256": digest}, content=payload)
        done = own.post(
            f"{BASE}/workspaces/{ws['_id']}/artifact/uploads/{upload_id}/complete",
            headers={**_auth(ws), "Idempotency-Key": f"gate-concurrent-{index:012d}"})
        assert done.status_code == 200, done.text
        workspaces.append((ws, payload))

    def fetch(item):
        ws, expected = item
        response = ws["_client"].post(
            f"{BASE}/workspaces/{ws['_id']}/artifact/download", headers=_auth(ws))
        return response.status_code, response.content, expected

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(fetch, workspaces * 3))

    for status, content, expected in results:
        assert status in {200, 429}, status
        if status == 200:
            assert content == expected, "并发下拿到了别人的字节——串台"


def test_export_flood_is_bounded_by_declared_limits():
    """导出洪泛的闸是**声明式的**，且不能被改成等于没有。"""
    assert 0 < EJ.MAX_CONCURRENT_JOBS <= 16
    assert 0 < EJ.MAX_JOBS_PER_OWNER <= 10_000
    assert 0 < BA.MAX_SYNC_ENTRIES <= 500
    assert 0 < BA.MAX_SYNC_BYTES <= 2 * 1024 * 1024 * 1024


def test_egress_is_bounded_per_request(enabled_store):
    """出网费用黑洞的防线：**单个请求能拉走多少字节有上界**。

    没有上界时，一个请求就能把整库拉走，账单在事后才出现。
    """
    assert BA.MAX_SYNC_BYTES <= 2 * 1024 * 1024 * 1024
    assert skeleton.MAX_ARTIFACT_BYTES <= 64 * 1024 * 1024
    assert skeleton.MAX_TOTAL_ARTIFACT_BYTES <= 8 * 1024 * 1024 * 1024
    # 上限必须**被执行**，不能只是声明——用一条超限请求实证
    over = BA.sync_batch_rejection(1, BA.MAX_SYNC_BYTES + 1)
    assert over and "MiB" in over


# ═══════════ 恢复 ═══════════

def test_missing_object_reports_unavailable_not_silence(enabled_store):
    """存储侧丢了对象时必须**明说**，不能返回一个空文件。

    空文件是最坏的回应：调用方拿到 200 和 0 字节，会以为报告就是空的。
    """
    ws = _create()
    payload = b"recoverable" * 100
    digest = hashlib.sha256(payload).hexdigest()
    opened = client.post(
        f"{BASE}/workspaces/{ws['_id']}/artifact/uploads", headers=_auth(ws),
        json={"total_bytes": len(payload), "content_sha256": digest,
              "filename": quote("恢复.bin"), "media_type": "application/octet-stream"})
    upload_id = opened.json()["upload_id"]
    client.patch(f"{BASE}/workspaces/{ws['_id']}/artifact/uploads/{upload_id}",
                 headers={**_auth(ws), "Upload-Offset": "0", "Chunk-SHA256": digest},
                 content=payload)
    client.post(f"{BASE}/workspaces/{ws['_id']}/artifact/uploads/{upload_id}/complete",
                headers={**_auth(ws), "Idempotency-Key": "gate-recovery-00000001"})

    for blob in (enabled_store / "objects").glob("*"):
        blob.unlink()

    response = client.post(f"{BASE}/workspaces/{ws['_id']}/artifact/download",
                           headers=_auth(ws))
    assert response.status_code == 503, f"对象没了却返回 {response.status_code}"
    assert response.json()["detail"] in {"artifact_unavailable",
                                         "artifact_integrity_failed"}


def test_a_corrupted_object_is_refused_not_served(enabled_store):
    """字节被改过就必须拒发。**发出去再让用户自己发现**等于把校验推给下游，
    而下游多半不会校验。"""
    ws = _create()
    payload = b"integrity" * 200
    digest = hashlib.sha256(payload).hexdigest()
    opened = client.post(
        f"{BASE}/workspaces/{ws['_id']}/artifact/uploads", headers=_auth(ws),
        json={"total_bytes": len(payload), "content_sha256": digest,
              "filename": quote("完整性.bin"), "media_type": "application/octet-stream"})
    upload_id = opened.json()["upload_id"]
    client.patch(f"{BASE}/workspaces/{ws['_id']}/artifact/uploads/{upload_id}",
                 headers={**_auth(ws), "Upload-Offset": "0", "Chunk-SHA256": digest},
                 content=payload)
    client.post(f"{BASE}/workspaces/{ws['_id']}/artifact/uploads/{upload_id}/complete",
                headers={**_auth(ws), "Idempotency-Key": "gate-integrity-0000001"})

    blobs = list((enabled_store / "objects").glob("*"))
    assert blobs, "没找到落盘的对象，用例失去了对象"
    original = blobs[0].read_bytes()
    blobs[0].write_bytes(b"\x00" + original[1:])  # 改一个字节，长度不变

    response = client.post(f"{BASE}/workspaces/{ws['_id']}/artifact/download",
                           headers=_auth(ws))
    assert response.status_code == 503, (
        f"内容被改过却返回 {response.status_code}——只比长度是抓不到的")
    assert response.json()["detail"] == "artifact_integrity_failed"
