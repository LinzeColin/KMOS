import importlib.util
import json
import struct
import unittest
import warnings
import zlib
from io import BytesIO
from pathlib import Path
from unittest import mock
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[4]
RUNTIME_CHECKER = ROOT / "scripts/check_file_type_detection_runtime.py"
RUNTIME_CONTRACT = (
    ROOT
    / "docs/pursuing_goal/ids_v0_1/file_type_detection"
    / "stage045_file_type_detection_runtime_contract.json"
)


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )


def _valid_png() -> bytes:
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    scanline = zlib.compress(b"\x00\x00\x00\x00")
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", scanline)
        + _png_chunk(b"IEND", b"")
    )


def _ooxml(*names: str) -> bytes:
    output = BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
            for name in names:
                archive.writestr(name, "<control />")
    return output.getvalue()


class Stage045FileTypeDetectionReviewRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = _load(RUNTIME_CHECKER, "stage045_review_runtime")

    def _request(
        self,
        *,
        filename: str = "control.pdf",
        mime: str = "application/pdf",
        requested_at: str = "2026-07-20T00:00:00Z",
    ):
        return self.runtime.build_detection_request(
            filename=filename,
            observed_mime=mime,
            mime_provenance_ref="evidence:stage045:review:mime",
            source_identity_ref="control:stage045:review",
            source_fingerprint_ref="fingerprint:sha256:" + "a" * 64,
            requested_at=requested_at,
        )

    def test_review_repairs_are_bound_into_the_phase2_contract(self):
        contract = json.loads(RUNTIME_CONTRACT.read_text(encoding="utf-8"))
        policy = contract["detector_policy"]
        self.assertEqual(
            self.runtime.FORMAT_VALIDATION_RULES,
            policy["format_validation_rules"],
        )
        self.assertTrue(
            policy["ooxml_container_rules"]["canonical_member_paths_required"]
        )
        self.assertFalse(
            policy["ooxml_container_rules"]["duplicate_member_names_allowed"]
        )
        request = contract["request_contract"]
        self.assertEqual("UNKNOWN", request["unknown_mime_canonical_value"])
        self.assertEqual(
            "RFC3339_UTC_REAL_CALENDAR_VALUE",
            request["requested_at_validation"],
        )
        self.assertTrue(
            contract["runtime_boundary"][
                "evidence_text_bounds_checked_before_signature"
            ]
        )

    def test_magic_only_or_truncated_payloads_never_confirm_a_type(self):
        cases = (
            ("truncated.pdf", "application/pdf", b"%PDF-1.7\n", "PDF_STRUCTURE_INVALID"),
            ("truncated.png", "image/png", b"\x89PNG\r\n\x1a\n", "PNG_STRUCTURE_INVALID"),
            ("truncated.jpg", "image/jpeg", b"\xff\xd8\xff\xe0", "JPEG_STRUCTURE_INVALID"),
            ("truncated.tif", "image/tiff", b"II*\x00", "TIFF_STRUCTURE_INVALID"),
        )
        for filename, mime, payload, error in cases:
            with self.subTest(filename=filename):
                result = self.runtime.detect_control_bytes(
                    self._request(filename=filename, mime=mime), payload
                )
                self.assertEqual("CORRUPT_OR_UNREADABLE", result["detected_type"])
                self.assertEqual("TYPE_INPUT_BLOCKED", result["detection_state"])
                self.assertEqual("ROUTE_BLOCKED", result["route_state"])
                self.assertIn(error, result["errors"])

    def test_structurally_bounded_controls_still_confirm_without_dispatch(self):
        cases = (
            ("control.pdf", "application/pdf", b"%PDF-1.7\ncontrol\n%%EOF", "PDF"),
            ("control.png", "image/png", _valid_png(), "PNG"),
            ("control.jpg", "image/jpeg", b"\xff\xd8\xff\xe0control\xff\xd9", "JPEG"),
            (
                "control.tif",
                "image/tiff",
                b"II*\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00",
                "TIFF",
            ),
        )
        for filename, mime, payload, expected in cases:
            with self.subTest(filename=filename):
                result = self.runtime.detect_control_bytes(
                    self._request(filename=filename, mime=mime), payload
                )
                self.assertEqual(expected, result["detected_type"])
                self.assertEqual("TYPE_CONFIRMED", result["detection_state"])
                self.assertEqual("HIGH", result["confidence"])
                self.assertFalse(result["parser_dispatch_performed"])

    def test_ooxml_rejects_noncanonical_and_duplicate_member_names(self):
        cases = (
            (
                _ooxml("[Content_Types].xml", "word/../evil.xml"),
                "OOXML_MEMBER_PATH_INVALID",
            ),
            (
                _ooxml(
                    "[Content_Types].xml",
                    "[Content_Types].xml",
                    "word/document.xml",
                ),
                "OOXML_DUPLICATE_MEMBER",
            ),
        )
        for payload, error in cases:
            with self.subTest(error=error):
                result = self.runtime.detect_control_bytes(
                    self._request(
                        filename="control.docx",
                        mime=(
                            "application/vnd.openxmlformats-officedocument."
                            "wordprocessingml.document"
                        ),
                    ),
                    payload,
                )
                self.assertEqual("TYPE_INPUT_BLOCKED", result["detection_state"])
                self.assertIn(error, result["errors"])

    def test_zip_magic_without_ooxml_markers_cannot_fall_back_to_mime_or_extension(self):
        payload = _ooxml("unrelated/control.txt")
        result = self.runtime.detect_control_bytes(
            self._request(
                filename="misleading.docx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                ),
            ),
            payload,
        )
        self.assertEqual("UNKNOWN", result["detected_type"])
        self.assertEqual("TYPE_UNKNOWN_REVIEW_REQUIRED", result["detection_state"])
        self.assertEqual("ROUTE_REVIEW_REQUIRED", result["route_state"])
        self.assertIn("OOXML_CONTAINER_MARKERS_MISSING", result["errors"])

    def test_unknown_mime_has_one_canonical_builder_representation(self):
        upper = self._request(filename="control.bin", mime="UNKNOWN")
        lower = self._request(filename="control.bin", mime="unknown")
        self.assertEqual("UNKNOWN", upper["mime_signal"]["value"])
        self.assertEqual(upper, lower)

    def test_requested_at_requires_a_real_utc_calendar_timestamp(self):
        for invalid in (
            "2026-13-20T00:00:00Z",
            "2026-02-30T00:00:00Z",
            "2026-07-20T24:00:00Z",
        ):
            with self.subTest(requested_at=invalid):
                with self.assertRaises(ValueError):
                    self._request(requested_at=invalid)

    def test_invalid_evidence_excerpt_is_blocked_before_signature_inspection(self):
        with mock.patch.object(
            self.runtime,
            "_inspect_signature",
            wraps=self.runtime._inspect_signature,
        ) as inspect_signature:
            result = self.runtime.detect_control_bytes(
                self._request(),
                b"%PDF-1.7\ncontrol\n%%EOF",
                source_text_excerpt="x" * (self.runtime.MAX_EVIDENCE_TEXT_CHARS + 1),
            )
        inspect_signature.assert_not_called()
        self.assertEqual("TYPE_INPUT_BLOCKED", result["detection_state"])
        self.assertIn("EVIDENCE_TEXT_LIMIT_EXCEEDED", result["errors"])
        self.assertFalse(result["file_signature_inspection_performed"])

if __name__ == "__main__":
    unittest.main()
