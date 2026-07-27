# -*- coding: utf-8 -*-
"""TEST-DL-002 —— S07/P7.2 · T-S07-02 Range、断点续传与可验证批量 ZIP。

AC-DL-002
  输入：大文件 Range、并行 Range、50/500 文件批量、重名与特殊字符
  过程：中断后续传；生成 ZIP；解压并逐项 hash；取消和重试
  阈值：Range 语义正确；续传 hash 一致；ZIP 项目无丢失/覆盖/路径穿越；失败可重试

T-S07-02
  pass_gate：Range/续传 hash 正确；ZIP 无丢失/覆盖/穿越；资源受控
  stop_condition：批量实现需要把整个归档放入单进程内存

## 两处「测法本身要讲清楚」的地方

**「续传 hash 一致」不能只测顺利路径。** 分段下载再拼起来 hash 对得上，
只证明了没人动过制品。真正会出事的是制品在两段之间变了——那时拼出来的东西
长度对、状态码对、没有任何一层报错，但它既不是旧版也不是新版。
所以这里专门造了「续传中途制品被替换」的用例，断言服务端**回整份而不是片段**。

**zip-slip 只能在模块层测，不能在 HTTP 层测。** 上传侧的 `safe_filename`
会把 `../../etc/passwd` 挡在门外，HTTP 层根本造不出这种数据。
但归档层不能因此就信任「名字一定是干净的」——历史导入、直接写库、
将来任何一条新的入库路径，都可能绕过上传检查。
所以对归档层直接喂恶意名字，验证它自己就把路径成分剥干净。
这是纵深防御：**两层都挡，不是一层挡了另一层就可以不挡。**
"""
from __future__ import annotations

import hashlib
import json
import tracemalloc
import zipfile
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from app import anti_abuse as abuse
from app import batch_archive as BA
from app import download_range as DR
from app import walking_skeleton as skeleton
from app.main import app

BASE = "/public-api/walking-skeleton/v1"
ORIGIN = "https://kmfa.test"

#: **必须走 https**，不是为了好看。设备 cookie `__Host-kmfa_device` 带 `Secure`，
#: 在 `http://testserver` 上 httpx 会拒绝存它，于是每个请求都被判成一台新设备：
#: 防滥用挑战绑定的 `actor_tag`（ip+device）每次都变，客户端**永远解不开**，
#: 而生产环境是 https、cookie 会粘住。用 http 测出来的续传行为不是生产行为。
client = TestClient(app, base_url=ORIGIN, headers={"Origin": ORIGIN})


@pytest.fixture
def enabled_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    state = tmp_path / "walking-state"
    monkeypatch.setenv("KMFA_WALKING_SKELETON_ENABLED", "1")
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(state))
    monkeypatch.delenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", raising=False)
    # 走 https 之后 cookie 才会真的被 jar 收下（这正是我们要的），
    # 代价是它也会**跨用例**留存：上一条用例的会话 cookie 会被自动带进下一条，
    # 于是「不带凭据」的用例其实带了凭据、状态目录换了却还在用旧会话。
    # 每条用例开始时清空，隔离到与「每个用例一个新客户端」等价。
    client.cookies.clear()
    return state


def _create(name="续传批量验收"):
    response = client.post(f"{BASE}/workspaces", json={"project_name": name})
    assert response.status_code == 201, response.text
    payload = response.json()
    payload["_session_token"] = response.cookies.get(skeleton.SESSION_COOKIE_NAME)
    payload["_id"] = payload["workspace"]["workspace_id"]
    return payload


def _auth(ws):
    return {"Authorization": f"Bearer {ws['_session_token']}"}


def _solve(challenge: dict) -> str:
    """按防滥用层给的工作量证明求解。测试**像真客户端一样行事**，不绕过它。"""
    assert challenge["algorithm"] == "sha256-leading-zero-bits"
    token, difficulty = str(challenge["token"]), int(challenge["difficulty_bits"])
    for nonce in range(2**32):
        proof = f"{token}:{nonce}"
        if abuse._leading_zero_bits(hashlib.sha256(proof.encode("ascii")).digest()) >= difficulty:
            return proof
    raise AssertionError("challenge solver exhausted")


def _post(url: str, **kwargs):
    """POST，遇到工作量证明就解开重试一次。

    **续传天生就是多次请求**，而防滥用层按请求数计——一个大文件分 20 段取回，
    在 10 秒窗口里看起来和导出滥用没有区别。这不是测试环境的怪癖，
    真实客户端一样会撞上（见 `S07_P72_RANGE_BATCH.md` 的「留下的摩擦」）。
    所以这里不关掉防滥用、也不放宽阈值，而是**照规矩解开挑战**：
    顺带证明了断点续传与防滥用可以共存，而不是二选一。
    """
    response = client.post(url, **kwargs)
    if response.status_code == 429 and "challenge" in response.json():
        headers = dict(kwargs.pop("headers", {}))
        headers["X-KMFA-Challenge-Proof"] = _solve(response.json()["challenge"])
        response = client.post(url, headers=headers, **kwargs)
    return response


