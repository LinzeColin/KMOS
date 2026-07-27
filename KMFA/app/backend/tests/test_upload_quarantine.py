# -*- coding: utf-8 -*-
"""TEST-UP-003 —— S06/P6.2 · T-S06-02 quarantine-first 文件安全流水线。

AC-UP-003 阈值：**恶意/畸形逃逸 = 0；解析不在主进程执行；标准合法夹具误拒 < 1%**。

前两条靠「每类攻击都有一条用例，一条都不许漏」来证；
第三条是**反向**指标——它防的是把上面两条做过头：
把所有东西都判成恶意，逃逸确实为 0，产品也确实不能用了。
所以本文件末尾有一组合法夹具，误拒率必须为 0。
"""
import io
import zipfile

import pytest

from app.upload_quarantine import (
    EICAR,
    MAX_ARCHIVE_RATIO,
    STATE_CLEAN,
    STATE_PENDING,
    STATE_QUARANTINED,
    STATE_SCAN_TIMEOUT,
    detect_magic,
    inspect_archive,
    magic_conflicts,
    rollback_verdict,
    safe_filename,
    scan,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def _file(tmp_path, name, payload: bytes):
    path = tmp_path / name
    path.write_bytes(payload)
    return path


# ─────────────── 路径穿越与文件名（在**落盘前**判） ───────────────

@pytest.mark.parametrize("name,keyword", [
    ("../../etc/passwd", "路径穿越"),
    ("..\\..\\windows\\system32\\cmd.exe", "路径穿越"),
    ("/etc/shadow", "路径分隔符"),
    ("C:\\Windows\\evil.dll", "路径分隔符"),
    ("正常\x00.png", "NUL"),
    ("CON", "保留设备名"),
    ("nul.txt", "保留设备名"),
    ("报表.pdf.", "结尾有点或空格"),
    ("报表.pdf ", "结尾有点或空格"),
])
def test_hostile_filenames_are_all_flagged(name, keyword):
    _, problems = safe_filename(name)
    assert any(keyword in p for p in problems), f"{name} 未被识别：{problems}"


@pytest.mark.parametrize("name", ["发票.pdf.exe", "照片.jpg.scr", "文档.docx.js", "包.tar.sh"])
def test_double_extension_is_flagged(name):
    """双扩展骗的是两拨人：只看最后一段的和只看第一段的，各能骗一批。"""
    _, problems = safe_filename(name)
    assert any("双扩展" in p for p in problems), problems


def test_a_single_dangerous_extension_is_also_flagged():
    _, problems = safe_filename("installer.exe")
    assert any("可执行类扩展" in p for p in problems)


def test_empty_filename_is_refused():
    assert safe_filename("")[1] and safe_filename(None)[1] and safe_filename("   ")[1]


# ─────────────── MIME 欺骗（以内容为准，不信声明） ───────────────

def test_magic_detects_what_it_actually_is():
    assert detect_magic(b"MZ\x90\x00") == "application/x-msdownload"
    assert detect_magic(b"\x7fELF\x02") == "application/x-executable"
    assert detect_magic(PNG) == "image/png"
    assert detect_magic(b"%PDF-1.7") == "application/pdf"
    assert detect_magic(b"#!/bin/sh\n") == "application/x-sh"


def test_declaring_png_while_being_an_executable_is_a_conflict():
    assert magic_conflicts("image/png", "application/x-msdownload") is True


def test_zip_magic_is_compatible_with_office_types():
    """docx/xlsx 本来就是 zip 壳。不认这条会造成**大批**误拒——直接违反 <1%。"""
    for office in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/epub+zip",
    ):
        assert magic_conflicts(office, "application/zip") is False


def test_undetectable_content_is_not_treated_as_spoofing():
    """判不出 ≠ 欺骗。把未知一律判欺骗，所有新格式都会被误拒。"""
    assert magic_conflicts("application/x-custom", None) is False
    assert detect_magic(b"random bytes with no signature") is None


def test_mime_spoofing_lands_in_quarantine(tmp_path):
    path = _file(tmp_path, "看起来是图片.png", b"MZ\x90\x00" + b"\x00" * 100)
    verdict = scan(path=path, declared_name="看起来是图片.png", declared_media_type="image/png")
    assert verdict.state == STATE_QUARANTINED
    assert any("MIME 欺骗" in r for r in verdict.reasons)
    assert verdict.may_parse is False and verdict.attachment_only is True


# ─────────────── EICAR ───────────────

def test_eicar_is_detected(tmp_path):
    """行业约定的自检样本。命不中说明这条链根本没在扫。"""
    path = _file(tmp_path, "样本.txt", EICAR)
    verdict = scan(path=path, declared_name="样本.txt", declared_media_type="text/plain")
    assert verdict.state == STATE_QUARANTINED
    assert any("EICAR" in r for r in verdict.reasons)


