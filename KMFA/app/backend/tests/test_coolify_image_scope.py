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
DAILY_FUNDS_DOCKERFILE = REPO / "KMFA/skills/每日资金/Dockerfile"


def test_kmfa_images_copy_only_runtime_and_shared_contract_layers():
    dockerignore = (REPO / ".dockerignore").read_text(encoding="utf-8")
    assert {"KM_IDSystem/", "whkmSalary/"} <= set(dockerignore.splitlines())

    for dockerfile in (APP_DOCKERFILE, SKILLS_DOCKERFILE):
        text = dockerfile.read_text(encoding="utf-8")
        assert "COPY . /opt/kmfa/KMOS" not in text
        assert "COPY KMDatabase /opt/kmfa/KMOS/KMDatabase" in text
        assert "COPY KMFA /opt/kmfa/KMOS/KMFA" in text


def test_app_image_uses_ci_verified_frontend_dist_not_a_host_node_build():
    """Keep the production build below the Coolify host's disk ceiling.

    The matching GitHub Actions gate rebuilds this tracked ``dist`` with the
    lockfile and rejects a diff before the image test runs.  The Dockerfile
    must therefore consume that exact artifact rather than materialising a
    second Node dependency tree on the constrained production builder.
    """

    text = APP_DOCKERFILE.read_text(encoding="utf-8")
    assert "FROM node:" not in text
    assert "npm ci" not in text
    assert (
        "COPY KMFA/app/frontend/dist "
        "/opt/kmfa/KMOS/KMFA/app/frontend/dist"
    ) in text


def test_daily_funds_runtime_reuses_the_app_base_and_keeps_fetch_tools_build_only():
    """The independent worker must not double the constrained host's base layers."""

    text = DAILY_FUNDS_DOCKERFILE.read_text(encoding="utf-8")
    base = "FROM python:3.12-slim-bookworm"
    assert text.count(base) == 2
    assert f"{base} AS dws-installer" in text
    assert "COPY --from=dws-installer /usr/local/bin/dws /usr/local/bin/dws" in text
    runtime = text.split(base, maxsplit=2)[-1]
    assert "curl" not in runtime
    assert "procps" not in runtime
