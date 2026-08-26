"""Contract for the narrow daily-funds source-pointer recovery action."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_source_advance_is_main_only_exact_target_and_values_free() -> None:
    workflow = (ROOT.parents[2] / ".github" / "workflows" / "coolify-ops.yml").read_text(encoding="utf-8")
    start = workflow.index("前进每日资金受控源码并重建")
    step = workflow[start:]

    assert "inputs.mode == 'daily-funds-source-advance'" in step
    assert 'GITHUB_REF:-}" = "refs/heads/main"' in step
    assert 'EXPECTED_SOURCE_REVISION="${GITHUB_SHA:-}"' in step
    assert "EXPECTED_SOURCE_REVISION: ${{ github.sha }}" not in step
    assert 'app.get("name") != "kmfa-kmos-p1"' in step
    assert 'app.get("build_pack") != "dockercompose"' in step
    assert 'app.get("git_branch") != "main"' in step
    assert "LinzeColin/KMOS" in step
    assert "KMFA/deploy/coolify/docker-compose.yml" in step
    assert "DEPLOYMENT_ALREADY_ACTIVE" in step
    assert 'active = active.get("deployments", active.get("items"))' in step
    assert "current_revision = (" in step
    assert '"CURRENT" if current_revision == expected else "ADVANCE"' in step
    assert 'json.dumps({"git_commit_sha": os.environ["EXPECTED_SOURCE_REVISION"]})' in step
    assert 'str(payload.get("git_commit_sha") or "").strip().lower() != expected' in step
    assert "daily_funds_source_advance_pointer=ADVANCED" in step
    assert "daily_funds_source_advance=FINISHED" in step
    assert "echo \"$EXPECTED_SOURCE_REVISION\"" not in step
    assert "print(expected)" not in step
