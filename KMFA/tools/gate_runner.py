#!/usr/bin/env python3
"""声明式门禁引擎（TSK.KMFA.GOVX.0001/0002 试点）。

一个门 = 一份 YAML（metadata/quality/gates/*.yaml）：只读 SQL 跑在私有 staging 上，
expect 断言列值。runner 逐门执行 → PASS/FAIL + 证据 JSON（公开面仅聚合值）。
新增门禁一律走本引擎（对标 dbt generic tests），不再手写校验脚本。
用法：python3 KMFA/tools/gate_runner.py [--gates-dir KMFA/metadata/quality/gates]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB_PATH = REPO / "KMFA" / ".codex_private_runtime" / "duckdb" / "kmfa_staging.duckdb"


def ensure_views(con) -> None:
    con.execute("""CREATE OR REPLACE VIEW _staging.v_collection_authoritative AS
        SELECT * FROM (SELECT *, row_number() OVER (
            PARTITION BY collection_date, customer_ref, contract_ref, collection_amount_cents,
                         coalesce(receipt_method,''), coalesce(row_seq,'')
            ORDER BY source_sha8, sheet_hash, row_index) rn FROM _staging.collection) WHERE rn=1
        AND source_sha8 IN ('d45324b4','5e5f46b6')""")


def run_gate(con, spec: dict) -> dict:
    row = con.execute(spec["source_sql"]).fetchone()
    cols = [d[0] for d in con.description]
    values = dict(zip(cols, row))
    exp = spec["expect"]
    checks = [(exp["列"], exp["等于"])]
    if "且列" in exp:
        checks.append((exp["且列"], exp["且等于"]))
    ok = all(values.get(col) == want for col, want in checks)
    return {"gate_id": spec["gate_id"], "名称": spec.get("名称"), "assertion_ref": spec.get("assertion_ref"),
            "values": values, "result": "PASS" if ok else "FAIL"}


def main() -> int:
    import duckdb, yaml
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gates-dir", default="KMFA/metadata/quality/gates")
    args = parser.parse_args()
    gates_dir = REPO / args.gates_dir
    con = duckdb.connect(str(DB_PATH), read_only=False)
    ensure_views(con)
    results = [run_gate(con, yaml.safe_load(p.read_text(encoding="utf-8")))
               for p in sorted(gates_dir.glob("*.yaml"))]
    con.close()
    summary = {"task_id": "TSK.KMFA.GOVX.0002", "gates": len(results),
               "pass": sum(r["result"] == "PASS" for r in results),
               "fail": sum(r["result"] == "FAIL" for r in results), "results": results}
    out = REPO / "KMFA/stage_artifacts/DT8_GOVX0002_gate_runner/machine/gate_run.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, default=str))
    return 0 if summary["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
