import copy
import importlib.util
import json
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[4]
BASE = PROJECT_ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = (
    BASE / "parser_output" / "stage047_parser_output_contract.json"
)
PHASE2_CONTRACT = (
    BASE / "parser_output" / "stage047_parser_output_runtime_contract.json"
)
PHASE1_CHECKER = PROJECT_ROOT / "scripts" / "check_parser_output.py"
PHASE2_CHECKER = PROJECT_ROOT / "scripts" / "check_parser_output_runtime.py"

INPUT_FIELDS = [
    "route_result_id",
    "route_result",
    "routing_request",
    "source_identity_ref",
    "requested_output_schema_version",
    "requested_at",
]
ROUTING_REQUEST_FIELDS = [
    "schema_version",
    "routing_request_id",
    "detection_request_id",
    "detection_result_id",
    "source_fingerprint_ref",
    "source_identity_ref",
    "detected_type",
    "detection_state",
    "detection_confidence",
    "detection_evidence_ref",
    "detector_contract_version",
    "parser_registry_version",
    "evidence_text_marker_applied",
    "requested_at",
]
ROUTE_HUMAN_STATUS = "控制路线夹具已绑定，未选择或执行解析器"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage047ParserOutputReviewRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.phase1 = _load(PHASE1_CHECKER, "stage047_review_phase1_repairs")
        cls.phase2 = _load(PHASE2_CHECKER, "stage047_review_phase2_repairs")
        cls.phase1_contract = json.loads(
            PHASE1_CONTRACT.read_text(encoding="utf-8")
        )
        cls.phase2_contract = json.loads(
            PHASE2_CONTRACT.read_text(encoding="utf-8")
        )

    def _wrapper(self, *, requested_at="2026-07-24T01:00:00Z"):
        return self.phase2.build_control_input(
            suffix="a",
            requested_at=requested_at,
        )

    def _payload_with_linked_table(self):
        return {
            "text": "Bounded review fixture.",
            "tables": [
                {
                    "table_id": "table:control:1",
                    "page_refs": ["page:control:1"],
                    "section_ref": "section:control:1",
                    "cells": [["A"]],
                    "confidence": "HIGH",
                    "errors": [],
                }
            ],
            "pages": [
                {
                    "page_id": "page:control:1",
                    "page_number": 1,
                    "text": "Bounded review fixture.",
                    "table_refs": ["table:control:1"],
                    "confidence": "HIGH",
                    "errors": [],
                }
            ],
            "sections": [
                {
                    "section_id": "section:control:1",
                    "title": "Review",
                    "level": 1,
                    "page_refs": ["page:control:1"],
                    "text": "Bounded review fixture.",
                    "table_refs": ["table:control:1"],
                    "confidence": "HIGH",
                    "errors": [],
                }
            ],
            "confidence": "HIGH",
            "errors": [],
        }

    def test_phase1_contract_requires_complete_request_result_lineage(self):
        incoming = self.phase1_contract["input_boundary"]
        self.assertEqual(INPUT_FIELDS, incoming["required_wrapper_fields"])
        self.assertEqual(
            "ids.stage046.parser_routing_request.v1",
            incoming["required_routing_request_schema_version"],
        )
        self.assertEqual(
            ROUTING_REQUEST_FIELDS,
            incoming["required_routing_request_fields"],
        )
        self.assertTrue(incoming["routing_request_identity_required"])
        self.assertEqual(
            "SHA256_CANONICAL_JSON",
            incoming["routing_request_identity_algorithm"],
        )
        self.assertTrue(incoming["request_result_lineage_match_required"])
        self.assertEqual(
            INPUT_FIELDS,
            self.phase2_contract["input_contract"][
                "phase1_required_field_names"
            ],
        )

    def test_unencodable_unicode_is_structurally_rejected_without_exception(self):
        payload = self._payload_with_linked_table()
        payload["text"] = "\ud800"
        result = self.phase2.normalize_parser_payload(
            self._wrapper(),
            payload,
            produced_at="2026-07-24T01:00:01Z",
        )
        self.assertFalse(result["accepted"])
        self.assertEqual("OUTPUT_REJECTED_FAIL_CLOSED", result["result_code"])
        self.assertIsNone(result["output"])
        self.assertTrue(
            self.phase2_contract["payload_contract"][
                "valid_utf8_encodable_text_required"
            ]
        )

    def test_control_references_are_canonical_lower_ascii_segments(self):
        for value in (
            "source:control:bad\nref",
            "source:control:é",
            "source:control:.hidden",
            "source:control:Upper",
        ):
            with self.subTest(value=ascii(value)):
                self.assertFalse(
                    self.phase2._canonical_control_ref(
                        value,
                        prefix="source:control:",
                    )
                )
        self.assertTrue(
            self.phase2._canonical_control_ref(
                "source:control:review-1",
                prefix="source:control:",
            )
        )
        self.assertEqual(
            "LOWER_ASCII_TOKEN_SEGMENTS",
            self.phase2_contract["input_contract"][
                "canonical_control_reference_format"
            ],
        )

    def test_table_page_and_section_references_must_be_reciprocal(self):
        wrapper = self._wrapper()
        cases = []

        missing_page_backref = self._payload_with_linked_table()
        missing_page_backref["pages"][0]["table_refs"] = []
        cases.append(missing_page_backref)

        missing_section_backref = self._payload_with_linked_table()
        missing_section_backref["sections"][0]["table_refs"] = []
        cases.append(missing_section_backref)

        for payload in cases:
            with self.subTest(payload=payload):
                result = self.phase2.normalize_parser_payload(
                    wrapper,
                    payload,
                    produced_at="2026-07-24T01:00:01Z",
                )
                self.assertFalse(result["accepted"])
                self.assertEqual(
                    "OUTPUT_REJECTED_FAIL_CLOSED",
                    result["result_code"],
                )

        payload_contract = self.phase2_contract["payload_contract"]
        self.assertTrue(
            payload_contract["reciprocal_table_page_references_required"]
        )
        self.assertTrue(
            payload_contract["reciprocal_table_section_references_required"]
        )

    def test_route_status_and_safe_errors_are_exact_and_bounded(self):
        wrapper = self._wrapper()
        wrapper["route_result"]["human_status"] = "unexpected"
        wrapper["route_result_id"] = self.phase2.route_result_id(
            wrapper["route_result"]
        )
        self.assertFalse(self.phase2.validate_input_wrapper(wrapper))

        for field, value in (
            ("code", "PARSER_" + "A" * 90),
            ("message_key", "parser." + "a" * 122),
        ):
            payload = self._payload_with_linked_table()
            safe_error = {
                "code": "PARSER_REVIEW_WARNING",
                "severity": "WARNING",
                "retryable": False,
                "message_key": "parser.review_warning",
            }
            safe_error[field] = value
            payload["errors"] = [safe_error]
            with self.subTest(field=field):
                result = self.phase2.normalize_parser_payload(
                    self._wrapper(),
                    payload,
                    produced_at="2026-07-24T01:00:01Z",
                )
                self.assertFalse(result["accepted"])

        incoming = self.phase2_contract["input_contract"]
        payload_contract = self.phase2_contract["payload_contract"]
        self.assertEqual(
            ROUTE_HUMAN_STATUS,
            incoming["route_result_human_status_exact"],
        )
        self.assertEqual(
            96,
            payload_contract["safe_error_code_max_characters"],
        )
        self.assertEqual(
            128,
            payload_contract["safe_error_message_key_max_characters"],
        )

    def test_produced_at_cannot_precede_requested_at(self):
        wrapper = self._wrapper(requested_at="2026-07-24T01:00:00Z")
        result = self.phase2.normalize_parser_payload(
            wrapper,
            self._payload_with_linked_table(),
            produced_at="2026-07-24T00:59:59Z",
        )
        self.assertFalse(result["accepted"])
        self.assertEqual("OUTPUT_REJECTED_FAIL_CLOSED", result["result_code"])

        accepted = self.phase2.normalize_parser_payload(
            wrapper,
            self._payload_with_linked_table(),
            produced_at="2026-07-24T01:00:01Z",
        )["output"]
        tampered = copy.deepcopy(accepted)
        tampered["produced_at"] = "2026-07-24T00:59:59Z"
        tampered["output_id"] = self.phase2.output_id(tampered)
        self.assertFalse(
            self.phase2.validate_output_envelope(tampered, wrapper)
        )
        self.assertTrue(
            self.phase2_contract["output_contract"][
                "produced_at_not_before_requested_at"
            ]
        )


if __name__ == "__main__":
    unittest.main()
