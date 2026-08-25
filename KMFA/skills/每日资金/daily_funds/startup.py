"""Startup-only gates for the isolated daily-funds worker."""

from __future__ import annotations

import sqlite3

from .config import ConfigError, DailyFundsConfig
from .parsing import PARSER_VERSION
from .state import RuntimeState


def raw_archive_audit_required(config: DailyFundsConfig | None = None) -> bool:
    """Return whether this container start needs a full raw-archive audit.

    A container restart cannot itself change the parser contract or source
    authority.  Once the current parser version owns a complete verified
    capability scope, the regular 05:20 cloud audit remains responsible for
    fresh source coverage.  Skipping the duplicate startup pass keeps a newly
    requested recovery from waiting behind an identical boot-time read.

    Configuration or journal uncertainty returns ``True``.  The caller then
    runs the normal fail-closed audit, which owns all source validation and
    produces the existing finite operational receipt.
    """

    try:
        resolved = config or DailyFundsConfig.from_env()
        resolved.validate(include_storage=False)
        return not RuntimeState(resolved.state_dir).has_complete_capability_scope(
            parser_version=PARSER_VERSION,
        )
    except (ConfigError, OSError, sqlite3.Error, ValueError):
        return True
