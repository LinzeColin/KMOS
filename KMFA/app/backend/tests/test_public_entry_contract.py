"""S03 public entry, private operations and search-index boundary contract."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
from types import SimpleNamespace

import jwt
import yaml
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.main import app
from app import main as main_module, private_access

client = TestClient(app)
CANONICAL_ROOT = "https://kmfa.linzezhang.com/"
REPO = Path(__file__).resolve().parents[4]


def _access_token(
    private_key,
    *,
    issuer: str,
    audience: str,
    kid: str = "test-key",
    valid_for_seconds: int = 300,
) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": "test-operator",
            "iss": issuer,
            "aud": [audience],
            "iat": now,
            "exp": now + timedelta(seconds=valid_for_seconds),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": kid},
    )


def test_root_is_direct_canonical_app_entry():
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 200
    assert "location" not in response.headers
    assert response.headers["x-kmfa-shell-mode"] == "public-app"
    assert '<div id="root">' in response.text
    assert f'<link rel="canonical" href="{CANONICAL_ROOT}">' in response.text
    assert f'<meta property="og:url" content="{CANONICAL_ROOT}">' in response.text
    assert "/assets/" in response.text
    assert "/ui/" not in response.text
    assert 'id="kmfa-app-module"' in response.text

    head = client.head("/", follow_redirects=False)
    assert head.status_code == 200 and not head.content
    assert head.headers["x-kmfa-shell-mode"] == "public-app"


def test_root_contains_complete_static_shell_without_account_controls():
    html = client.get("/").text
    entries = re.findall(r'data-static-shell-entry="([a-z]+)"', html)
    assert entries == ["project", "upload", "search", "progress", "report", "help"]
    for label in ("项目", "上传", "搜索", "进度", "报告", "帮助"):
        assert label in html
    assert 'data-no-js-state="visible"' in html
    assert "JavaScript 已停用" in html
    assert not re.search(r'<input\b[^>]*type=["\'](?:email|password)["\']', html, re.I)
    assert not re.search(r"<(?:button|a)\b[^>]*>\s*(?:登录|注册|OAuth)", html, re.I)
    assert "/api" not in html and "/ops" not in html


def test_public_shell_flag_rolls_back_only_to_stable_static_entry(monkeypatch):
    monkeypatch.setenv("KMFA_PUBLIC_SHELL_ENABLED", "0")
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 200
    assert response.headers["x-kmfa-shell-mode"] == "stable-static"
    assert 'id="kmfa-app-module"' not in response.text
    assert response.text.count("data-static-shell-entry=") == 6
    assert "静态公共入口已就绪" in response.text
    assert "/api" not in response.text and "/ops" not in response.text

    head = client.head("/", follow_redirects=False)
    assert head.status_code == 200 and not head.content
    assert head.headers["x-kmfa-shell-mode"] == "stable-static"


def test_private_dashboard_compatibility_path_is_not_a_public_alias(monkeypatch):
    monkeypatch.delenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", raising=False)
    response = client.get("/ops/app", follow_redirects=False)
    assert response.status_code == 200
    assert response.headers["x-kmfa-app-mode"] == "private-operations"
    assert 'id="kmfa-app-module"' in response.text

    deep = client.get("/ops/app/legacy/deep-link", follow_redirects=False)
    assert deep.status_code == 200
    assert deep.headers["x-kmfa-app-mode"] == "private-operations"


def test_legacy_ui_aliases_are_single_hop_308_for_get_and_head():
    for method in ("GET", "HEAD"):
        for path in ("/ui", "/ui/", "/ui/legacy/deep-link"):
            response = client.request(method, path, follow_redirects=False)
            assert response.status_code == 308
            assert response.headers["location"] == "/"
            final = client.request(
                method, response.headers["location"], follow_redirects=False
            )
            assert final.status_code == 200 and "location" not in final.headers


def test_sitemap_and_share_surface_name_only_the_root(monkeypatch):
    monkeypatch.setenv("KMFA_PUBLIC_INDEXING_ENABLED", "1")
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert response.text.count("<loc>") == 1
    assert f"<loc>{CANONICAL_ROOT}</loc>" in response.text
    assert "/ui" not in response.text


def test_index_hold_is_default_and_keeps_the_human_homepage(monkeypatch):
    monkeypatch.delenv("KMFA_PUBLIC_INDEXING_ENABLED", raising=False)

    root = client.get("/", follow_redirects=False)
    assert root.status_code == 200
    assert root.headers["x-kmfa-index-mode"] == "hold"
    assert "noindex" in root.headers["x-robots-tag"]
    assert root.headers["cache-control"] == "private, no-store"
    assert '<meta name="robots" content="noindex,nofollow,noarchive">' in root.text
    assert '<meta name="robots" content="index,follow,max-snippet:-1">' not in root.text

    robots = client.get("/robots.txt")
    assert robots.status_code == 200
    assert robots.text == "User-agent: *\nDisallow: /\n"
    assert robots.headers["x-kmfa-index-mode"] == "hold"
    assert "noindex" not in robots.headers

    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200
    assert sitemap.text.count("<loc>") == 0
    assert sitemap.headers["x-kmfa-index-mode"] == "hold"


def test_index_flag_typos_fail_closed(monkeypatch):
    monkeypatch.setenv("KMFA_PUBLIC_INDEXING_ENABLED", "enable-ish")
    root = client.get("/")
    assert root.status_code == 200
    assert root.headers["x-kmfa-index-mode"] == "hold"
    assert "noindex" in root.headers["x-robots-tag"]
    assert client.get("/robots.txt").text == "User-agent: *\nDisallow: /\n"
    assert "<loc>" not in client.get("/sitemap.xml").text


def test_promoted_index_mode_allows_only_the_canonical_root(monkeypatch):
    monkeypatch.setenv("KMFA_PUBLIC_INDEXING_ENABLED", "1")

    root = client.get("/", follow_redirects=False)
    assert root.status_code == 200
    assert root.headers["x-kmfa-index-mode"] == "public-root"
    assert "x-robots-tag" not in root.headers
    assert root.headers["cache-control"] == "no-cache, must-revalidate"
    for metadata in (
        '<meta name="robots" content="index,follow,max-snippet:-1">',
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="KMFA">',
        '<meta property="og:title" content="KMFA｜公开工作区">',
        '<meta property="og:locale" content="zh_CN">',
        '<meta name="twitter:card" content="summary">',
    ):
        assert metadata in root.text

    robots = client.get("/robots.txt")
    assert robots.text.splitlines() == [
        "User-agent: *",
        "Disallow: /",
        "Allow: /$",
        "Allow: /assets/",
        "Allow: /robots.txt",
        "Allow: /sitemap.xml",
        f"Sitemap: {CANONICAL_ROOT}sitemap.xml",
    ]
    assert robots.headers["cache-control"] == "public, no-cache, must-revalidate"
    assert robots.headers["content-type"].startswith("text/plain")

    sitemap = client.get("/sitemap.xml")
    assert sitemap.text.count("<loc>") == 1
    assert f"<loc>{CANONICAL_ROOT}</loc>" in sitemap.text
    assert sitemap.headers["cache-control"] == "public, no-cache, must-revalidate"


def test_promoted_root_and_asset_errors_fail_closed(monkeypatch, tmp_path):
    monkeypatch.setenv("KMFA_PUBLIC_INDEXING_ENABLED", "1")
    monkeypatch.setattr(main_module, "FRONTEND_DIST", tmp_path)

    root = client.get("/", follow_redirects=False)
    assert root.status_code == 503
    assert root.headers["x-robots-tag"] == "noindex, nofollow, noarchive"
    assert root.headers["cache-control"] == "private, no-store"

    missing_asset = client.get("/assets/missing-deadbeef.js")
    assert missing_asset.status_code == 404
    assert missing_asset.headers["x-robots-tag"] == "noindex, nofollow, noarchive"
    assert missing_asset.headers["cache-control"] == "private, no-store"


def test_unpublished_private_and_non_page_routes_never_become_index_candidates(
    monkeypatch,
):
    monkeypatch.setenv("KMFA_PUBLIC_INDEXING_ENABLED", "1")
    monkeypatch.delenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", raising=False)
    unpublished_canary = "/unpublished/__kmfa_publication_canary__/private-file"

    robots = client.get("/robots.txt").text
    sitemap = client.get("/sitemap.xml").text
    assert unpublished_canary not in robots
    assert unpublished_canary not in sitemap
    assert all(marker not in sitemap for marker in ("/api", "/ops", "/ui", "/healthz"))

    for path, expected_status in (
        (unpublished_canary, 404),
        ("/ops/app", 200),
        ("/api/状态", 200),
        ("/ui/legacy", 308),
        ("/healthz", 200),
    ):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == expected_status
        assert response.headers["x-kmfa-index-mode"] == "public-root"
        assert response.headers["x-robots-tag"] == "noindex, nofollow, noarchive"
        assert response.headers["cache-control"] == "private, no-store"

    asset_path = re.search(r'(?:src|href)="(/assets/[^"]+)"', client.get("/").text)
    assert asset_path is not None
    asset = client.get(asset_path.group(1))
    assert asset.status_code == 200
    assert asset.headers["x-robots-tag"] == "noindex, nofollow, noarchive"
    assert asset.headers["cache-control"] == "public, max-age=31536000, immutable"


def test_public_health_and_errors_do_not_disclose_private_details():
    health = client.get("/healthz")
    assert health.status_code == 200 and health.json() == {"status": "ok"}
    assert "facts" not in health.text.lower()

    missing = client.get("/this-path-does-not-exist", follow_redirects=False)
    assert missing.status_code == 404 and "location" not in missing.headers
    lowered = missing.text.lower()
    assert (
        "traceback" not in lowered
        and "/opt/" not in lowered
        and "access_token" not in lowered
    )


def test_openapi_and_deep_health_live_only_under_private_ops(monkeypatch):
    monkeypatch.delenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", raising=False)
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/ops/openapi.json").status_code == 200
    deep = client.get("/ops/healthz")
    assert deep.status_code == 200 and "facts_dir_present" in deep.json()


def test_private_paths_fail_closed_and_verify_access_jwt(monkeypatch):
    issuer = "https://test-team.cloudflareaccess.com"
    audience = "test-private-operations-audience"
    trusted_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    forged_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class FakeJwkClient:
        def get_signing_key_from_jwt(self, _token):
            return SimpleNamespace(key=trusted_key.public_key())

    monkeypatch.setenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", "1")
    monkeypatch.setenv("KMFA_CLOUDFLARE_ACCESS_TEAM_DOMAIN", issuer)
    monkeypatch.setenv("KMFA_CLOUDFLARE_ACCESS_AUD", f"{audience},second-private-app")
    monkeypatch.setattr(private_access, "_jwk_client", lambda _uri: FakeJwkClient())

    # The public plane remains anonymous even while the origin guard is active.
    assert client.get("/").status_code == 200
    assert client.get("/healthz").status_code == 200
    assert client.get("/sitemap.xml").status_code == 200

    for path in (
        "/api",
        "/api/状态",
        "/ops",
        "/ops/app",
        "/ops/healthz",
        "/ops/openapi.json",
    ):
        denied = client.get(path)
        assert denied.status_code == 403
        assert denied.json() == {"detail": "cloudflare_access_required"}
        assert denied.headers["cache-control"] == "no-store"
        assert denied.headers["x-robots-tag"] == "noindex, nofollow, noarchive"

    assert client.get("/api-public-near-prefix").status_code == 404

    assert (
        client.get(
            "/api/状态", headers={"Cf-Access-Jwt-Assertion": "not-a-jwt"}
        ).status_code
        == 403
    )

    valid = _access_token(trusted_key, issuer=issuer, audience=audience)
    allowed = client.get("/api/状态", headers={"Cf-Access-Jwt-Assertion": valid})
    assert allowed.status_code == 200
    allowed_dashboard = client.get(
        "/ops/app", headers={"Cf-Access-Jwt-Assertion": valid}
    )
    assert allowed_dashboard.status_code == 200

    wrong_audience = _access_token(
        trusted_key, issuer=issuer, audience="wrong-audience"
    )
    assert (
        client.get(
            "/api/状态", headers={"Cf-Access-Jwt-Assertion": wrong_audience}
        ).status_code
        == 403
    )

    wrong_issuer = _access_token(
        trusted_key,
        issuer="https://other-team.cloudflareaccess.com",
        audience=audience,
    )
    assert (
        client.get(
            "/api/状态", headers={"Cf-Access-Jwt-Assertion": wrong_issuer}
        ).status_code
        == 403
    )

    expired = _access_token(
        trusted_key,
        issuer=issuer,
        audience=audience,
        valid_for_seconds=-1,
    )
    assert (
        client.get(
            "/api/状态", headers={"Cf-Access-Jwt-Assertion": expired}
        ).status_code
        == 403
    )

    forged = _access_token(forged_key, issuer=issuer, audience=audience)
    assert (
        client.get("/api/状态", headers={"Cf-Access-Jwt-Assertion": forged}).status_code
        == 403
    )


def test_enabled_guard_with_missing_or_invalid_config_is_unavailable(monkeypatch):
    monkeypatch.setenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", "typo-still-enables-guard")
    monkeypatch.delenv("KMFA_CLOUDFLARE_ACCESS_TEAM_DOMAIN", raising=False)
    monkeypatch.delenv("KMFA_CLOUDFLARE_ACCESS_AUD", raising=False)
    response = client.get("/api/状态")
    assert response.status_code == 503
    assert response.json() == {"detail": "private_operations_unavailable"}
    assert response.headers["cache-control"] == "no-store"

    monkeypatch.setenv("KMFA_CLOUDFLARE_ACCESS_TEAM_DOMAIN", "http://attacker.invalid")
    monkeypatch.setenv("KMFA_CLOUDFLARE_ACCESS_AUD", "configured")
    assert client.get("/ops/healthz").status_code == 503

    monkeypatch.setenv(
        "KMFA_CLOUDFLARE_ACCESS_TEAM_DOMAIN",
        "https://test-team.cloudflareaccess.com:not-a-port",
    )
    assert client.get("/ops/healthz").status_code == 503


def test_deployment_contract_enables_origin_guard_before_public_bypass():
    compose_path = REPO / "KMFA" / "deploy" / "coolify" / "docker-compose.yml"
    compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    environment = compose["services"]["app"]["environment"]
    assert environment["KMFA_PUBLIC_SHELL_ENABLED"] == (
        "${KMFA_PUBLIC_SHELL_ENABLED:-1}"
    )
    assert environment["KMFA_PUBLIC_INDEXING_ENABLED"] == (
        "${KMFA_PUBLIC_INDEXING_ENABLED:-0}"
    )
    assert environment["KMFA_PRIVATE_OPS_REQUIRE_ACCESS"] == (
        "${KMFA_PRIVATE_OPS_REQUIRE_ACCESS:-1}"
    )
    assert "KMFA_CLOUDFLARE_ACCESS_TEAM_DOMAIN" in environment
    assert "KMFA_CLOUDFLARE_ACCESS_AUD" in environment

    runbook = (REPO / "KMFA" / "deploy" / "coolify" / "README.md").read_text(
        encoding="utf-8"
    )
    for route_pattern in ("`/api`", "`/api/*`", "`/ops`", "`/ops/*`"):
        assert route_pattern in runbook
    assert "Bypass / Include Everyone" in runbook
    assert "KMFA_PUBLIC_INDEXING_ENABLED=0" in runbook
    assert "KMFA_PUBLIC_INDEXING_ENABLED=1" in runbook
    assert "X-KMFA-Index-Mode: public-root" in runbook
    assert "恢复原" in runbook and "Owner Allow 策略" in runbook
    assert (
        runbook.index("先建更具体的路径锁")
        < runbook.index("再启源站私有面守卫")
        < runbook.index("最后公开根路径并验收")
    )


def test_deployment_waits_for_application_and_governance_gates():
    app_e2e = yaml.load(
        (REPO / ".github/workflows/app-e2e.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    deploy = yaml.load(
        (REPO / ".github/workflows/deploy.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )

    assert "workflow_call" in app_e2e["on"]
    assert "push" not in app_e2e["on"]
    assert ".github/workflows/deploy.yml" in app_e2e["on"]["pull_request"]["paths"]
    commands = "\n".join(
        str(step.get("run", "")) for step in app_e2e["jobs"]["e2e"]["steps"]
    )
    steps = app_e2e["jobs"]["e2e"]["steps"]
    python_setup = next(
        step for step in steps if step.get("uses") == "actions/setup-python@v5"
    )
    node_setup = next(
        step for step in steps if step.get("uses") == "actions/setup-node@v4"
    )
    assert python_setup["with"]["python-version"] == "3.12"
    assert node_setup["with"]["node-version"] == "20"
    for command in (
        "pytest -q KMFA/app/backend/tests",
        "validate_taskpack.py --root KMFA",
        "test_validate_taskpack_mutations.py --root KMFA",
        "check_dual_plane_ci.py --root . --require-projects",
    ):
        assert command in commands

    gate = deploy["jobs"]["app-e2e-gate"]
    golden_path = deploy["jobs"]["golden-path"]
    assert deploy["concurrency"] == {
        "group": "kmfa-main-deploy",
        "cancel-in-progress": "true",
    }
    assert gate["uses"] == "./.github/workflows/app-e2e.yml"
    assert golden_path["needs"] == "app-e2e-gate"
