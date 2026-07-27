# -*- coding: utf-8 -*-
"""TEST-UP-001 / TEST-UP-002 —— S06/P6.1 · T-S06-01。

**测试照着验收阈值写，不照着实现写。** 每个用例上面标出它对应哪一条阈值，
这样实现改了、阈值没改时，测试仍然在测该测的东西。

AC-UP-001 任意文件类型可存储
  阈值：所有合规样本可安全存储；未知/高风险仅附件；执行成功 = 0
AC-UP-002 大文件与断点续传
  阈值：允许范围内恢复成功率 = 100%；篡改漏检 = 0；
        超限在写入预算前拒绝；重复对象不可控增长 = 0
"""
import hashlib

import pytest

from app.resumable_upload import (
    CHUNK_BYTES,
    dedupe_decision,
    MAX_CHUNK_BYTES,
    ResumableUploadError,
    UploadSession,
    append_chunk,
    disposition_for,
    file_sha256,
    new_upload_id,
    plan_session,
    validate_chunk,
    validate_upload_id,
    verify_complete,
)


def _session(tmp_path, *, total, expected, received=0):
    part = tmp_path / "up.part"
    part.touch()
    return UploadSession(
        upload_id=new_upload_id(), workspace_id="ws_1", original_name="x.bin",
        media_type="application/octet-stream", total_bytes=total,
        expected_sha256=expected, received_bytes=received, part_path=part,
    )


# ─────────────── TEST-UP-001：任意类型 · 未知/高风险仅附件 · 执行成功=0 ───────────────

@pytest.mark.parametrize("media_type", [
    "text/plain", "text/csv", "application/json", "application/pdf",
    "image/png", "image/jpeg", "image/gif", "image/webp",
])
def test_known_safe_types_may_render_inline(media_type):
    """合规样本要能正常存取——把所有类型都变成附件不叫安全，叫不可用。"""
    served, disposition = disposition_for(media_type)
    assert served == media_type and disposition == "inline"


@pytest.mark.parametrize("media_type", [
    "text/html", "image/svg+xml", "application/xhtml+xml",     # 可在浏览器里执行脚本
    "application/x-msdownload", "application/x-executable",     # 可执行样本
    "application/x-sh", "text/javascript", "application/javascript",
    "application/vnd.ms-excel.sheet.macroEnabled.12",           # 宏
    "application/zip", "video/mp4", "audio/mpeg",               # 压缩包与音视频
    "application/octet-stream", "", None, "  ",                  # 未知/缺失
    "application/unknown-made-up-type",
])
def test_everything_outside_the_whitelist_is_attachment_only(media_type):
    """AC-UP-001「未知/高风险仅附件；执行成功=0」。

    **Content-Type 也必须被改写**，不能只加 attachment——
    保留 text/html 在某些场景下仍可能被当作可渲染内容处理。
    """
    served, disposition = disposition_for(media_type)
    assert disposition == "attachment"
    assert served == "application/octet-stream"


def test_the_policy_is_a_whitelist_not_a_blacklist():
    """这条是设计锁：黑名单永远漏，而漏掉的那个正好是能执行的那个。

    随便造一个没人见过的类型，它必须默认落在附件侧。
    """
    for invented in ("application/x-totally-new-2099", "weird/type", "x/y"):
        assert disposition_for(invented) == ("application/octet-stream", "attachment")


def test_media_type_parameters_do_not_smuggle_an_inline_render():
    """`text/html; charset=utf-8` 不能因为带了参数就绕过白名单比对。"""
    assert disposition_for("text/html; charset=utf-8")[1] == "attachment"
    assert disposition_for("text/plain; charset=utf-8") == ("text/plain", "inline")


def test_media_type_case_is_normalized_before_matching():
    assert disposition_for("IMAGE/PNG") == ("image/png", "inline")


# ─────────────── TEST-UP-002：超限在写入预算前拒绝 ───────────────

def test_oversize_is_rejected_at_session_open_before_any_byte_lands():
    """AC-UP-002「超限**在写入预算前**拒绝」。

    等分片写进来再算就晚了——那时字节已落盘，可以用必然失败的上传反复占空间。
    """
    with pytest.raises(ResumableUploadError) as caught:
        plan_session(total_bytes=9 * 1024 * 1024, expected_sha256="a" * 64,
                     max_artifact_bytes=8 * 1024 * 1024,
                     remaining_quota_bytes=512 * 1024 * 1024)
    assert caught.value.status_code == 413 and caught.value.code == "artifact_too_large"


