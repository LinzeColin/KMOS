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

    @staticmethod
    def _revision(value: object, *, code: str) -> str:
        revision = str(value or "")
        if len(revision) != 64 or any(character not in "0123456789abcdef" for character in revision):
            raise ControlError(code)
        return revision

    @staticmethod
    def _signature(value: Mapping[str, Any], *, code: str) -> tuple[object, ...]:
        """Return the immutable business meaning of a control revision."""

        mode = value.get("mode")
        if mode == "disabled":
            return ("disabled",)
        if mode == "numeric":
            try:
                return ("numeric", validate_custom_numeric(value.get("amount_fen")))
            except ContractError as exc:
                raise ControlError(code) from exc
        if mode == "date_range":
            try:
                start = date.fromisoformat(str(value.get("from") or ""))
                end = date.fromisoformat(str(value.get("to") or ""))
            except ValueError as exc:
                raise ControlError(code) from exc
            if end < start or (end - start).days + 1 < 7:
                raise ControlError(code)
            return ("date_range", start.isoformat(), end.isoformat())
        raise ControlError(code)

    def apply_pending(self) -> dict[str, Any] | None:
        request = self._read(self.request_path)
        if request is None:
            current = self.active()
            if current is not None:
                self._revision(current.get("revision"), code="THRESHOLD_ACTIVE_INVALID")
                self._signature(current, code="THRESHOLD_ACTIVE_INVALID")
            return current
        mode = str(request.get("mode") or "")
        if mode not in {"disabled", "date_range", "numeric"}:
            raise ControlError("THRESHOLD_REQUEST_INVALID")
        revision = self._revision(request.get("revision"), code="THRESHOLD_REQUEST_INVALID")
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
        signature = self._signature(active, code="THRESHOLD_REQUEST_INVALID")
        if current is not None:
            current_revision = self._revision(current.get("revision"), code="THRESHOLD_ACTIVE_INVALID")
            current_signature = self._signature(current, code="THRESHOLD_ACTIVE_INVALID")
            if current_revision == revision:
                if current_signature != signature:
                    raise ControlError("THRESHOLD_REVISION_COLLISION")
                return current
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
            try:
                amount = validate_custom_numeric(active.get("amount_fen"))
            except ContractError as exc:
                raise ControlError("THRESHOLD_ACTIVE_INVALID") from exc
            return FloatingLine("custom_numeric", amount, business_date, business_date, 1, 1, Decimal("1"), True, None, 1, 0)
        if mode == "date_range":
            try:
                start = date.fromisoformat(str(active["from"]))
                end = date.fromisoformat(str(active["to"]))
                return custom_date_line(start, end, tuple(balances))
            except (KeyError, ValueError, ContractError) as exc:
                # A valid range with insufficient observations returns an
                # inactive ``FloatingLine`` above.  Every exception here is
                # therefore malformed saved control data or a balance-quality
                # failure and must not be silently relabelled as coverage.
                if str(exc).startswith("DAILY_BALANCE_"):
                    raise ControlError("THRESHOLD_BALANCE_QUALITY_INVALID") from exc
                raise ControlError("THRESHOLD_ACTIVE_INVALID") from exc
        raise ControlError("THRESHOLD_REQUEST_INVALID")
