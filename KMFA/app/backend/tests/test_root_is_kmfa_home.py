# -*- coding: utf-8 -*-
"""根路径身份守卫 —— Owner 明令：根域名必须是 KMFA 自己的经营驾驶舱门面。

背景（写清楚，免得再被改回去）：
  · 2026-07-25 Owner：「这根本不是 KMFA / 一进去不应该是 KMFA 的首页吗」→ #171 归位。
  · 2026-07-26 Owner 再次（看到线上又变回匿名工作区）：「这根本不是我的东西，
    你不要搞这些恶心人的东西来恶心我」，并指明是 Codex 开发线覆盖的、要求管住。

因此本测试是**治理门禁**，不是普通单测：
  根路径必须是 KMFA 经营驾驶舱门面；v1.5.2 匿名 App Shell 不删除，平移到 `/workspace`。
  任何把根路径改回匿名工作区的改动，都会在这里失败——请勿修改本测试来"修复"失败，
  应当保持根路径归属不变。
"""
import re
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
KMFA_ENTRIES = ["today", "cash", "tax", "cost", "decide", "report"]
WORKSPACE_ENTRIES = ["project", "upload", "search", "progress", "report", "help"]


def _entries(html: str) -> list[str]:
    return re.findall(r'data-static-shell-entry="([a-z]+)"', html)


def test_root_is_kmfa_business_cockpit_not_generic_workspace():
    html = client.get("/").text
    assert _entries(html) == KMFA_ENTRIES, (
        "根路径必须是 KMFA 经营驾驶舱门面（今天/回款账龄/开票税务/项目成本/待拍板/报告），"
        "不得是匿名工作区六入口。Owner 已两次明确此归属。"
    )
    assert "把钱、票、成本与拍板" in html, "根路径缺 KMFA 主张锚点"
    assert "KMFA｜经营驾驶舱" in html, "根路径标题必须是 KMFA 经营驾驶舱"


def test_workspace_keeps_anonymous_app_shell():
    """v1.5.2 匿名 App Shell 不删除，只平移——其契约在 /workspace 上继续成立。"""
    r = client.get("/workspace")
    assert r.status_code == 200
    assert r.headers.get("x-kmfa-shell-mode") == "public-workspace"
    assert _entries(r.text) == WORKSPACE_ENTRIES, "匿名工作区六入口必须在 /workspace 完整保留"


def test_root_and_workspace_are_distinct_faces():
    assert _entries(client.get("/").text) != _entries(client.get("/workspace").text)