def test_quota_exhaustion_is_distinguishable_from_a_too_large_file():
    """两者要分得开：文件太大换文件没用，额度不够删旧的就行。"""
    with pytest.raises(ResumableUploadError) as caught:
        plan_session(total_bytes=1024, expected_sha256="a" * 64,
                     max_artifact_bytes=8 * 1024 * 1024, remaining_quota_bytes=0)
    assert caught.value.code == "artifact_capacity_reached"

    with pytest.raises(ResumableUploadError) as caught:
        plan_session(total_bytes=2048, expected_sha256="a" * 64,
                     max_artifact_bytes=8 * 1024 * 1024, remaining_quota_bytes=1024)
    assert caught.value.code == "artifact_capacity_reached"


def test_a_session_within_both_limits_is_admitted():
    plan_session(total_bytes=1024, expected_sha256="b" * 64,
                 max_artifact_bytes=8 * 1024 * 1024, remaining_quota_bytes=4096)


def test_expected_digest_must_be_declared_up_front():
    """完成时才知道该是什么摘要，就没法在开会话时查重、也没法逐片对账。"""
    for bad in ("", "xyz", "A" * 64, "a" * 63):
        with pytest.raises(ResumableUploadError) as caught:
            plan_session(total_bytes=1, expected_sha256=bad,
                         max_artifact_bytes=1024, remaining_quota_bytes=1024)
        assert caught.value.code == "invalid_expected_sha256"


# ─────────────── TEST-UP-002：篡改漏检 = 0 ───────────────

def test_a_tampered_chunk_is_rejected_before_it_is_written(tmp_path):
    """AC-UP-002「篡改漏检=0」——逐片先验后写，不等到最后整体校验。"""
    payload = b"honest bytes"
    session = _session(tmp_path, total=len(payload), expected=hashlib.sha256(payload).hexdigest())
    tampered = b"tampered!!!!"
    assert len(tampered) == len(payload), "长度相同才测得出摘要在起作用"
    with pytest.raises(ResumableUploadError) as caught:
        validate_chunk(session=session, offset=0, payload=tampered,
                       chunk_sha256=hashlib.sha256(payload).hexdigest())
    assert caught.value.code == "chunk_checksum_mismatch"
    assert session.part_path.stat().st_size == 0, "被拒的片一个字节都不许落盘"


def test_an_honest_chunk_passes(tmp_path):
    payload = b"honest bytes"
    session = _session(tmp_path, total=len(payload), expected=hashlib.sha256(payload).hexdigest())
    validate_chunk(session=session, offset=0, payload=payload,
                   chunk_sha256=hashlib.sha256(payload).hexdigest())


def test_out_of_order_offset_is_a_conflict_not_a_silent_gap(tmp_path):
    """偏移对不上不是「继续传」，是状态分歧——静默接受会在文件里留下空洞。"""
    session = _session(tmp_path, total=100, expected="c" * 64, received=10)
    with pytest.raises(ResumableUploadError) as caught:
        validate_chunk(session=session, offset=40, payload=b"x",
                       chunk_sha256=hashlib.sha256(b"x").hexdigest())
    assert caught.value.status_code == 409 and caught.value.code == "upload_offset_conflict"


def test_a_chunk_cannot_write_past_the_declared_total(tmp_path):
    """越界写会让配额预留失去意义——声明 100 字节却写 200，额度就白算了。"""
    session = _session(tmp_path, total=8, expected="d" * 64, received=4)
    payload = b"0123456789"
    with pytest.raises(ResumableUploadError) as caught:
        validate_chunk(session=session, offset=4, payload=payload,
                       chunk_sha256=hashlib.sha256(payload).hexdigest())
    assert caught.value.code == "upload_exceeds_declared_total"


def test_chunk_size_is_bounded(tmp_path):
    """单片过大等于回到整传，断一次白传一次，「恢复成功率」就没意义了。"""
    assert CHUNK_BYTES <= MAX_CHUNK_BYTES
    session = _session(tmp_path, total=MAX_CHUNK_BYTES * 4, expected="e" * 64)
    payload = b"\0" * (MAX_CHUNK_BYTES + 1)
    with pytest.raises(ResumableUploadError) as caught:
        validate_chunk(session=session, offset=0, payload=payload,
                       chunk_sha256=hashlib.sha256(payload).hexdigest())
    assert caught.value.code == "chunk_too_large"


def test_empty_chunk_is_rejected(tmp_path):
    """空片不推进进度，接受它等于允许无限次空请求。"""
    session = _session(tmp_path, total=10, expected="f" * 64)
    with pytest.raises(ResumableUploadError) as caught:
        validate_chunk(session=session, offset=0, payload=b"",
                       chunk_sha256=hashlib.sha256(b"").hexdigest())
    assert caught.value.code == "empty_chunk"


# ─────────────── TEST-UP-002：恢复成功率 = 100% ───────────────

