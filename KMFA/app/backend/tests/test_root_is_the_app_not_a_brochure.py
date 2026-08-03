# -*- coding: utf-8 -*-
"""Root public-access guard.

Owner 2026-08-03 explicitly required the default KMFA site to be public with
no login.  The root must therefore load the anonymous public workspace.  The
private operations dashboard remains at /ops/app and continues to be guarded
by Cloudflare Access plus the origin JWT verifier.
"""

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
FRONTEND_SRC = Path(__file__).resolve().parents[3] / "app" / "frontend" / "src"


def test_root_serves_the_anonymous_public_copy():
    html = client.get("/").text
    assert "一个入口，通往项目、文件与可验证进度。" in html
    assert "KMFA｜公开工作区" in html
    assert "KMFA｜经营驾驶舱" not in html


def test_removed_cockpit_home_component_stays_deleted():
    assert not (FRONTEND_SRC / "KmfaHome.jsx").exists()


def test_root_boots_the_public_shell_not_the_private_dashboard():
    main_jsx = (FRONTEND_SRC / "main.jsx").read_text(encoding="utf-8")
    assert "loadKmfaHome" not in main_jsx
    assert "loadPrivateOperationsApp()" in main_jsx
    assert "loadPublicAppShell()" in main_jsx
    assert "const appModule = isPrivateOperationsApp" in main_jsx


def test_root_has_no_private_paths_or_login_controls():
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 200
    html = response.text
    assert "/api" not in html and "/ops" not in html
    assert not re.search(r"<(?:button|a)\b[^>]*>\s*(?:登录|注册|OAuth)", html, re.I)
    assert '<div id="root">' in html


def test_no_js_fallback_is_a_complete_public_module_list():
    html = client.get("/").text
    assert html.count("data-static-shell-entry=") == 6
    assert "静态公共入口已就绪" in html
    assert re.findall(r'data-static-shell-entry="([a-z]+)"', html) == [
        "project", "upload", "search", "progress", "report", "help",
    ]


def test_workspace_remains_a_public_compatibility_path():
    response = client.get("/workspace")
    assert response.status_code == 200
    assert response.headers.get("x-kmfa-shell-mode") == "public-workspace"
    assert "<title>KMFA｜公开工作区</title>" in response.text
