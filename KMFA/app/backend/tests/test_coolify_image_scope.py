"""Keep unrelated KM product lines out of KMFA production images.

Coolify builds the compose services from the repository root.  On its compact
host, copying the whole monorepo can exhaust the disk after dependency layers
have already been built.  KMFA's runtime contract only needs ``KMFA`` plus the
shared ``KMDatabase`` schema/tool layer, so this remains a static gate in the
same test suite that protects the deployed App image.
"""
from __future__ import annotations

from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
APP_DOCKERFILE = REPO / "KMFA/app/backend/Dockerfile"
SKILLS_DOCKERFILE = REPO / "KMFA/deploy/skills-runtime/Dockerfile"


def test_kmfa_images_copy_only_runtime_and_shared_contract_layers():
    dockerignore = (REPO / ".dockerignore").read_text(encoding="utf-8")
    assert {"KM_IDSystem/", "whkmSalary/"} <= set(dockerignore.splitlines())

    for dockerfile in (APP_DOCKERFILE, SKILLS_DOCKERFILE):
        text = dockerfile.read_text(encoding="utf-8")
        assert "COPY . /opt/kmfa/KMOS" not in text
        assert "COPY KMDatabase /opt/kmfa/KMOS/KMDatabase" in text
        assert "COPY KMFA /opt/kmfa/KMOS/KMFA" in text