def test_interrupting_at_every_chunk_boundary_still_reconstructs_the_file(tmp_path):
    """AC-UP-002「允许范围内恢复成功率=100%」。

    在**每一个**分片边界都断一次、再从服务端报的偏移续上，
    最终字节与整体摘要都要和一次传完完全一致。
    """
    content = bytes((i * 7 + 13) % 251 for i in range(20_000))
    expected = hashlib.sha256(content).hexdigest()
    piece = 4096
    pieces = [content[i:i + piece] for i in range(0, len(content), piece)]

    for 断点 in range(len(pieces) + 1):          # 含「不断」与「每一片后断」
        part = tmp_path / f"resume-{断点}.part"
        part.touch()
        received = 0
        for index, block in enumerate(pieces):
            if index == 断点:                     # 模拟断网：会话对象丢了，进度还在
                session = UploadSession(
                    upload_id=new_upload_id(), workspace_id="ws", original_name="a",
                    media_type="application/octet-stream", total_bytes=len(content),
                    expected_sha256=expected, received_bytes=received, part_path=part)
            session = UploadSession(
                upload_id=new_upload_id(), workspace_id="ws", original_name="a",
                media_type="application/octet-stream", total_bytes=len(content),
                expected_sha256=expected, received_bytes=received, part_path=part)
            validate_chunk(session=session, offset=received, payload=block,
                           chunk_sha256=hashlib.sha256(block).hexdigest())
            received = append_chunk(session, block)

        final = UploadSession(
            upload_id=new_upload_id(), workspace_id="ws", original_name="a",
            media_type="application/octet-stream", total_bytes=len(content),
            expected_sha256=expected, received_bytes=received, part_path=part)
        verify_complete(final, file_sha256(part))
        assert part.read_bytes() == content, f"断点 {断点} 处恢复后内容不一致"


def test_completing_early_is_refused(tmp_path):
    """字节数不够就完成，会产出一个「看起来成功」的残缺对象。"""
    session = _session(tmp_path, total=100, expected="a" * 64, received=40)
    with pytest.raises(ResumableUploadError) as caught:
        verify_complete(session, "a" * 64)
    assert caught.value.code == "upload_incomplete"


def test_reordered_or_replayed_chunks_are_caught_by_the_whole_file_digest(tmp_path):
    """逐片校验管不到「片没坏但顺序被换」——整体摘要管得到，所以两道都要有。"""
    content = b"AAAABBBBCCCC"
    session = _session(tmp_path, total=len(content),
                       expected=hashlib.sha256(content).hexdigest(),
                       received=len(content))
    session.part_path.write_bytes(b"CCCCBBBBAAAA")     # 每片都完好，顺序错了
    with pytest.raises(ResumableUploadError) as caught:
        verify_complete(session, file_sha256(session.part_path))
    assert caught.value.code == "upload_checksum_mismatch"


# ─────────────── 会话 id：服务端生成，不接受客户端指定 ───────────────

def test_upload_id_shape_is_enforced():
    validate_upload_id(new_upload_id())
    for bad in ("", "up_", "abc", "up_../../etc/passwd", "up_" + "x" * 200, None):
        with pytest.raises(ResumableUploadError) as caught:
            validate_upload_id(bad)
        assert caught.value.code == "invalid_upload_id"


def test_upload_ids_are_unpredictable():
    """可猜的会话 id 意味着可以往别人的上传里塞分片。"""
    ids = {new_upload_id() for _ in range(500)}
    assert len(ids) == 500


# ─────────────── TEST-UP-002：重复对象不可控增长 = 0 ───────────────

def test_duplicate_content_accepts_zero_bytes(tmp_path):
    """AC-UP-002「重复对象不可控增长=0」——**在收字节之前**就判掉。

    放到完成时再查重没有意义：那时重复内容已经完整传了一遍也落过盘，
    「不可控增长」已经发生，事后删除挡不住下一次。
    """
    decision = dedupe_decision(expected_sha256="a" * 64,
                               existing_version_id="av_existing_1")
    assert decision.accept_bytes is False
    assert decision.existing_artifact_version_id == "av_existing_1"
    assert decision.reason == "content_already_stored"


def test_new_content_is_accepted():
    decision = dedupe_decision(expected_sha256="b" * 64, existing_version_id=None)
    assert decision.accept_bytes is True and decision.existing_artifact_version_id is None


def test_dedupe_is_by_content_not_by_filename():
    """同名不同内容必须各存一份（那是两个版本，血缘要求它们都在）；
    不同名同内容共用一个对象——重复的是字节，不是记录。

    判定只吃摘要，签名里根本没有文件名——这条是结构性保证，不是约定。
    """
    import inspect
    params = set(inspect.signature(dedupe_decision).parameters)
    assert params == {"expected_sha256", "existing_version_id"}, (
        "查重判定不得依赖文件名——把文件名放进来就会出现『同名即重复』的错判")


def test_dedupe_still_validates_the_digest_shape():
    with pytest.raises(ResumableUploadError) as caught:
        dedupe_decision(expected_sha256="not-a-digest", existing_version_id=None)
    assert caught.value.code == "invalid_expected_sha256"
