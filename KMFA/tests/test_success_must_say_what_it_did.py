# -*- coding: utf-8 -*-
"""rc=0 也要说清楚「做了什么」——成功不是终点。

2026-07-29 的活例子：`dws-data-auth` 连着 **9 次 rc=0**，而 rc=0 底下藏着三种
完全不同的结局：

    AUTH_REQUESTED           授权请求已发出，Owner 该看到弹窗了
    NOT_REQUESTED_BY_DESIGN  按设计没请求（没卡住 / 在静默期内）
    PROBED_ONLY              只探测没发起（压测跑走 --dry-run）

三者在台账里长得**一模一样**：`rc=0，失败码=None`。于是 Owner 说「我没收到
弹窗」时，没有任何人能对上账——不知道它到底请求了没有。

根因在 run_skill.sh：`CODE` 原本只在 `RC -ne 0` 时才提取。
「失败要可诊断」这条已经做到了（#232），但**「成功里做了什么」还是黑的**。

这是今天同一个形状的第四次：
  · 排序：代码在 HTML 里 ≠ 浏览器会执行它
  · 冷启动重试：写进日志 ≠ 有人读得到
  · 技能可见性：技能在跑 ≠ 面上看得见
  · 这次：**跑成功了 ≠ 做了该做的事**
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUN_SKILL = REPO / "KMFA/deploy/skills-runtime/run_skill.sh"


def test_the_ledger_code_is_extracted_on_success_too():
    """CODE 不许再被 `if RC -ne 0` 圈住。

    第一版这条断言写错过：它在取码行**之前**的切片里找
    `if ...; then\\n    CODE=`，而那个字符串正好跨在切片边界上，
    于是把 CODE 圈回失败分支它也照样绿。改成看**前一行**，边界问题消失。
    """
    lines = RUN_SKILL.read_text(encoding="utf-8").splitlines()
    idx = next((i for i, l in enumerate(lines)
                if "skill_failure_code.py" in l and "CODE=" in l), None)
    assert idx is not None, "找不到取码那一行"
    previous = lines[idx - 1].strip() if idx else ""
    assert not previous.startswith('if [ "$RC" -ne 0 ]'), (
        f"取码又被圈回「只在失败时」了——成功里做了什么会重新变黑。上一行：{previous}")


def test_the_health_page_shows_what_a_successful_run_did():
    """健康面必须能显示 rc=0 那次的状态，否则台账有码也白搭。"""
    main = (REPO / "KMFA/app/backend/app/main.py").read_text(encoding="utf-8")
    assert '"本次状态"' in main, "健康面没有「本次状态」这一格"
    # 这一格不能被 rc 条件圈住
    line = next(l for l in main.splitlines() if l.strip().startswith("本次状态 ="))
    assert 'last.get("rc")' not in line, \
        f"「本次状态」也被 rc 圈住了，等于没加：{line.strip()}"


def test_the_three_outcomes_survive_the_public_whitelist():
    """状态码要真能穿过两侧白名单——穿不过就还是显示不出来。

    两侧是**故意各写一遍**的（分属两个容器、两条部署链），所以两边都要验。
    """
    sys.path.insert(0, str(REPO / "KMFA/tools"))
    sys.path.insert(0, str(REPO / "KMFA/app/backend"))
    from skill_failure_code import extract  # noqa: PLC0415
    from app.main import _public_failure_code  # noqa: PLC0415

    for status in ("AUTH_REQUESTED", "NOT_REQUESTED_BY_DESIGN", "PROBED_ONLY",
                   "NO_AUTH_SUBCOMMAND_FOUND", "AUTH_REQUESTED_AWAITING_CONFIRM"):
        log = "开始\n" + json.dumps({"status": status}, ensure_ascii=False) + "\n结束 rc=0\n"
        assert extract(log) == status, f"{status} 没被提取器认出来"
        assert _public_failure_code(status) == status, f"{status} 被端点白名单拦掉了"


def test_the_two_outcomes_are_actually_distinguishable():
    """**本文件的正主。** 「请求已发出」和「按设计没请求」必须能分开。

    分不开，Owner 说「我没收到弹窗」时就无从查起——今天就是这么卡了两个小时。
    """
    sys.path.insert(0, str(REPO / "KMFA/tools"))
    from skill_failure_code import extract  # noqa: PLC0415

    sent = extract('{"status": "AUTH_REQUESTED"}\n结束 rc=0\n')
    quiet = extract('{"status": "NOT_REQUESTED_BY_DESIGN"}\n结束 rc=0\n')
    assert sent != quiet, "两种结局提取出同一个码——等于没分开"
    assert "UNKNOWN" not in (sent, quiet), (sent, quiet)


def test_useless_statuses_still_do_not_take_the_slot():
    """放开 rc=0 取码，不等于让 OK/SUCCESS 这类没信息量的词占住那一格。"""
    sys.path.insert(0, str(REPO / "KMFA/tools"))
    from skill_failure_code import extract, UNKNOWN  # noqa: PLC0415

    assert extract('{"status": "SUCCESS"}\n') == UNKNOWN
    assert extract('{"status": "OK"}\n') == UNKNOWN


def test_no_secret_leaks_through_the_new_slot():
    """这一格现在**每次运行都会填**，暴露面比原来大——凭据形状必须照样拦住。"""
    sys.path.insert(0, str(REPO / "KMFA/app/backend"))
    from app.main import _public_failure_code  # noqa: PLC0415

    for bad in ("ghp_" + "a" * 36, "sk-" + "b" * 32, "A" * 40, "xoxb-" + "c" * 24):
        assert _public_failure_code(bad) is None, f"凭据形状漏出去了：{bad[:12]}…"
    assert _public_failure_code("有中文的状态") is None
    assert not re.search(r"\s", "AUTH_REQUESTED")
