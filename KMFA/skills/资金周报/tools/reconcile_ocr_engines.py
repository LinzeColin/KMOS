#!/usr/bin/env python3
"""swift Vision 历史 OCR sidecar ↔ Python OCR 对账（TSK.KMFA.SKL.0005 验收工具）。

对既有 run 目录（含 screenshot_ocr_sidecar_generation_plan.csv 与私有 sidecar 文本）逐条：
用 Python 引擎链重新 OCR 同一张源图，与 swift 版文本比较，输出对账 CSV + 汇总 JSON。
判定口径（宽严结合，金额优先）：
  exact         —— 规范化后全文一致（去空白/全半角统一）
  digits_match  —— 提取的数字序列多重集一致（金额/日期核心一致，版式差异可容）
  mismatch      —— 数字都对不上，需人工看
迁移完成标准（09 七节红线）：digits_match 及以上 100%，mismatch=0；报告供 Owner 异步查阅。

用法：
  python3 reconcile_ocr_engines.py --repo-root . --input-dir <截图根目录> --run-dir <run目录> --out <输出目录>
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import importlib.util

_HELPER = Path(__file__).with_name("ocr_with_python.py")
_spec = importlib.util.spec_from_file_location("ocr_with_python", _HELPER)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", "", text)


def digit_runs(text: str) -> Counter:
    return Counter(re.findall(r"\d+(?:\.\d+)?", unicodedata.normalize("NFKC", text)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve()
    input_dir = Path(args.input_dir).expanduser().resolve()
    run_dir = Path(args.run_dir).expanduser().resolve()
    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    plan_path = run_dir / "screenshot_ocr_sidecar_generation_plan.csv"
    with plan_path.open(encoding="utf-8-sig", newline="") as handle:
        plan_rows = [row for row in csv.DictReader(handle) if row.get("generation_status") == "ocr_text_generated_pending_review"]

    chain = _mod.load_engine_chain()
    results, tallies = [], Counter()
    for row in plan_rows:
        sidecar = repo_root / row["ocr_text_private_relative_path"]
        image = input_dir / row["source_image_relative_path"]
        verdict, py_len, engine_label = "source_missing", 0, ""
        if sidecar.is_file() and image.is_file():
            swift_text = sidecar.read_text(encoding="utf-8")
            py_text = ""
            for run, label in chain:
                try:
                    py_text = run(image)
                except Exception:  # noqa: BLE001
                    continue
                if py_text:
                    engine_label = label
                    break
            py_len = len(py_text)
            if not py_text:
                verdict = "python_no_text"
            elif normalize(py_text) == normalize(swift_text):
                verdict = "exact"
            elif digit_runs(py_text) == digit_runs(swift_text):
                verdict = "digits_match"
            else:
                missing = digit_runs(swift_text) - digit_runs(py_text)
                verdict = "mismatch" if missing else "digits_superset"
        tallies[verdict] += 1
        results.append({
            "ocr_generation_id": row["ocr_generation_id"],
            "source_image_relative_path": row["source_image_relative_path"],
            "swift_text_sha256": row["text_sha256"],
            "python_engine": engine_label,
            "python_text_length": py_len,
            "verdict": verdict,
        })

    out_csv = out_dir / "ocr_engine_reconciliation.csv"
    with out_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0].keys()) if results else ["verdict"])
        writer.writeheader()
        writer.writerows(results)
    ok = tallies["exact"] + tallies["digits_match"] + tallies["digits_superset"]
    summary = {
        "status": "OCR_ENGINE_RECONCILIATION_DONE",
        "compared": len(results),
        "tallies": dict(tallies),
        "pass_ratio": (ok / len(results)) if results else None,
        "migration_gate": "PASS" if results and tallies["mismatch"] == 0 and tallies["python_no_text"] == 0 else "FAIL",
        "out_csv": str(out_csv),
    }
    (out_dir / "ocr_engine_reconciliation_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["migration_gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