def _patch(url: str, **kwargs):
    response = client.patch(url, **kwargs)
    if response.status_code == 429 and "challenge" in response.json():
        headers = dict(kwargs.pop("headers", {}))
        headers["X-KMFA-Challenge-Proof"] = _solve(response.json()["challenge"])
        response = client.patch(url, headers=headers, **kwargs)
    return response


def _upload(ws, content: bytes, *, name: str, media="application/octet-stream", key=None):
    digest = hashlib.sha256(content).hexdigest()
    opened = _post(
        f"{BASE}/workspaces/{ws['_id']}/artifact/uploads", headers=_auth(ws),
        json={"total_bytes": len(content), "content_sha256": digest,
              "filename": quote(name), "media_type": media})
    assert opened.status_code == 201, opened.text
    upload_id = opened.json()["upload_id"]
    sent = _patch(
        f"{BASE}/workspaces/{ws['_id']}/artifact/uploads/{upload_id}",
        headers={**_auth(ws), "Upload-Offset": "0", "Chunk-SHA256": digest},
        content=content)
    assert sent.status_code == 200, sent.text
    done = _post(
        f"{BASE}/workspaces/{ws['_id']}/artifact/uploads/{upload_id}/complete",
        headers={**_auth(ws), "Idempotency-Key": key or f"batch-fixture-{digest[:24]}"})
    assert done.status_code == 200, done.text
    return done


def _download(ws, headers=None):
    return _post(
        f"{BASE}/workspaces/{ws['_id']}/artifact/download",
        headers={**_auth(ws), **(headers or {})})


def test_one_artifact_per_workspace_is_a_schema_invariant(enabled_store):
    """**本任务撞到的边界，如实钉在这里。**

    `artifacts.workspace_id` 从 0001 号迁移起就带 `UNIQUE`：
    一个 workspace 结构上**只能**有一个制品。所以 HTTP 批量下载
    今天最多只能装一个条目——不是被限流，是数据模型不允许更多。

    这条用例存在的意义是让这个边界**可见**：
    读到「批量下载」四个字的人，会默认它能装很多个；
    没有这条用例，他要么读迁移文件才知道，要么在生产上才发现。

    AC-DL-002 点名的 50/500 文件批量，因此只能在归档层证（见本文件下半部分：
    500 条目零丢失、逐项 hash、峰值内存与归档大小无关）。
    放开这个约束要改数据模型 + 迁移 + 保留策略，那是 S02/S03 的范围，
    不在 T-S07-02 里做——**范围不缩，但也不越界去改别人的地基**。
    """
    ws = _create()
    _upload(ws, b"first", name="第一个.txt", key="guard-first-artifact-000001")

    # 第二次上传**开得成**（201），撞墙发生在 complete。
    # 这个顺序值得记一笔：占位阶段不查上限，用户传完整个文件才被拒——
    # 小文件无所谓，大文件就是白传一遍。不在本任务里改，但别假装它不存在。
    payload = b"second"
    digest = hashlib.sha256(payload).hexdigest()
    opened = _post(
        f"{BASE}/workspaces/{ws['_id']}/artifact/uploads", headers=_auth(ws),
        json={"total_bytes": len(payload), "content_sha256": digest,
              "filename": quote("第二个.txt"), "media_type": "text/plain"})
    assert opened.status_code == 201, opened.text
    upload_id = opened.json()["upload_id"]
    _patch(f"{BASE}/workspaces/{ws['_id']}/artifact/uploads/{upload_id}",
           headers={**_auth(ws), "Upload-Offset": "0", "Chunk-SHA256": digest},
           content=payload)
    done = _post(
        f"{BASE}/workspaces/{ws['_id']}/artifact/uploads/{upload_id}/complete",
        headers={**_auth(ws), "Idempotency-Key": "guard-second-artifact-00002"})
    assert done.status_code == 409, done.text
    assert done.json()["detail"] == "artifact_limit_reached"

    migration = (Path(skeleton.__file__).parent.parent
                 / "migrations" / "sqlite" / "0001_legacy_walking_skeleton.sql")
    assert "workspace_id TEXT NOT NULL UNIQUE" in migration.read_text(encoding="utf-8"), (
        "上面的 409 可能只是应用层限制；这一句确认它是 schema 级不变量")


def _member(tmp_path: Path, name: str, payload: bytes, *, sort_key: str) -> BA.ArchiveMember:
    path = tmp_path / f"src-{hashlib.sha256(sort_key.encode()).hexdigest()[:16]}"
    path.write_bytes(payload)
    return BA.ArchiveMember(
        source_path=path, original_name=name,
        sha256=hashlib.sha256(payload).hexdigest(),
        size_bytes=len(payload), sort_key=sort_key)


# ═════════════════ 阈值一：Range 语义正确 ═════════════════

