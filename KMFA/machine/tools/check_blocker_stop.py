#!/usr/bin/env python3
"""Delegate the shared blocker-review gate from the governance owner."""

from pathlib import Path
import runpy


TARGET = Path(__file__).resolve().parents[3] / "KM_IDSystem" / "machine" / "tools" / "check_blocker_stop.py"
runpy.run_path(str(TARGET), run_name="__main__")