# ─────────────── zip bomb 与压缩包结构（只读中央目录，不解压） ───────────────

def test_high_ratio_entry_is_flagged_without_extracting(tmp_path):
    """压缩炸弹的杀伤力全在解压。先解压再看大小，那时机器已经在挨打了。"""
    path = tmp_path / "bomb.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("big.txt", b"\0" * (MAX_ARCHIVE_RATIO * 5000))
    problems = inspect_archive(path)
    assert any("压缩炸弹形态" in p for p in problems), problems


def test_zip_slip_entry_path_is_flagged(tmp_path):
    path = tmp_path / "slip.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("../../etc/cron.d/evil", b"payload")
    assert any("条目路径穿越" in p for p in inspect_archive(path))


def test_absolute_entry_path_is_flagged(tmp_path):
    path = tmp_path / "abs.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("/etc/passwd", b"x")
    assert any("条目路径穿越" in p for p in inspect_archive(path))


def test_nested_archive_is_flagged(tmp_path):
    """嵌套解压是炸弹的常见放大手法。"""
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as nested:
        nested.writestr("a.txt", b"x")
    path = tmp_path / "outer.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("inner.zip", inner.getvalue())
    assert any("内嵌压缩包" in p for p in inspect_archive(path))


def test_malformed_archive_is_reported_not_crashed(tmp_path):
    path = _file(tmp_path, "坏.zip", b"PK\x03\x04" + b"garbage" * 20)
    problems = inspect_archive(path)
    assert problems, "畸形压缩包必须被判出来，不能静默通过"


def test_an_ordinary_zip_passes(tmp_path):
    """普通压缩包不能被误伤——它是最常见的合法上传之一。"""
    path = tmp_path / "正常.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("说明.txt", "这是一个正常的压缩包，内容不可压缩得离谱" * 5)
    assert inspect_archive(path) == []


# ─────────────── 状态机与解析隔离 ───────────────

def test_only_clean_may_be_parsed(tmp_path):
    """AC-UP-003「解析不在主进程执行」的前置：非 clean 一律不许进解析器。"""
    bad = scan(path=_file(tmp_path, "e.txt", EICAR),
               declared_name="e.txt", declared_media_type="text/plain")
    good = scan(path=_file(tmp_path, "好.png", PNG),
                declared_name="好.png", declared_media_type="image/png")
    assert bad.may_parse is False and good.may_parse is True


def test_scan_timeout_is_distinct_from_quarantined(tmp_path):
    """「没判完」和「判定为恶意」必须分得开——混在一起会把运维引向错误方向。"""
    missing = scan(path=tmp_path / "根本不存在", declared_name="x.png",
                   declared_media_type="image/png")
    assert missing.state == STATE_SCAN_TIMEOUT
    assert missing.may_parse is False, "判不了就不放行"


def test_rollback_downgrades_without_pretending_it_is_clean():
    """回滚的语义是「停止冒险」，不是「放弃检查」。"""
    verdict = rollback_verdict("预览处理器已停用")
    assert verdict.state == STATE_PENDING
    assert verdict.attachment_only is True and verdict.may_parse is False
    assert verdict.is_clean is False


# ─────────────── 合法夹具误拒率（阈值 < 1%，这里要求 0） ───────────────

def test_legitimate_fixtures_are_not_falsely_rejected(tmp_path):
    """反向阈值：把所有东西都判恶意，逃逸确实为 0，产品也确实不能用了。

    这一组是日常真会上传的东西，一个都不许被拦。
    """
    fixtures = [
        ("报表.png", PNG, "image/png"),
        ("照片.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 80, "image/jpeg"),
        ("合同.pdf", b"%PDF-1.7\n" + b"x" * 200, "application/pdf"),
        ("说明.txt", "普通中文文本，没有任何可疑内容。".encode(), "text/plain"),
        ("数据.csv", b"a,b,c\n1,2,3\n", "text/csv"),
        ("配置.json", b'{"ok": true}', "application/json"),
        ("未知格式.dat", b"\x01\x02\x03" * 50, "application/octet-stream"),
    ]
    rejected = []
    for name, payload, media in fixtures:
        verdict = scan(path=_file(tmp_path, name, payload),
                       declared_name=name, declared_media_type=media)
        if verdict.state != STATE_CLEAN:
            rejected.append((name, verdict.reasons))
    assert not rejected, f"合法夹具被误拒（阈值要求 <1%，实测应为 0）：{rejected}"


def test_a_real_office_document_shape_is_not_falsely_rejected(tmp_path):
    """xlsx 是 zip 壳。这一条单独列，因为它最容易被 magic 检查误伤。"""
    path = tmp_path / "台账.xlsx"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("xl/workbook.xml", "<workbook/>")
    verdict = scan(
        path=path, declared_name="台账.xlsx",
        declared_media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    assert verdict.state == STATE_CLEAN, verdict.reasons