@pytest.mark.parametrize("header,total,expected", [
    ("bytes=0-499", 1000, DR.ByteRange(0, 499)),
    ("bytes=500-", 1000, DR.ByteRange(500, 999)),
    ("bytes=-500", 1000, DR.ByteRange(500, 999)),
    ("bytes=0-0", 1000, DR.ByteRange(0, 0)),
    ("bytes=999-999", 1000, DR.ByteRange(999, 999)),
    # 终点越界要截断，不是报错：RFC 9110 明确允许「不知总长时先要一大段」。
    ("bytes=900-99999", 1000, DR.ByteRange(900, 999)),
    # 后缀长度超过总长 ⇒ 整份。
    ("bytes=-99999", 1000, DR.ByteRange(0, 999)),
    ("BYTES=0-9", 1000, DR.ByteRange(0, 9)),
    ("  bytes = 0 - 9 ", 1000, DR.ByteRange(0, 9)),
])
def test_range_parsing_is_rfc_correct(header, total, expected):
    assert DR.parse_range(header, total) == expected


@pytest.mark.parametrize("header,total", [
    ("bytes=1000-", 1000),      # 起点越界
    ("bytes=1000-1005", 1000),
    ("bytes=-0", 1000),         # 「最后 0 个字节」不可满足，不是整份
    ("bytes=0-", 0),            # 空资源上任何区间都不可满足
    ("bytes=-1", 0),
])
def test_unsatisfiable_ranges_are_distinguished_from_absent(header, total):
    assert DR.parse_range(header, total) is DR.UNSATISFIABLE


@pytest.mark.parametrize("header", [
    None, "", "items=0-9", "bytes=abc", "bytes=", "bytes=-",
    "bytes=500-100",              # 语义颠倒 ⇒ 按无效忽略
    "bytes=0-1,2-3",              # 多段：不给片段，回整份（放大攻击）
    "bytes=0-1, 5-6, 9-10",
])
def test_invalid_or_multi_range_falls_back_to_whole(header):
    """RFC 9110：无效 Range 必须被忽略、当普通请求处理，而不是 400。"""
    assert DR.parse_range(header, 1000) is None


def test_content_range_header_is_inclusive_end():
    assert DR.ByteRange(0, 499).content_range(1000) == "bytes 0-499/1000"
    assert DR.ByteRange(0, 499).length == 500


def test_etag_is_strong_not_weak():
    """弱 ETag 不允许用于 Range 比对：它允许「语义等价但字节不同」，
    而续传拼接要的正是字节相同。"""
    etag = DR.etag_for("a" * 64)
    assert etag == '"' + "a" * 64 + '"'
    assert not etag.startswith("W/")


def test_if_range_absent_is_permissive_but_mismatch_is_not():
    etag = DR.etag_for("a" * 64)
    assert DR.if_range_satisfied(None, etag) is True
    assert DR.if_range_satisfied(etag, etag) is True
    assert DR.if_range_satisfied(DR.etag_for("b" * 64), etag) is False
    # HTTP-date 形式不支持：秒级分辨率会留一个一秒宽的损坏窗口。
    assert DR.if_range_satisfied("Wed, 21 Oct 2015 07:28:00 GMT", etag) is False


def test_iter_file_range_never_holds_more_than_one_chunk(tmp_path: Path):
    path = tmp_path / "big.bin"
    path.write_bytes(b"x" * (1024 * 1024))
    sizes = [len(b) for b in DR.iter_file_range(path, None, chunk_size=4096)]
    assert max(sizes) == 4096
    assert sum(sizes) == 1024 * 1024


def test_truncated_source_raises_instead_of_short_read(tmp_path: Path):
    """少发的字节会让客户端拼出短文件，而 Content-Length 已承诺了长度。
    静默少发正是「hash 不一致」的直接来源，必须报错。"""
    path = tmp_path / "shrink.bin"
    path.write_bytes(b"x" * 100)
    with pytest.raises(IOError):
        list(DR.iter_file_range(path, DR.ByteRange(0, 199), chunk_size=16))


# ═════════════════ HTTP 层：206 / 416 / Accept-Ranges ═════════════════

def test_http_range_returns_206_with_correct_headers(enabled_store):
    ws = _create()
    payload = bytes(range(256)) * 400  # 102400 字节
    _upload(ws, payload, name="大文件.bin")

    response = _download(ws, {"Range": "bytes=100-199"})
    assert response.status_code == 206
    assert response.headers["Content-Range"] == f"bytes 100-199/{len(payload)}"
    assert response.headers["Content-Length"] == "100"
    assert response.content == payload[100:200]
    assert response.headers["Accept-Ranges"] == "bytes"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    # 片段也必须是附件：T-S07-01 的「一律 attachment」不因为是片段就破例。
    assert "attachment" in response.headers["Content-Disposition"]


def test_full_download_advertises_range_support_and_etag(enabled_store):
    ws = _create()
    payload = b"advertise" * 500
    _upload(ws, payload, name="广播.bin")
    response = _download(ws)
    assert response.status_code == 200
    # 不广播 Accept-Ranges，客户端就不会尝试续传，Range 支持等于没做。
    assert response.headers["Accept-Ranges"] == "bytes"
    assert response.headers["ETag"] == '"' + hashlib.sha256(payload).hexdigest() + '"'


def test_unsatisfiable_range_returns_416_with_total_size(enabled_store):
    ws = _create()
    payload = b"short"
    _upload(ws, payload, name="短.bin")
    response = _download(ws, {"Range": "bytes=9999-"})
    assert response.status_code == 416
    # 416 必须带 `bytes */total`，否则客户端不知道该退到哪。
    assert response.headers["Content-Range"] == f"bytes */{len(payload)}"


