#!/usr/bin/env python3
"""Delegate the shared human-plane budget gate from the governance owner."""

from pathlib import Path
import runpy


TARGET = Path(__file__).resolve().parents[3] / "KM_IDSystem" / "machine" / "tools" / "check_doc_budget.py"
runpy.run_path(str(TARGET), run_name="__main__")
