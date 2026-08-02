# -*- coding: utf-8 -*-
"""防止 Coolify 的 project-directory 让镜像构建上下文跳出仓库。

所有 KMFA Dockerfile 都从仓库根目录 ``COPY KMFA/...``。Compose 的相对
``build.context`` 在 Coolify 的实际调用中以 ``--project-directory=<仓根>``
为基准；写成 ``../../..`` 会跳出仓库，配置仍能通过 YAML 校验，实际构建
才会找不到 Dockerfile 或源码。这条门禁不依赖 Docker 守护进程，先在仓内
阻止这种部署期失败。
"""
from __future__ import annotations

import re
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
COMPOSE = REPO / "KMFA/deploy/coolify/docker-compose.yml"
EXPECTED_DOCKERFILES = {
    "daily-funds": "KMFA/skills/每日资金/Dockerfile",
    "app": "KMFA/app/backend/Dockerfile",
    "lifecycle-worker": "KMFA/app/backend/Dockerfile",
}


def _build_mapping(service: str) -> tuple[str, str]:
    """Extract the two scalar build fields without requiring PyYAML at test time."""
    text = COMPOSE.read_text(encoding="utf-8")
    match = re.search(
        rf"^  {re.escape(service)}:\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:|\\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match, f"compose 缺少服务 {service}"
    body = match.group("body")
    context = re.search(
        r"^      context:\s*(\S+)(?:\s+#.*)?\s*$", body, flags=re.MULTILINE
    )
    dockerfile = re.search(
        r"^      dockerfile:\s*(\S+)(?:\s+#.*)?\s*$", body, flags=re.MULTILINE
    )
    assert context, f"{service} 缺少 build.context"
    assert dockerfile, f"{service} 缺少 build.dockerfile"
    return context.group(1), dockerfile.group(1)


def test_all_coolify_builds_use_repository_root_context():
    for service, expected_dockerfile in EXPECTED_DOCKERFILES.items():
        relative_context, dockerfile = _build_mapping(service)
        # Coolify invokes Compose with --project-directory=<repository root>.
        context = (REPO / relative_context).resolve()
        assert context == REPO, (
            f"{service} 的构建上下文不是仓库根目录：{context} != {REPO}；"
            "Dockerfile 的 COPY KMFA/... 会在真实部署时失败"
        )
        assert dockerfile == expected_dockerfile
        assert (context / dockerfile).is_file(), (
            f"{service} Dockerfile 不在 build context 内：{dockerfile}"
        )


def test_shared_skills_reuses_existing_local_image_during_daily_funds_rollout():
    """Do not rebuild unrelated OCR-heavy skills for an independent slice.

    The generic runtime remains separately buildable in CI.  A compact
    Coolify host instead reuses the image already referenced by its running
    ``skills`` container, so an App/daily-funds release cannot exhaust disk
    while downloading Chinese OCR dependencies that the slice never uses.
    """

    text = COMPOSE.read_text(encoding="utf-8")
    match = re.search(
        r"^  skills:\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:|\\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match, "compose 缺少 skills 服务"
    body = match.group("body")
    assert re.search(r"^    build:", body, flags=re.MULTILINE) is None
    assert 'image: "${KMFA_SKILLS_IMAGE:-kmfa-skills:coolify}"' in body