def test_invalid_range_serves_whole_file_not_an_error(enabled_store):
    ws = _create()
    payload = b"whole-file" * 100
    _upload(ws, payload, name="整份.bin")
    response = _download(ws, {"Range": "bytes=nonsense"})
    assert response.status_code == 200
    assert response.content == payload


def test_multi_range_serves_whole_file(enabled_store):
    """多段合法但不给片段：一个请求塞几千个小段会把响应体和 CPU 撬起来。"""
    ws = _create()
    payload = b"multi" * 1000
    _upload(ws, payload, name="多段.bin")
    response = _download(ws, {"Range": "bytes=0-9,20-29,40-49"})
    assert response.status_code == 200
    assert response.content == payload


# ═════════════════ 阈值二：续传 hash 一致 ═════════════════

def test_resumed_download_reassembles_to_identical_hash(enabled_store):
    """中断后续传：分 7 段取回，拼起来必须与原件逐字节相同。"""
    ws = _create()
    payload = bytes(range(256)) * 500  # 128000 字节
    _upload(ws, payload, name="续传.bin")
    total = len(payload)

    step = total // 7 + 1
    assembled = bytearray()
    while len(assembled) < total:
        start = len(assembled)
        end = min(start + step - 1, total - 1)
        part = _download(ws, {"Range": f"bytes={start}-{end}"})
        assert part.status_code == 206, part.text
        assert part.headers["Content-Range"] == f"bytes {start}-{end}/{total}"
        assembled.extend(part.content)

    assert hashlib.sha256(bytes(assembled)).hexdigest() == hashlib.sha256(payload).hexdigest()
    assert bytes(assembled) == payload


