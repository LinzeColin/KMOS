# -*- coding: utf-8 -*-
"""根路径身份守卫 —— 不允许宣传页死而复活。

事情经过（写清楚，因为它已经反复三次）：
  · 2026-07-25 Owner：「这根本不是 KMFA / 一进去不应该是 KMFA 的首页吗」→ #171 归位。
  · 2026-07-26 Owner（线上又变回泛化匿名工作区）：「这根本不是我的东西，你不要搞这些
    恶心人的东西来恶心我」→ #211 归位 + 本守卫首版。
  · 2026-07-27 Owner（看到归位后的 KMFA 门面仍是一张宣传页）：
    「把这个恶心的页面彻底删除掉，不允许死而复活无数次，我只要我的软件」。

因此当前契约是**最终形态**：根路径不是任何门面、不是任何介绍页——
它就是经营驾驶舱应用本体（与 /ops/app 同一个应用）。真实经营数字仍由边缘层
Cloudflare Access 守在 /api* 与 /ops* 之后，未认证者拿到空数据界面而不是数字。

本文件是治理门禁，不是普通单测：**它红了要改代码，不许改它来"修复"失败。**
"""
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
FRONTEND_SRC = Path(__file__).resolve().parents[3] / "app" / "frontend" / "src"
BACKEND_APP = Path(__file__).resolve().parents[1] / "app"

# 三次被 Owner 点名"恶心"的东西的共同特征：营销主张、能力自夸、模块推介文案。
BROCHURE_PHRASES = [
    "把钱、票、成本与拍板",
    "一个入口，通往项目",
    "六个模块",
    "管住经营的每一步",
    "真数据，不用演示冒充",
    "这六个模块已在驾驶舱内上线运转",
    "公开页只讲能力",
    "BUSINESS COCKPIT",
    "PUBLIC WORKSPACE",
]


def test_root_serves_no_brochure_copy():
    html = client.get("/").text
    found = [p for p in BROCHURE_PHRASES if p in html]
    assert not found, (
        f"根路径又出现宣传文案：{found}。Owner 已三次点名要求删除，"
        "根路径只能是驾驶舱应用本体。请改代码，不要改本测试。"
    )


def test_brochure_component_stays_deleted():
    """删掉的组件不许被谁再加回来。"""
    assert not (FRONTEND_SRC / "KmfaHome.jsx").exists(), (
        "KmfaHome.jsx 又出现了。Owner 2026-07-27：「彻底删除掉，不允许死而复活无数次」。"
    )


def test_root_boots_the_operations_app_not_a_landing_page():
    main_jsx = (FRONTEND_SRC / "main.jsx").read_text(encoding="utf-8")
    assert "loadKmfaHome" not in main_jsx, "根路径不得再挂任何门面组件"
    assert "import('./App.jsx')" in main_jsx, "根路径必须加载经营驾驶舱应用"
    assert "PublicAppShell" not in main_jsx, "不得按路径重新挂载已删除页面"


def test_root_still_meets_the_public_boundary():
    """删门面不等于放开边界：根 HTML 仍不得出现私有路径或登录入口。"""
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 200
    html = r.text
    assert "/api" not in html and "/ops" not in html
    assert not re.search(r"<(?:button|a)\b[^>]*>\s*(?:登录|注册|OAuth)", html, re.I)
    assert '<div id="root">' in html


def test_no_js_fallback_is_a_module_list_not_a_pitch():
    """无脚本兜底可以列模块名，但不能变成第二张宣传页。"""
    html = client.get("/").text
    assert html.count("data-static-shell-entry=") == 6, "六个模块入口必须保留"
    assert "静态公共入口已就绪" in html
    # 兜底文案要短：任何一段超过 60 字的推介性描述都是宣传页在回潮
    for para in re.findall(r"<p[^>]*>([^<]{60,})</p>", html):
        assert "数字" in para or "JavaScript" in para, f"兜底出现长篇推介文案：{para[:40]}…"


def test_workspace_page_and_its_recovery_assets_stay_deleted():
    """Owner 明令删除的页面没有兼容路由，也没有可重新挂载的源文件。"""
    for path in ("/workspace", "/workspace/", "/workspace/anything"):
        assert client.get(path, follow_redirects=False).status_code == 404
    assert not (FRONTEND_SRC / "PublicAppShell.jsx").exists()
    assert not (FRONTEND_SRC / "public-shell.css").exists()
    assert not (BACKEND_APP / "workspace_shell_fragment.html").exists()
    assert '"/workspace' not in (BACKEND_APP / "main.py").read_text(encoding="utf-8")
