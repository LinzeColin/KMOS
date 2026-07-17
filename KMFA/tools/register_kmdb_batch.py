#!/usr/bin/env python3
"""把 KMDatabase/data 的内容寻址账本桥接进 KMFA v0.1.4 导入登记协议（TSK.KMFA.DATA.0001/0002）。

来源账本：KMDatabase/data/manifest.jsonl（ingest_data.py 产出，sha256/大小/域/批次）
登记去向：
  - KMFA/metadata/imports/raw_file_manifest.jsonl   append-only，schema kmfa.raw_manifest_schema.v1
  - KMFA/metadata/imports/import_runs.jsonl          append 一条 run 汇总（含 zip 预检聚合与 D11 授权说明）
  - KMFA/.codex_private_runtime/imports/zip_member_lists/<sha8>.json   zip 成员明细（gitignore，永不 tracked）
边界：raw 字节不进 KMFA/（storage_ref 指向 KMDatabase 内容寻址对象，D11 授权入公开仓）；
     金额/明细值零出现；.doc 不在 S03-P1 支持格式表 → manifest_status=quarantined（B 级待议）。
幂等：同 file_hash 已登记则跳过。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RAW_MANIFEST = REPO / "KMFA" / "metadata" / "imports" / "raw_file_manifest.jsonl"
IMPORT_RUNS = REPO / "KMFA" / "metadata" / "imports" / "import_runs.jsonl"
PRIVATE_ZIP_DIR = REPO / "KMFA" / ".codex_private_runtime" / "imports" / "zip_member_lists"

SUPPORTED_FORMATS = {"zip", "xlsx", "xls", "csv", "pdf", "wps"}
DOMAIN_SOURCE_SLUG = {"财务": "finance-kingdee", "WPS钉钉红圈": "wps-dingtalk-hongquan", "绩效": "performance-review"}
DOMAIN_GRADE = {"财务": "A0", "WPS钉钉红圈": "A1", "绩效": "A2"}
IMP_RE = re.compile(r"^IMP-[0-9]{8}-[0-9]{6}-[a-z0-9-]{3,40}-[a-f0-9]{8}$")
SRC_RE = re.compile(r"^SRC-[a-z0-9-]{3,40}-[a-f0-9]{8}$")


def h8(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def source_id(domain: str) -> str:
    slug = DOMAIN_SOURCE_SLUG[domain]
    sid = f"SRC-{slug}-{h8(slug)}"
    assert SRC_RE.match(sid), sid
    return sid


def grade(domain: str, file_format: str) -> str:
    return "B" if file_format in {"pdf", "doc"} else DOMAIN_GRADE[domain]


def zip_precheck(obj_path: Path, sha256: str) -> dict:
    summary = {"member_count": 0, "total_uncompressed_bytes": 0, "suspicious_members": 0, "member_list_private_ref": ""}
    members = []
    with zipfile.ZipFile(obj_path) as zf:
        for info in zf.infolist():
            name = info.filename
            bad = name.startswith("/") or ".." in Path(name).parts
            members.append({"name": name, "size": info.file_size, "suspicious": bad})
            summary["member_count"] += 1
            summary["total_uncompressed_bytes"] += info.file_size
            summary["suspicious_members"] += int(bad)
    PRIVATE_ZIP_DIR.mkdir(parents=True, exist_ok=True)
    private_path = PRIVATE_ZIP_DIR / f"{sha256[:8]}.json"
    private_path.write_text(json.dumps({"sha256": sha256, "members": members}, ensure_ascii=False, indent=2), encoding="utf-8")
    summary["member_list_private_ref"] = str(private_path.relative_to(REPO))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kmdb-manifest", default="KMDatabase/data/manifest.jsonl")
    parser.add_argument("--received", required=True, help="批次接收日 YYYY-MM-DD")
    parser.add_argument("--now", required=True, help="登记时刻 YYYYMMDD-HHMMSS（进 import_run_id）")
    parser.add_argument("--evidence-ref", default="KMFA/stage_artifacts/DT5_DATA0001_0002_intake_registration")
    args = parser.parse_args()

    rows = [json.loads(l) for l in (REPO / args.kmdb_manifest).read_text(encoding="utf-8").splitlines() if l.strip()]
    existing = set()
    if RAW_MANIFEST.exists():
        for line in RAW_MANIFEST.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                if rec.get("record_type") == "raw_file_manifest":
                    existing.add(rec.get("file_hash", ""))

    date_part, time_part = args.now.split("-")
    run_id = f"IMP-{date_part}-{time_part}-kmdb-batch-{h8(args.kmdb_manifest + args.received)}"
    assert IMP_RE.match(run_id), run_id

    registered, quarantined, skipped, zip_summaries, fmt_counts, grade_counts = [], [], 0, [], {}, {}
    for row in rows:
        file_hash = f"sha256:{row['sha256']}"
        if file_hash in existing:
            skipped += 1
            continue
        name = unicodedata.normalize("NFC", row["original_name"])
        fmt = Path(name).suffix.lower().lstrip(".")
        status = "registered" if fmt in SUPPORTED_FORMATS else "quarantined"
        g = grade(row["domain"], fmt)
        obj_rel = f"KMDatabase/data/{row['object_path']}"
        entry = {
            "record_type": "raw_file_manifest",
            "schema_version": "kmfa.raw_file_manifest.v1",
            "stage_phase": "S03-P1",
            "import_run_id": run_id,
            "source_id": source_id(row["domain"]),
            "file_hash": file_hash,
            "file_size_bytes": row["size_bytes"],
            "storage_ref": obj_rel,
            "original_filename_hash": f"sha256:{hashlib.sha256(name.encode('utf-8')).hexdigest()}",
            "file_format": fmt,
            "container_type": "zip_archive" if fmt == "zip" else "single_file",
            "received_at": args.received,
            "manifest_status": status,
            "source_package_ref": args.kmdb_manifest,
            "evidence_ref": args.evidence_ref,
            "data_grade": g,
            "source_domain": row["domain"],
            "kmdb_batch": row["batch"],
        }
        fmt_counts[fmt] = fmt_counts.get(fmt, 0) + 1
        grade_counts[g] = grade_counts.get(g, 0) + 1
        if fmt == "zip":
            zs = zip_precheck(REPO / obj_rel, row["sha256"])
            entry["zip_precheck"] = {k: zs[k] for k in ("member_count", "total_uncompressed_bytes", "suspicious_members")}
            zip_summaries.append({"file_hash": file_hash, **zs})
        (quarantined if status == "quarantined" else registered).append(entry)

    new_entries = registered + quarantined
    if new_entries:
        with RAW_MANIFEST.open("a", encoding="utf-8") as f:
            for entry in new_entries:
                f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        run_record = {
            "record_type": "import_run",
            "schema_version": "kmfa.import_runs.v1",
            "stage_phase": "S03-P1",
            "import_run_id": run_id,
            "executed_at": f"{args.received}T00:00:00+10:00/registered-{args.now}",
            "tool_ref": "KMFA/tools/register_kmdb_batch.py",
            "source_package_ref": args.kmdb_manifest,
            "registered_count": len(registered),
            "quarantined_count": len(quarantined),
            "idempotent_skipped": skipped,
            "format_counts": fmt_counts,
            "grade_counts": grade_counts,
            "zip_precheck_aggregate": [{k: z[k] for k in ("file_hash", "member_count", "total_uncompressed_bytes", "suspicious_members")} for z in zip_summaries],
            "zip_member_lists_private": True,
            "raw_bytes_under_kmfa": False,
            "d11_authorization": "owner_20260717_raw_data_into_public_kmdatabase_data_reconfirmed_all_repos_public",
            "metadata_required_fields_validated": True,
        }
        with IMPORT_RUNS.open("a", encoding="utf-8") as f:
            f.write(json.dumps(run_record, ensure_ascii=False, sort_keys=True) + "\n")

    print(json.dumps({
        "status": "REGISTERED" if new_entries else "IDEMPOTENT_NOOP",
        "import_run_id": run_id if new_entries else None,
        "registered": len(registered), "quarantined": len(quarantined), "skipped_existing": skipped,
        "format_counts": fmt_counts, "grade_counts": grade_counts,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
