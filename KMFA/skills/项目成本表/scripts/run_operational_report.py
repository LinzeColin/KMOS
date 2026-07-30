#!/usr/bin/env python3
"""Run the canonical KMFA project-cost operational adapter.

This is the only entry point used by production. Reference replay stays on the
separate ``run_reference_regression.py`` path and cannot feed this command.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(MODULE_ROOT / "src"))

from project_cost_table.operational import (  # noqa: E402
    ProjectCostError,
    calculate_and_generate,
    inventory_sources,
    pretty_json,
    self_test,
    verify_skill,
    verify_output,
)


def _roots(values: list[str]) -> tuple[Path, ...]:
    roots = tuple(Path(value).expanduser().resolve() for value in values)
    if not roots:
        raise ProjectCostError(
            "DATA_ROOT_MISSING",
            "at least one --data-root is required",
        )
    return roots


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="KMFA 项目成本正式源重算、运行态发布与输出封印验证"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory = subparsers.add_parser("inventory", help="只读盘点可识别来源")
    inventory.add_argument("--data-root", action="append", required=True)

    calculate = subparsers.add_parser("calculate", help="计算指定年度全部项目")
    calculate.add_argument("--data-root", action="append", required=True)
    calculate.add_argument("--year", type=int, required=True)
    calculate.add_argument("--as-of", required=True)
    calculate.add_argument("--output-dir", required=True)
    calculate.add_argument("--ocr-jsonl")
    calculate.add_argument("--payroll-workbook", action="append", default=[])
    calculate.add_argument("--attendance-root", action="append", default=[])
    calculate.add_argument(
        "--payroll-password-env",
        help="只传环境变量名；密码值不进入参数、日志或输出",
    )
    verify = subparsers.add_parser("verify-output", help="复核已封印输出目录")
    verify.add_argument("--output-dir", required=True)

    verify_package = subparsers.add_parser(
        "verify-skill",
        help="验证源码目录或下载 ZIP 的版本、结构、隐私与可编译性",
    )
    verify_package.add_argument("--skill-root", required=True)

    subparsers.add_parser("self-test", help="运行合成分级、去重与整数分测试")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "inventory":
            result = inventory_sources(_roots(args.data_root))
        elif args.command == "calculate":
            output_dir = Path(args.output_dir).expanduser().resolve()
            result = calculate_and_generate(
                _roots(args.data_root),
                year=args.year,
                as_of=args.as_of,
                output_dir=output_dir,
                ocr_jsonl=(
                    Path(args.ocr_jsonl).expanduser().resolve()
                    if args.ocr_jsonl
                    else None
                ),
                payroll_workbooks=tuple(
                    Path(value).expanduser().resolve()
                    for value in args.payroll_workbook
                ),
                attendance_roots=tuple(
                    Path(value).expanduser().resolve()
                    for value in args.attendance_root
                ),
                payroll_password_env=args.payroll_password_env,
            )
        elif args.command == "verify-output":
            result = verify_output(
                Path(args.output_dir).expanduser().resolve()
            )
        elif args.command == "verify-skill":
            result = verify_skill(
                Path(args.skill_root).expanduser().resolve()
            )
        elif args.command == "self-test":
            result = self_test()
        else:  # pragma: no cover - argparse prevents this path
            raise ProjectCostError("COMMAND_UNKNOWN", "unknown command")
    except ProjectCostError as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "error_code": exc.code,
                    "message": exc.message,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    except Exception as exc:  # noqa: BLE001 - surface typed unexpected failures
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "error_code": "UNEXPECTED_ERROR",
                    "message": "%s: %s" % (type(exc).__name__, exc),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 3
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return (
        0
        if result.get("status") in ("PASS", "PASS_WITH_OPEN_REVIEWS", None)
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
