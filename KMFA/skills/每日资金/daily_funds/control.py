"""Versioned custom-threshold control hand-off between private app and worker."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping

from .contracts import ContractError, DailyBalance, FloatingLine, custom_date_line, validate_custom_numeric
from .state import atomic_json_write, iso_now


class ControlError(ContractError):
    pass


class ThresholdControl:
    def __init__(self, control_dir: str | Path):
        self.root = Path(control_dir)
        self.request_path = self.root / "threshold_request.json"
        self.active_path = self.root / "active_threshold.json"
        self.audit_path = self.root / "threshold_audit.jsonl"

    @staticmethod
    def _read(path: Path) -> dict[str, Any] | None:
        if not path.is_file():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def active(self) -> dict[str, Any] | None:
        return self._read(self.active_path)

    def apply_pending(self) -> dict[str, Any] | None:
        request = self._read(self.request_path)
        if request is None:
            return self.active()
        mode = str(request.get("mode") or "")
        if mode not in {"disabled", "date_range", "numeric"}:
            raise ControlError("THRESHOLD_REQUEST_INVALID")
        revision = str(request.get("revision") or "")
        if len(revision) != 64:
            raise ControlError("THRESHOLD_REQUEST_INVALID")
        active: dict[str, Any] = {
            "schema_version": "kmfa.daily_funds.threshold_control.v1",
            "mode": mode,
            "revision": revision,
            "applied_at": iso_now(),
            "actor": str(request.get("actor") or "kmfa_private_owner_ui")[:120],
            "reason": str(request.get("reason") or "")[:500],
        }
        if mode == "numeric":
            active["amount_fen"] = validate_custom_numeric(request.get("amount_fen"))
        elif mode == "date_range":
            try:
                start = date.fromisoformat(str(request.get("from") or ""))
                end = date.fromisoformat(str(request.get("to") or ""))
            except ValueError as exc:
                raise ControlError("THRESHOLD_REQUEST_INVALID") from exc
            if end < start or (end - start).days + 1 < 7:
                raise ControlError("THRESHOLD_REQUEST_INVALID")
            active.update({"from": start.isoformat(), "to": end.isoformat()})
        self.root.mkdir(parents=True, exist_ok=True)
        current = self.active()
        if current is None or current.get("revision") != revision:
            atomic_json_write(self.active_path, active)
            with self.audit_path.open("a", encoding="utf-8") as audit:
                audit.write(json.dumps({
                    "schema_version": "kmfa.daily_funds.threshold_audit.v1",
                    "revision": revision,
                    "actor": active["actor"],
                    "changed_at": active["applied_at"],
                    "old_value": current,
                    "new_value": active,
                    "reason": active["reason"],
                    "rollback_version": current.get("revision") if isinstance(current, dict) else None,
                }, ensure_ascii=False, sort_keys=True) + "\n")
        return active

    def line(self, balances: Iterable[DailyBalance], business_date: date) -> FloatingLine | None:
        active = self.apply_pending()
        if active is None or active.get("mode") == "disabled":
            return None
        mode = active.get("mode")
        if mode == "numeric":
            amount = validate_custom_numeric(active.get("amount_fen"))
            return FloatingLine("custom_numeric", amount, business_date, business_date, 1, 1, Decimal("1"), True, None, 1, 0)
        if mode == "date_range":
            try:
                return custom_date_line(
                    date.fromisoformat(str(active["from"])),
                    date.fromisoformat(str(active["to"])),
                    tuple(balances),
                )
            except (KeyError, ValueError, ContractError):
                # A custom range with not-yet-available data is an inactive
                # line, never a guessed threshold or a failed cash publication.
                return FloatingLine("custom_date_range", None, business_date, business_date, 0, 0, Decimal("0"), False, "COVERAGE_INSUFFICIENT")
        raise ControlError("THRESHOLD_REQUEST_INVALID")