def test_parallel_ranges_reassemble_correctly(enabled_store):
    """并行 Range：四段同时取，顺序拼回仍须逐字节相同。"""
    ws = _create()
    payload = bytes(range(256)) * 600
    _upload(ws, payload, name="并行.bin")
    total = len(payload)
    step = total // 4

    windows = [(i * step, (total - 1) if i == 3 else (i + 1) * step - 1) for i in range(4)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        parts = list(pool.map(
            lambda w: _download(ws, {"Range": f"bytes={w[0]}-{w[1]}"}), windows))

    assert [p.status_code for p in parts] == [206] * 4
    assembled = b"".join(p.content for p in parts)
    assert assembled == payload


def test_stale_if_range_restarts_instead_of_corrupting(enabled_store):
    """**本文件最重要的一条。**

    客户端手上的验证器和服务端当前内容对不上时，继续发片段，
    会让它拼出一个既不是旧版也不是新版的文件——长度对、状态码对、无人报错。
    服务端必须回 200 整份，把「静默损坏」换成「多下一次」。

    这里用「客户端带着一个不匹配的 ETag 来续传」来触发，而不是真的替换制品：
    `artifacts.workspace_id` 的 UNIQUE 约束不允许同一 workspace 换制品
    （见 `test_one_artifact_per_workspace_is_a_schema_invariant`）。
    两种情形走的是同一个分支、要的是同一个结果——**验证器不匹配就不给片段**，
    至于是服务端变了还是客户端记错了，服务端无从分辨，也不需要分辨。
    """
    ws = _create()
    payload = b"A" * 4000
    _upload(ws, payload, name="会变的.bin", key="if-range-original-0001")

    head = _download(ws, {"Range": "bytes=0-999"})
    assert head.status_code == 206
    current_etag = head.headers["ETag"]

    stale_etag = DR.etag_for(hashlib.sha256(b"an earlier version").hexdigest())
    assert stale_etag != current_etag

    resumed = _download(ws, {"Range": "bytes=1000-", "If-Range": stale_etag})
    assert resumed.status_code == 200, "验证器对不上却仍发片段 ⇒ 客户端会拼出损坏文件"
    assert resumed.content == payload
    assert resumed.headers["ETag"] == current_etag


def test_if_range_matching_etag_still_serves_the_partial(enabled_store):
    """反向锁：ETag 没变时不能因为「保险」就退化成整份——那等于取消续传。"""
    ws = _create()
    payload = b"stable" * 800
    _upload(ws, payload, name="不变.bin")
    etag = _download(ws).headers["ETag"]
    resumed = _download(ws, {"Range": "bytes=100-199", "If-Range": etag})
    assert resumed.status_code == 206
    assert resumed.content == payload[100:200]


def test_served_etag_matches_actually_delivered_bytes(enabled_store):
    """ETag 是服务端自报的，必须与实发字节对得上，否则续传校验建在沙上。"""
    ws = _create()
    payload = b"\x00\xff" * 5000
    _upload(ws, payload, name="自证.bin")
    response = _download(ws)
    assert response.headers["ETag"] == '"' + hashlib.sha256(response.content).hexdigest() + '"'


# ═════════════════ 阈值三：ZIP 无丢失 / 覆盖 / 穿越 ═════════════════

@pytest.mark.parametrize("hostile", [
    "../../etc/passwd",
    "../../../root/.ssh/authorized_keys",
    "/etc/shadow",
    "C:\\Windows\\System32\\drivers\\etc\\hosts",
    "subdir/nested/file.txt",
    "..\\..\\windows\\win.ini",
    "..",
    ".",
])
def test_archive_strips_every_path_component_from_entry_names(tmp_path, hostile):
    """归档端的 zip-slip：我们是**生产者**，只要把 `../..` 写成条目名，
    任何没做防护的解压器都会被我们打穿。上传侧已经挡过一层，这里再挡一层——
    历史导入、直接写库、将来任何新入库路径都可能绕过上传检查。"""
    member = _member(tmp_path, hostile, b"payload", sort_key="s1")
    destination = tmp_path / "out.zip"
    manifest = BA.build_archive([member], destination)

    entry = manifest["entries"][0]["entry_name"]
    assert "/" not in entry and "\\" not in entry
    assert not entry.startswith("..")
    assert not entry.startswith("/")
    assert BA.verify_archive(destination, manifest) == []


@pytest.mark.parametrize("raw", ["file\x00.txt", "报表\x07.csv", "\x1b[31m.txt"])
def test_archive_strips_nul_and_control_characters(tmp_path, raw):
    member = _member(tmp_path, raw, b"x", sort_key="s1")
    manifest = BA.build_archive([member], tmp_path / "c.zip")
    entry = manifest["entries"][0]["entry_name"]
    assert "\x00" not in entry
    assert not any(ord(ch) < 32 for ch in entry)
    assert manifest["entries"][0]["renamed"] is True
    assert manifest["entries"][0]["rename_reasons"], "改写必须留痕，否则用户无从判断"


def test_duplicate_names_do_not_overwrite_each_other(tmp_path):
    """同名条目会被多数解压器**静默覆盖**——用户以为拿到 2 个，实际 1 个。"""
    members = [
        _member(tmp_path, "报表.xlsx", b"first-content", sort_key="a"),
        _member(tmp_path, "报表.xlsx", b"second-content", sort_key="b"),
        _member(tmp_path, "报表.xlsx", b"third-content", sort_key="c"),
    ]
    destination = tmp_path / "dup.zip"
    manifest = BA.build_archive(members, destination)

    assert manifest["entry_count"] == 3
    names = [e["entry_name"] for e in manifest["entries"]]
    assert len(set(names)) == 3
    assert names == ["报表.xlsx", "报表 (2).xlsx", "报表 (3).xlsx"]

    with zipfile.ZipFile(destination) as archive:
        recovered = {archive.read(n) for n in names}
    assert recovered == {b"first-content", b"second-content", b"third-content"}
    assert BA.verify_archive(destination, manifest) == []


def test_case_only_difference_is_a_collision_because_the_filesystem_says_so(tmp_path):
    """`Report.xlsx` 与 `report.xlsx` 在归档里是两个条目，
    落到 macOS / Windows 上是一个。按字节比对的去重会漏掉它，于是丢文件。"""
    members = [
        _member(tmp_path, "Report.xlsx", b"upper", sort_key="a"),
        _member(tmp_path, "report.xlsx", b"lower", sort_key="b"),
    ]
    manifest = BA.build_archive(members, tmp_path / "case.zip")
    names = [e["entry_name"] for e in manifest["entries"]]
    assert len({BA.collision_key(n) for n in names}) == 2, f"解压端会碰撞：{names}"


def test_unicode_normalization_difference_is_a_collision(tmp_path):
    """macOS 用 NFD，多数来源用 NFC。`é` 的两种写法字节不同、看起来一样、解压时碰撞。"""
    nfc, nfd = "café.txt", "cafe\u0301.txt"
    assert nfc != nfd
    members = [
        _member(tmp_path, nfc, b"one", sort_key="a"),
        _member(tmp_path, nfd, b"two", sort_key="b"),
    ]
    manifest = BA.build_archive(members, tmp_path / "nfc.zip")
    names = [e["entry_name"] for e in manifest["entries"]]
    assert len({BA.collision_key(n) for n in names}) == 2, f"解压端会碰撞：{names}"


def test_trailing_dot_and_space_collision_is_resolved(tmp_path):
    """Windows 静默去掉结尾的点和空格，于是 `a .txt` 与 `a.txt` 碰撞。
    我们主动去掉，让碰撞在自己这里可见、可消解。"""
    members = [
        _member(tmp_path, "账单.txt", b"plain", sort_key="a"),
        _member(tmp_path, "账单.txt ", b"trailing-space", sort_key="b"),
        _member(tmp_path, "账单.txt.", b"trailing-dot", sort_key="c"),
    ]
    manifest = BA.build_archive(members, tmp_path / "trail.zip")
    names = [e["entry_name"] for e in manifest["entries"]]
    assert len({BA.collision_key(n) for n in names}) == 3, f"解压端会碰撞：{names}"


@pytest.mark.parametrize("reserved", ["CON", "NUL.txt", "com1.csv", "LPT9.bin"])
def test_windows_reserved_device_names_are_escaped(tmp_path, reserved):
    """写 `CON` 等于写设备而不是文件——解压在 Windows 上会失败或写错地方。"""
    member = _member(tmp_path, reserved, b"x", sort_key="a")
    manifest = BA.build_archive([member], tmp_path / "res.zip")
    entry = manifest["entries"][0]["entry_name"]
    assert entry.split(".", 1)[0].upper() not in BA._WINDOWS_RESERVED
    assert manifest["entries"][0]["renamed"] is True


@pytest.mark.parametrize("name", [
    "中文文件名.xlsx", "日本語のファイル.csv", "한국어.txt",
    "emoji-📊-报表.xlsx", "with spaces and (parens).pdf",
    "Ünïcödé-àccénts.txt", "«guillemets».txt", "很长" * 80 + ".txt",
])
def test_special_character_names_survive_the_round_trip(tmp_path, name):
    payload = name.encode("utf-8") * 10
    member = _member(tmp_path, name, payload, sort_key="a")
    destination = tmp_path / "uni.zip"
    manifest = BA.build_archive([member], destination)
    entry = manifest["entries"][0]["entry_name"]
    with zipfile.ZipFile(destination) as archive:
        assert archive.read(entry) == payload
    assert BA.verify_archive(destination, manifest) == []


@pytest.mark.parametrize("count", [50, 500])
def test_batch_of_50_and_500_loses_nothing(tmp_path, count):
    """AC 点名的 50/500。逐项 hash 复核，不是只数条目数——
    条目数对而内容错位，是重名去重写错时的典型表现。"""
    members = [
        _member(tmp_path, f"报表-{i:04d}.csv", f"row,{i}\n".encode() * 20, sort_key=f"k{i:05d}")
        for i in range(count)
    ]
    destination = tmp_path / f"batch-{count}.zip"
    manifest = BA.build_archive(members, destination)

    assert manifest["entry_count"] == count
    assert BA.verify_archive(destination, manifest) == []
    with zipfile.ZipFile(destination) as archive:
        for member, entry in zip(
            sorted(members, key=lambda m: (m.sort_key, m.sha256)), manifest["entries"]
        ):
            assert hashlib.sha256(archive.read(entry["entry_name"])).hexdigest() == member.sha256


def test_manifest_entry_name_is_reserved_so_a_user_file_is_not_overwritten(tmp_path):
    """用户真上传了一个叫 `_kmfa_manifest.json` 的文件时，
    不能被归档自己的清单覆盖——那是发生在「防覆盖」功能内部的一次数据丢失。"""
    member = _member(tmp_path, BA.MANIFEST_ENTRY_NAME, b"user-owned-content", sort_key="a")
    destination = tmp_path / "reserved.zip"
    manifest = BA.build_archive([member], destination)

    entry = manifest["entries"][0]["entry_name"]
    assert entry != BA.MANIFEST_ENTRY_NAME
    with zipfile.ZipFile(destination) as archive:
        assert archive.read(entry) == b"user-owned-content"
        embedded = json.loads(archive.read(BA.MANIFEST_ENTRY_NAME).decode("utf-8"))
    assert embedded["entries"] == manifest["entries"]


def test_embedded_manifest_lets_the_archive_verify_itself_offline(tmp_path):
    """归档离开本系统后（转发、备份、拷进 U 盘）响应头就没了，
    自带清单是它唯一还能自证的东西。"""
    members = [_member(tmp_path, f"f{i}.txt", f"c{i}".encode(), sort_key=f"k{i}") for i in range(5)]
    destination = tmp_path / "selfverify.zip"
    manifest = BA.build_archive(members, destination)

    with zipfile.ZipFile(destination) as archive:
        embedded = json.loads(archive.read(BA.MANIFEST_ENTRY_NAME).decode("utf-8"))
        for record in embedded["entries"]:
            assert hashlib.sha256(
                archive.read(record["entry_name"])).hexdigest() == record["sha256"]
    assert embedded["entry_count"] == 5


def test_verify_archive_detects_a_tampered_member(tmp_path):
    """复核函数本身要能抓到问题，否则它只是一句「PASS」。"""
    members = [_member(tmp_path, "a.txt", b"original", sort_key="a")]
    destination = tmp_path / "tamper.zip"
    manifest = BA.build_archive(members, destination)

    forged = tmp_path / "forged.zip"
    with zipfile.ZipFile(destination) as src, zipfile.ZipFile(forged, "w") as dst:
        for name in src.namelist():
            data = b"tampered!" if name == "a.txt" else src.read(name)
            dst.writestr(name, data)

    problems = BA.verify_archive(forged, manifest)
    assert any("摘要不符" in p for p in problems), problems


def test_source_bytes_disagreeing_with_recorded_digest_aborts(tmp_path):
    """入库摘要与实读字节不符 ⇒ 存储已损坏。必须中断：
    继续下去会打出一个 manifest 与内容不符、但自校验通过的归档
    （因为 manifest 抄的是数据库）。"""
    path = tmp_path / "rot.bin"
    path.write_bytes(b"actual-bytes")
    member = BA.ArchiveMember(
        source_path=path, original_name="rot.bin",
        sha256=hashlib.sha256(b"what-the-db-thinks").hexdigest(),
        size_bytes=12, sort_key="a")
    with pytest.raises(IOError, match="不符"):
        BA.build_archive([member], tmp_path / "rot.zip")
    assert not (tmp_path / "rot.zip").exists()


# ═════════════════ 阈值四：取消与重试 ═════════════════

def test_retry_produces_a_byte_identical_archive(tmp_path):
    """「失败可重试」要可验证，就得能判断「重试出来的和原来是同一份」。
    时间戳钉死在 ZIP 纪元，条目稳定排序 ⇒ 归档是输入集合的纯函数。"""
    members = [_member(tmp_path, f"f{i}.txt", f"c{i}".encode(), sort_key=f"k{i}") for i in range(8)]
    first = BA.build_archive(members, tmp_path / "one.zip")
    second = BA.build_archive(list(reversed(members)), tmp_path / "two.zip")

    assert first["archive_sha256"] == second["archive_sha256"], "输入顺序变了归档就变 ⇒ 无法自证"
    assert (tmp_path / "one.zip").read_bytes() == (tmp_path / "two.zip").read_bytes()


def test_cancellation_leaves_no_archive_at_all(tmp_path):
    """取消必须是异常，不能是「返回一个短归档」——
    半份 ZIP 能正常打开、条目少而已，用户不会知道它被截断了。"""
    members = [_member(tmp_path, f"f{i}.txt", b"x" * 1000, sort_key=f"k{i}") for i in range(20)]
    destination = tmp_path / "cancelled.zip"
    seen = {"n": 0}

    def should_cancel() -> bool:
        seen["n"] += 1
        return seen["n"] > 5

    with pytest.raises(BA.ArchiveCancelled):
        BA.build_archive(members, destination, should_cancel=should_cancel)

    assert not destination.exists(), "取消后留下了一份看起来完整的归档"
    assert not destination.with_name(destination.name + ".partial").exists()


def test_a_failed_build_can_simply_be_retried(tmp_path):
    """取消之后重试，产出与从未失败过一模一样——这就是「可重试」的含义。"""
    members = [_member(tmp_path, f"f{i}.txt", b"y" * 500, sort_key=f"k{i}") for i in range(10)]
    destination = tmp_path / "retry.zip"
    calls = {"n": 0}

    with pytest.raises(BA.ArchiveCancelled):
        BA.build_archive(
            members, destination,
            should_cancel=lambda: (calls.__setitem__("n", calls["n"] + 1), calls["n"] > 3)[1])

    after_retry = BA.build_archive(members, destination)
    clean = BA.build_archive(members, tmp_path / "clean.zip")
    assert after_retry["archive_sha256"] == clean["archive_sha256"]
    assert BA.verify_archive(destination, after_retry) == []


# ═════════════════ pass_gate：资源受控 ═════════════════

def test_build_never_reads_more_than_one_chunk_at_a_time(tmp_path, monkeypatch):
    """stop_condition 的直接反证：如果实现某处 `read()` 了整个文件，
    这里会看到一次远大于 chunk 的读取。"""
    payload = b"z" * (2 * 1024 * 1024)
    member = _member(tmp_path, "big.bin", payload, sort_key="a")

    reads: list[int] = []
    real_open = Path.open

    def watched_open(self, *args, **kwargs):
        handle = real_open(self, *args, **kwargs)
        if self == member.source_path:
            real_read = handle.read

            def read(size=-1):
                block = real_read(size)
                reads.append(len(block))
                return block

            handle.read = read  # type: ignore[method-assign]
        return handle

    monkeypatch.setattr(Path, "open", watched_open)
    BA.build_archive([member], tmp_path / "chunked.zip", chunk_size=64 * 1024)
    assert reads, "没有观察到任何读取，测试本身失效了"
    assert max(reads) <= 64 * 1024


def test_peak_memory_stays_far_below_archive_size(tmp_path):
    """500 个条目共 ~10 MiB，峰值内存必须与归档大小无关。"""
    members = [
        _member(tmp_path, f"m{i:03d}.bin", bytes((i * 7) % 251 for _ in range(20480)),
                sort_key=f"k{i:03d}")
        for i in range(500)
    ]
    destination = tmp_path / "mem.zip"

    tracemalloc.start()
    try:
        BA.build_archive(members, destination)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    total = sum(m.size_bytes for m in members)
    assert total > 9 * 1024 * 1024
    assert peak < 4 * 1024 * 1024, f"峰值 {peak} 字节，接近归档总量 ⇒ 整份进了内存"


def test_sync_batch_limits_state_the_boundary(tmp_path):
    """「太大了」这种提示会让人反复试探，每次试探都是一次真实的资源消耗。"""
    assert BA.sync_batch_rejection(BA.MAX_SYNC_ENTRIES, 1024) is None
    over = BA.sync_batch_rejection(BA.MAX_SYNC_ENTRIES + 1, 1024)
    assert over and str(BA.MAX_SYNC_ENTRIES) in over
    big = BA.sync_batch_rejection(1, BA.MAX_SYNC_BYTES + 1)
    assert big and "MiB" in big


# ═════════════════ HTTP 层：批量端点 ═════════════════

def test_batch_endpoint_returns_a_verifiable_zip(enabled_store):
    """端到端：鉴权 → 物化 → 流式打包 → 自带清单可离线复核。

    只有一个条目，因为 schema 只允许一个（见
    `test_one_artifact_per_workspace_is_a_schema_invariant`）。
    条目数由归档层的 50/500 用例覆盖；这里验的是 HTTP 这一层接得对不对。
    """
    ws = _create()
    name = "项目资料.csv"
    payload = b"col_a,col_b\n1,2\n" * 30
    contents = {name: payload}
    _upload(ws, payload, name=name, key="batch-http-single-entry-0001")

    response = _post(f"{BASE}/workspaces/{ws['_id']}/artifact/batch", headers=_auth(ws))
    assert response.status_code == 200, response.text
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "attachment" in response.headers["Content-Disposition"]
    assert response.headers["X-KMFA-Archive-Entries"] == "1"
    assert response.headers["X-KMFA-Archive-SHA256"] == hashlib.sha256(response.content).hexdigest()

    with zipfile.ZipFile(BytesIO(response.content)) as archive:
        embedded = json.loads(archive.read(BA.MANIFEST_ENTRY_NAME).decode("utf-8"))
        recovered = {archive.read(r["entry_name"]) for r in embedded["entries"]}
    assert recovered == set(contents.values())


def test_batch_manifest_previews_without_producing_bytes(enabled_store):
    """预演：花掉带宽之前先看到会拿到什么。

    重名改写的预演逻辑在归档层测（`assign_entry_names` 那一组）；
    这里验的是 HTTP 预演口**不产出字节**、且报出与真打包一致的上限值。
    """
    ws = _create()
    _upload(ws, b"content", name="同名报表.csv", key="manifest-preview-0001-abcd")

    response = _post(
        f"{BASE}/workspaces/{ws['_id']}/artifact/batch/manifest", headers=_auth(ws))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["entry_count"] == 1
    assert body["rejection"] is None
    assert body["entries"][0]["entry_name"] == "同名报表.csv"
    assert body["max_sync_entries"] == BA.MAX_SYNC_ENTRIES
    assert body["max_sync_bytes"] == BA.MAX_SYNC_BYTES
    # 预演不产出字节：响应是 JSON，不是归档。
    assert "application/json" in response.headers["content-type"]


def test_batch_over_the_sync_limit_is_refused_not_truncated(enabled_store, monkeypatch):
    """超限不降级成截断的归档：悄悄少打包几个，用户会以为自己拿全了。

    上限压到 0，让唯一那个条目也越界——测的是**拒绝这条路径**，
    与上限的具体数值无关。
    """
    ws = _create()
    monkeypatch.setattr(BA, "MAX_SYNC_ENTRIES", 0)
    _upload(ws, b"over-limit", name="超限.txt", key="batch-over-limit-0001-abcd")

    response = _post(f"{BASE}/workspaces/{ws['_id']}/artifact/batch", headers=_auth(ws))
    assert response.status_code == 413
    assert "0" in response.json()["detail"], "拒绝时必须说清界限值，否则用户只能反复试探"


def test_batch_across_workspaces_is_404_not_a_partial_archive(enabled_store):
    """越权=0。批量接口与单件走同一条 `_authorize`——
    自建鉴权是「单件补了、批量忘了」这类越权的常见来源。"""
    owner = _create("批量本体")
    # 先把本体的东西传完再造入侵者：全局客户端的 cookie jar 只留最后一个会话，
    # 顺序反了会变成「用入侵者的会话往本体里传」，测的就不是越权了。
    _upload(owner, b"secret-business-data", name="机密.csv", key="batch-cross-ws-0001-abcd")
    intruder = _create("批量入侵者")

    response = _post(
        f"{BASE}/workspaces/{owner['_id']}/artifact/batch", headers=_auth(intruder))
    assert response.status_code == 404
    assert response.status_code != 403, "403 会确认该 workspace 存在"


def test_batch_without_credentials_is_404(enabled_store):
    ws = _create()
    _upload(ws, b"anything", name="a.txt", key="batch-noauth-0001-abcdefgh")
    # 用一个全新的客户端，而不是清掉全局客户端的 cookie：
    # 「没有凭据」必须是**结构上**没有，不能依赖某一步记得清干净。
    stranger = TestClient(app, base_url=ORIGIN, headers={"Origin": ORIGIN})
    for path in ("artifact/batch", "artifact/batch/manifest"):
        response = stranger.post(f"{BASE}/workspaces/{ws['_id']}/{path}")
        assert response.status_code == 404, path


def test_batch_records_an_audit_event(enabled_store):
    """越权追溯的唯一依据。批量和单件都必须留痕。"""
    ws = _create()
    _upload(ws, b"audited", name="留痕.txt", key="batch-audit-0001-abcdefgh")
    _post(f"{BASE}/workspaces/{ws['_id']}/artifact/batch", headers=_auth(ws))

    events = client.get(f"{BASE}/workspaces/{ws['_id']}/audit-events", headers=_auth(ws)).json()
    actions = [e["action"] for e in events["events"]]
    assert "artifact_batch_download" in actions
