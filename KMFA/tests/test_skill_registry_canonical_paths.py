from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
KMFA_ROOT = REPO_ROOT / "KMFA"
REGISTRY = KMFA_ROOT / "skills" / "registry.yaml"


def test_every_kmfa_skill_is_registered_under_canonical_root() -> None:
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    entries = registry["skills"]

    ids = [entry["id"] for entry in entries]
    declared = {Path(entry["path"]) for entry in entries}
    discovered = {
        skill_file.parent.relative_to(REPO_ROOT)
        for skill_file in KMFA_ROOT.rglob("SKILL.md")
    }

    assert len(ids) == len(set(ids)), "KMFA Skill IDs must be unique"
    assert declared == discovered, "registry.yaml must exactly cover every KMFA SKILL.md"
    assert all(path.parts[:2] == ("KMFA", "skills") for path in declared)
