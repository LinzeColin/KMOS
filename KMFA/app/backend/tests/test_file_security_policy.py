"""S06/P6.2 bounded content-firewall corpus and false-rejection gate."""

from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

import pytest
from app.file_security_policy import inspect_file


def _inspect(
    root: Path,
    *,
    name: str,
    media_type: str,
    payload: bytes,
):
    target = root / "scanner-local.part"
    target.write_bytes(payload)
    return inspect_file(
        target,
        original_name=name,
        reported_media_type=media_type,
        expected_size=len(payload),
        expected_sha256=hashlib.sha256(payload).hexdigest(),
    )


def _zip(entries: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(
        output,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for name, payload in entries.items():
            archive.writestr(name, payload)
    return output.getvalue()


def _eicar() -> bytes:
    return (
        b"X5O!P%@AP[4"
        + bytes((92,))
        + b"PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    )


@pytest.mark.parametrize(
    ("name", "media_type", "payload", "expected_verdict", "expected_reason"),
    [
        (
            "../escape.txt",
            "text/plain",
            b"safe text",
            "rejected",
            "security_filename_invalid",
        ),
        (
            "invoice.exe.txt",
            "text/plain",
            b"not executable but deliberately misleading",
            "attachment_only",
            "security_dangerous_double_extension",
        ),
        (
            "photo.png",
            "image/png",
            b"MZ" + (b"\x00" * 64),
            "attachment_only",
            "security_active_content",
        ),
        (
            "payload.txt",
            "text/plain",
            _eicar(),
            "rejected",
            "security_malware_eicar",
        ),
        (
            "broken.png",
            "image/png",
            b"\x89PNG\r\n\x1a\nbroken",
            "rejected",
            "security_media_malformed",
        ),
        (
            "broken.zip",
            "application/zip",
            b"PK\x03\x04not-a-zip",
            "rejected",
            "security_archive_malformed",
        ),
        (
            "active.txt",
            "text/plain",
            b"<!doctype html><script>alert(1)</script>",
            "attachment_only",
            "security_active_content",
        ),
        (
            "unknown.bin",
            "application/octet-stream",
            b"\x00\x01\x02\x03\x04",
            "attachment_only",
            "security_unknown_format",
        ),
    ],
)
def test_attack_and_unknown_corpus_never_escapes_as_clean(
    tmp_path: Path,
    name: str,
    media_type: str,
    payload: bytes,
    expected_verdict: str,
    expected_reason: str,
):
    decision = _inspect(
        tmp_path,
        name=name,
        media_type=media_type,
        payload=payload,
    )
    assert decision.verdict == expected_verdict
    assert decision.reason_code == expected_reason
    assert decision.verdict != "clean"


def test_archive_traversal_macro_eicar_and_bomb_are_bounded(tmp_path: Path):
    fixtures = (
        (
            "traversal.zip",
            _zip({"../outside.txt": b"escape"}),
            "rejected",
            "security_archive_path_traversal",
        ),
        (
            "macro.docx",
            _zip(
                {
                    "[Content_Types].xml": b"<Types/>",
                    "word/vbaProject.bin": b"macro bytes",
                }
            ),
            "attachment_only",
            "security_office_macro",
        ),
        (
            "eicar.zip",
            _zip({"canary.txt": _eicar()}),
            "rejected",
            "security_malware_eicar",
        ),
        (
            "bomb.zip",
            _zip({"large.txt": b"A" * (2 * 1024 * 1024)}),
            "rejected",
            "security_archive_bomb",
        ),
    )
    for name, payload, verdict, reason in fixtures:
        decision = _inspect(
            tmp_path,
            name=name,
            media_type="application/zip",
            payload=payload,
        )
        assert decision.verdict == verdict
        assert decision.reason_code == reason
        assert decision.verdict != "clean"


def test_standard_legal_fixture_false_rejection_is_below_one_percent(
    tmp_path: Path,
):
    fixtures: list[tuple[str, str, bytes]] = []
    for index in range(25):
        fixtures.extend(
            (
                (
                    f"legal-{index}.txt",
                    "text/plain",
                    f"KMFA legal text fixture {index}\n".encode(),
                ),
                (
                    f"legal-{index}.csv",
                    "text/csv",
                    f"key,value\nfixture,{index}\n".encode(),
                ),
                (
                    f"legal-{index}.md",
                    "text/markdown",
                    f"# Legal fixture {index}\n\nNo active content.\n".encode(),
                ),
                (
                    f"legal-{index}.json",
                    "application/json",
                    f'{{"fixture":{index},"safe":true}}'.encode(),
                ),
            )
        )
    decisions = [
        _inspect(
            tmp_path,
            name=name,
            media_type=media_type,
            payload=payload,
        )
        for name, media_type, payload in fixtures
    ]
    rejected = [decision for decision in decisions if decision.verdict == "rejected"]
    assert len(fixtures) == 100
    assert len(rejected) == 0
    assert len(rejected) / len(fixtures) < 0.01
    assert all(decision.verdict == "clean" for decision in decisions)
