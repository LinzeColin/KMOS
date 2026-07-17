#!/usr/bin/env python3
"""Regression tests for DWS output file layout."""

from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import archive_dingtalk_all_files as archive  # noqa: E402
import validate_dws_output_structure as validate_output  # noqa: E402


class DwsOutputLayoutTests(unittest.TestCase):
    def test_archive_paths_use_month_directory_not_mmdd(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            downloaded = Path(tmpdir) / "原始文件.pdf"
            downloaded.write_bytes(b"%PDF\n")
            archive_rel, output_path = archive.archive_names(
                {
                    "group_slug": "demo-group",
                    "message_time": "2026-07-07 10:11:12",
                    "original_filename": "原始文件.pdf",
                    "sender_name": "张三",
                    "open_message_id": "message-1",
                },
                downloaded,
            )

        self.assertEqual(archive_rel.parts[:5], ("data", "archive", "demo-group", "files", "07"))
        self.assertEqual(output_path.split("/")[:2], ["files", "07"])
        self.assertNotIn("0707", archive_rel.parts)
        self.assertNotIn("/0707/", output_path)

    def test_cold_storage_uses_group_files_month_file_layout(self) -> None:
        inner_path = archive.cold_storage_inner_path(
            "生产管理群",
            "data/archive/demo-group/files/07/20260707101112_张三_abcd_原始文件.pdf",
            "2026-07-07 10:11:12",
        )

        self.assertEqual(inner_path, "生产管理群/files/07/20260707101112_张三_abcd_原始文件.pdf")

    def test_cold_validator_accepts_files_month_and_rejects_files_mmdd(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cold_root = Path(tmpdir) / "DWS_Archive"
            good_file = cold_root / "生产管理群" / "files" / "07" / "原始文件.pdf"
            good_file.parent.mkdir(parents=True)
            good_file.write_bytes(b"ok")

            self.assertEqual(validate_output.validate_cold_root(cold_root)["errors"], [])

            bad_file = cold_root / "付款请示群" / "files" / "0707" / "原始文件.pdf"
            bad_file.parent.mkdir(parents=True)
            bad_file.write_bytes(b"bad")

            self.assertTrue(
                any(
                    error.startswith("cold_file_not_under_files_mm:")
                    for error in validate_output.validate_cold_root(cold_root)["errors"]
                )
            )

    def test_mirror_validator_accepts_files_month_and_rejects_files_mmdd(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mirror = Path(tmpdir) / "DWS_Outputs.zip"
            group = "生产管理群"
            prefix = f"DWS_Outputs/{group}/"
            with zipfile.ZipFile(mirror, "w") as zf:
                for rel in validate_output.REQUIRED_EVIDENCE:
                    if rel == "_manifest/manifest.csv":
                        zf.writestr(
                            f"{prefix}{rel}",
                            "status,message_time\n"
                            "downloaded,2026-07-07 10:11:12\n",
                        )
                    else:
                        zf.writestr(f"{prefix}{rel}", "")
                zf.writestr(f"{prefix}files/07/原始文件.pdf", b"ok")

            self.assertEqual(validate_output.validate_group_in_mirror(mirror, group)["errors"], [])

            bad_mirror = Path(tmpdir) / "DWS_Outputs_bad.zip"
            with zipfile.ZipFile(bad_mirror, "w") as zf:
                for rel in validate_output.REQUIRED_EVIDENCE:
                    if rel == "_manifest/manifest.csv":
                        zf.writestr(
                            f"{prefix}{rel}",
                            "status,message_time\n"
                            "downloaded,2026-07-07 10:11:12\n",
                        )
                    else:
                        zf.writestr(f"{prefix}{rel}", "")
                zf.writestr(f"{prefix}files/0707/原始文件.pdf", b"bad")

            self.assertTrue(
                any(
                    error.startswith("mmdd_file_path_forbidden:")
                    for error in validate_output.validate_group_in_mirror(bad_mirror, group)["errors"]
                )
            )


if __name__ == "__main__":
    unittest.main()
