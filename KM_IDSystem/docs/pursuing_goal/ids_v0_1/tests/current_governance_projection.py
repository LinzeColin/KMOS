import re
from pathlib import Path


def _roadmap_current_projection(roadmap: Path) -> tuple[str, str, str, str]:
    text = roadmap.read_text(encoding="utf-8")
    fields = (
        "current_stage_id",
        "current_phase_id",
        "current_task_id",
        "next_gate_id",
    )
    values: list[str] = []
    for field in fields:
        match = re.search(rf'^{field}: "([^"]+)"$', text, flags=re.MULTILINE)
        if match is None:
            raise AssertionError(f"roadmap missing {field}")
        values.append(match.group(1))
    return values[0], values[1], values[2], values[3]


def assert_legacy_or_current_projection(
    test_case,
    observed: tuple[str, ...],
    legacy_projections,
    status: dict,
    plan: dict,
    roadmap: Path,
) -> bool:
    """Validate a historical projection or the single current roadmap projection.

    Historical stage tests retain their explicit local progression.  When the
    project advances beyond that local list, the canonical roadmap projection,
    status fact, and plan fact must agree before the test continues.
    """
    roadmap_projection = _roadmap_current_projection(roadmap)
    status_projection = (
        status["stage"],
        status["phase"],
        status["task"],
        status["next_gate"],
    )
    plan_projection = (plan["stage"], plan["phase"], plan["task"])
    test_case.assertEqual(roadmap_projection, status_projection)
    test_case.assertEqual(roadmap_projection[:3], plan_projection)
    test_case.assertEqual(roadmap_projection[: len(observed)], observed)
    return observed not in legacy_projections
