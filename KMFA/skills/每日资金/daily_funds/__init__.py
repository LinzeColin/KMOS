"""Independent, deterministic daily-funds runtime.

The package intentionally contains no agent, model, local-machine or existing
KMFA skill dependency.  Runtime input enters only through the configured DWS
history command; public KMFA code reads only the validated projection pointer.
"""

from .contracts import (
    HARD_THRESHOLD_FEN,
    SOFT_THRESHOLD_FEN,
    HUMAN_STATUSES,
    fixed_risk,
    parse_amount_to_fen,
)

__all__ = [
    "HARD_THRESHOLD_FEN",
    "SOFT_THRESHOLD_FEN",
    "HUMAN_STATUSES",
    "fixed_risk",
    "parse_amount_to_fen",
]
