#!/usr/bin/env python3
"""Thin wrapper: delegate to KM_IDSystem/machine/tools/check_blocker_stop.py; do not copy Governance implementation."""
from pathlib import Path
import runpy
TARGET = Path(__file__).resolve().parents[3] / "machine" / "tools" / "check_blocker_stop.py"
if not TARGET.is_file():
    raise SystemExit(f"shared governance tool missing: {TARGET}")
runpy.run_path(str(TARGET), run_name="__main__")
