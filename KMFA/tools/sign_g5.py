#!/usr/bin/env python3
"""G5 签核执行器——只在 sign-g5 workflow_dispatch 里跑，Owner 亲手触发才有效。

签名的效力来自三层，缺一不可：
  1. GitHub 身份：workflow 层拦 `github.actor`，本器再拦一次 --actor（纵深防御）；
  2. 确认语：必须逐字输入「同意签核G5」——防误触，签名是个动作不是个默认值；
  3. 技术判据：现场重跑 check_g5_exit.py，不全绿不许签——签名不豁免技术判据。

三层都过才追加 g5_signoff 事件到审批台账（append-only），然后重跑检查器
让 g5_passed 由「识别签名」翻真，并把 roadmap DT6 标记完成。
本器幂等：已签核过则原样退出，不重复落痕。
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
import zoneinfo
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KMFA = ROOT / "KMFA"
LEDGER = KMFA / "metadata" / "approvals" / "control_events.jsonl"
CHECKLIST = KMFA / "stage_artifacts" / "DT6_PROD0018_g5" / "g5_checklist.json"
ROADMAP = KMFA / "docs" / "governance" / "roadmap.yaml"
APPROVER = "LinzeColin"
CONFIRM_PHRASE = "同意签核G5"


def _run_checker() -> dict:
    r = subprocess.run([sys.executable, str(KMFA / "tools" / "check_g5_exit.py")],
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        print(f"FAIL: 检查器输出不是 JSON（rc={r.returncode}）：{r.stdout[:200]} {r.stderr[:200]}")
        raise SystemExit(2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--actor", required=True)
    ap.add_argument("--confirm", required=True)
    ap.add_argument("--site-verified", required=True, choices=["是", "否"])
    ap.add_argument("--run-url", required=True)
    args = ap.parse_args()

    if args.actor != APPROVER:
        print(f"FAIL: 签核人必须是 {APPROVER}，当前 actor={args.actor}——不代签，不例外。")
        return 3
    if args.confirm != CONFIRM_PHRASE:
        print(f"FAIL: 确认语必须逐字为「{CONFIRM_PHRASE}」。签名是个动作，不是个默认值。")
        return 4

    before = _run_checker()
    if before.get("g5_passed"):
        print("已签核过（台账里已有 g5_signoff 事件），本次不重复落痕。")
        return 0
    if not before.get("technical_checks_all_green"):
        print("FAIL: 技术判据当前不全绿，不许签——签名不豁免技术判据。逐项见检查器输出。")
        return 5

    now = datetime.datetime.now(zoneinfo.ZoneInfo("Asia/Shanghai"))
    event = {
        "record_type": "control_event",
        "schema_version": "kmfa.control_event.v1",
        "event_id": f"CTRL-KMFA-{now:%Y%m%d}-G5-SIGNOFF",
        "event_time": now.isoformat(timespec="seconds"),
        "event_type": "g5_signoff",
        "stage_phase": "DT6",
        "task_id": "TSK.KMFA.PROD.0018",
        "approver": args.actor,
        "approval_channel": "github-actions workflow_dispatch",
        "workflow_run_url": args.run_url,
        "confirm_phrase": args.confirm,
        "site_content_verified_by_owner": args.site_verified,
        "evidence_ref": "KMFA/stage_artifacts/DT6_PROD0018_g5/g5_checklist.json",
        "append_only": True,
        "raw_layer_write_allowed": False,
        "forbidden_plaintext": False,
    }
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

    after = _run_checker()
    if not after.get("g5_passed"):
        print("FAIL: 事件已追加但检查器仍不认——识别逻辑与落痕字段不一致，人工排查。")
        return 6
    CHECKLIST.write_text(json.dumps(after, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    s = ROADMAP.read_text(encoding="utf-8")
    anchor = '    status: "in_progress_20260720_M5十八项全部已建(18/18)'
    if anchor in s:
        补 = (f"G5已签核{now:%Y%m%d}：Owner 经 sign-g5 workflow_dispatch 亲签"
              f"（事件 {event['event_id']}，网站内容亲验={args.site_verified}），"
              f"g5_passed 已由检查器识别签名翻真——DT6 完成。原状态留档：")
        s = s.replace(anchor, f'    status: "completed_{now:%Y%m%d}_{补}in_progress_20260720_M5十八项全部已建(18/18)', 1)
        ROADMAP.write_text(s, encoding="utf-8")
        roadmap_note = "roadmap DT6 已标记完成（原状态全文留档）"
    else:
        roadmap_note = "roadmap 锚点未命中，DT6 状态未改——签核本身已生效，人工补记即可"

    print(json.dumps({
        "签核完成": True,
        "事件号": event["event_id"],
        "g5_passed": after["g5_passed"],
        "网站内容亲验": args.site_verified,
        "roadmap": roadmap_note,
    }, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
