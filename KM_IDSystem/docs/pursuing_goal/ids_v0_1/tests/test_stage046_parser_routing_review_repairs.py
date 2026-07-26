import copy
import importlib.util
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
PHASE2_CHECKER = PROJECT_ROOT / "scripts/check_parser_routing_runtime.py"
PHASE3_CHECKER = PROJECT_ROOT / "scripts/check_parser_routing_scenarios.py"
PHASE3_EVIDENCE = (
    PROJECT_ROOT
    / "docs/pursuing_goal/ids_v0_1/STAGE046_PHASE3_PARSER_ROUTING_SCENARIOS.md"
)


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage046ParserRoutingReviewRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.phase2 = _load(PHASE2_CHECKER, "stage046_review_phase2_repairs")
        cls.phase3 = _load(PHASE3_CHECKER, "stage046_review_phase3_repairs")

    def _request(self, **overrides):
        values = {
            "detection_request_id": "detection:sha256:" + "a" * 64,
            "source_fingerprint_ref": "fingerprint:sha256:" + "a" * 64,
            "source_identity_ref": "source:stage046:review:a",
            "detected_type": "PDF",
            "detection_state": "TYPE_CONFIRMED",
            "detection_confidence": "HIGH",
            "detection_evidence_ref": "evidence:stage045:stage046:review:a",
            "evidence_text_marker_applied": False,
            "requested_at": "2026-07-22T10:00:00Z",
        }
        values.update(overrides)
        return self.phase2.build_routing_request(**values)

    def test_detection_result_projection_has_distinct_verified_identity(self):
        pdf = self._request()
        docx = self._request(detected_type="DOCX")
        self.assertEqual(pdf["detection_request_id"], docx["detection_request_id"])
        self.assertRegex(
            pdf["detection_result_id"],
            r"^detection-result:sha256:[0-9a-f]{64}$",
        )
        self.assertNotEqual(pdf["detection_result_id"], docx["detection_result_id"])
        result = self.phase2.evaluate_parser_route(pdf)
        self.assertEqual(
            "PROJECTION_DIGEST_VERIFIED",
            result["detection_result_identity_status"],
        )

        tampered = copy.deepcopy(pdf)
        tampered["detected_type"] = "DOCX"
        body = {
            key: tampered[key]
            for key in self.phase2.REQUEST_FIELDS
            if key != "routing_request_id"
        }
        tampered["routing_request_id"] = (
            "routing:sha256:" + self.phase2._canonical_sha256(body)
        )
        blocked = self.phase2.evaluate_parser_route(tampered)
        self.assertEqual(["INVALID_ROUTING_REQUEST"], blocked["errors"])
        self.assertEqual(
            "UNVERIFIED",
            blocked["detection_result_identity_status"],
        )

    def test_invalid_request_returns_sanitized_non_echoing_result(self):
        untrusted = {
            "routing_request_id": "control:unverified",
            "detection_request_id": "control:unverified",
            "detected_type": {"untrusted": "value"},
            "detection_state": ["untrusted"],
            "detection_confidence": {"untrusted": "value"},
            "evidence_text_marker_applied": True,
        }
        result = self.phase2.evaluate_parser_route(untrusted)
        self.assertIsNone(result["routing_request_id"])
        self.assertIsNone(result["detection_request_id"])
        self.assertIsNone(result["detection_result_id"])
        self.assertEqual("UNKNOWN", result["detected_type"])
        self.assertEqual("TYPE_INPUT_BLOCKED", result["detection_state"])
        self.assertEqual("UNKNOWN", result["detection_confidence"])
        self.assertEqual("UNKNOWN", result["routing_confidence"])
        self.assertFalse(result["evidence_text_marker_preserved"])
        self.assertEqual("INVALID", result["route_fact_level"])
        self.assertEqual("UNVERIFIED", result["detection_result_identity_status"])
        self.assertEqual(["INVALID_ROUTING_REQUEST"], result["errors"])

    def test_path_like_or_noncanonical_references_are_rejected(self):
        cases = (
            {"source_identity_ref": "file:///private/raw/control.pdf"},
            {"source_identity_ref": "source:review//control"},
            {"source_identity_ref": "source:review/./control"},
            {
                "detection_evidence_ref": (
                    "evidence:stage045:file:///private/raw/control.pdf"
                )
            },
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    self._request(**overrides)

    def test_route_fact_level_matches_the_actual_disposition(self):
        cases = (
            ({}, "CANDIDATE"),
            (
                {
                    "detected_type": "TXT",
                    "detection_state": "TYPE_PROVISIONAL",
                    "detection_confidence": "MEDIUM",
                },
                "REVIEW_REQUIRED",
            ),
            (
                {
                    "detected_type": "UNSUPPORTED",
                    "detection_state": "TYPE_UNSUPPORTED",
                    "detection_confidence": "UNKNOWN",
                },
                "UNSUPPORTED",
            ),
            (
                {
                    "detected_type": "CORRUPT_OR_UNREADABLE",
                    "detection_state": "TYPE_INPUT_BLOCKED",
                    "detection_confidence": "UNKNOWN",
                },
                "BLOCKED",
            ),
        )
        for overrides, expected in cases:
            with self.subTest(expected=expected):
                result = self.phase2.evaluate_parser_route(
                    self._request(**overrides)
                )
                self.assertEqual(expected, result["route_fact_level"])

    def test_phase3_summary_fails_if_error_or_identity_invariant_drifts(self):
        result = self.phase2.evaluate_parser_route(self._request())
        result["errors"] = []
        summary = self.phase3._summarize(
            "pdf_high_candidate_parser_unavailable",
            result,
        )
        self.assertEqual("FAIL_CLOSED", summary["status"])

        result = self.phase2.evaluate_parser_route(self._request())
        result["detection_result_identity_status"] = "UNVERIFIED"
        summary = self.phase3._summarize(
            "pdf_high_candidate_parser_unavailable",
            result,
        )
        self.assertEqual("FAIL_CLOSED", summary["status"])

    def test_phase3_document_does_not_claim_phase4_performs_stage_review(self):
        text = PHASE3_EVIDENCE.read_text(encoding="utf-8")
        self.assertNotIn("完成全 Stage 独立复审并修复其暴露问题", text)
        self.assertIn("完成 Phase 4；整 Stage 独立复审仍须后续单独执行", text)


if __name__ == "__main__":
    unittest.main()
