#!/usr/bin/env python3
"""项目成本页：**真浏览器真点击**回归。

为什么非要一套真浏览器测试（2026-07-29）：
Owner 报「排序功能无法使用」。当时仓里有两条排序断言、全绿：

    assert "aria-sort" in r.text      → 命中的是 CSS 规则 th[aria-sort]::after
    assert "空值永远沉底" in r.text     → 命中的是**脚本里的注释**

两条都只证明「字符串在 HTML 里」。而页面脚本当时是内联的，被本站 CSP
（`script-src 'self'`，无 `'unsafe-inline'`）拒绝执行——拦截恰好发生在
「字符串已经在 HTML 里」之后。**没有任何纯文本断言能看见这件事。**

更阴的是 `style-src` 带 `'unsafe-inline'`：内联样式照常生效。于是手型光标、
hover 变色、⇅ 箭头全在，页面看着完全正常，只有行为是死的。

所以这一套只问一个问题：**点下去，事情有没有真的发生。**
两道判据：
  1. 整页不许有 CSP 违规（`securitypolicyviolation` 事件），不只是脚本；
  2. 点表头之后，行的顺序必须真的变了——比对点击前后的合同编号序列。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeout

COST_PATH = "/项目成本"

# 刻意造出排序能看出差别的分布：数量级跨度大（按字符串排会错），且有一个空值。
SAMPLE = {
    "schema_version": "kmfa.project_cost.current.v4",
    "快照ID": "kmfa-pc-2099-page-e2e",
    "计算状态": "PASS",
    "待确认": {
        "状态": "PASS",
        "P0阻断数": 0,
        "P1开放复核数": 0,
        "P2已排除或提示数": 0,
    },
    "项目数": 4,
    "封印来源": {
        "源码摘要算法": "kmfa.project_cost.subject_tree.v1",
        "源码SHA256": "a" * 64,
        "源码文件数": 1,
        "输入清单类型": "PRIVATE_MANIFEST_SHA256",
        "输入清单SHA256": "b" * 64,
        "私有输入清单SHA256": "b" * 64,
        "选中来源绑定SHA256": "c" * 64,
    },
    "封印工作簿": {
        "文件名": "sealed-page-e2e.xlsx",
        "SHA256": "d" * 64,
        "字节数": 1,
        "快照ID": "kmfa-pc-2099-page-e2e",
    },
    "生成时间": "2026-07-29T09:00:00+08:00",
    "项目": [
        {"合同编号": "E2E-002", "项目名称": "合成项目乙", "甲方名称": "合成客户乙",
         "施工状态": "施工中", "含税合同金额": "5000000",
         "项目过账实际": "1000000", "项目应计": "0", "项目已发生成本": "1000000",
         "项目成本": "2000000", "有效合同额": "5000000",
         "毛利": "3000000", "毛利率": "60.00%", "毛利率基点": 6000,
         "收入与毛利状态": "READY",
         "项目成本覆盖": "FULL_SELECTED_GL_PERIOD;POSTING_PRESENT"},
        {"合同编号": "E2E-003", "项目名称": "合成项目丙", "甲方名称": "合成客户丙",
         "施工状态": "待入场", "含税合同金额": "80000",
         "项目过账实际": "250000", "项目应计": "0", "项目已发生成本": "250000",
         "项目成本": "250000", "有效合同额": "80000",
         "毛利": "-170000", "毛利率": "-212.50%", "毛利率基点": -21250,
         "收入与毛利状态": "READY",
         "项目成本覆盖": "FULL_SELECTED_GL_PERIOD;POSTING_PRESENT"},
        {"合同编号": "E2E-004", "项目名称": "合成项目丁", "甲方名称": "合成客户丁",
         "施工状态": "已完工", "项目过账实际": "77777", "项目应计": "0",
         "项目已发生成本": "77777",
         "收入与毛利状态": "BLOCKED_COST_COMPLETENESS",
         "项目成本覆盖": "FULL_SELECTED_GL_PERIOD;POSTING_PRESENT"},
        {"合同编号": "E2E-001", "项目名称": "合成项目甲", "甲方名称": "合成客户甲",
         "施工状态": "已完工",
         "完工日期": "2025-06-30", "含税合同金额": "100000",
         "项目过账实际": "40000", "项目应计": "-31000", "项目已发生成本": "9000",
         "项目成本": "40000", "有效合同额": "100000",
         "毛利": "60000", "毛利率": "60.00%", "毛利率基点": 6000,
         "收入与毛利状态": "READY",
         "项目成本覆盖": "FULL_SELECTED_GL_PERIOD;POSTING_PRESENT"},
    ],
}

# 有效收入列。数量级跨到 5,000,000 vs 80,000——按显示的千分位字符串排会把
# 「1,000,000」排在「9,000」前面，这一列专门用来照出那种退化。
REVENUE_COL = 4

CSP_WATCHER = """
window.__cspViolations = [];
document.addEventListener('securitypolicyviolation', function (e) {
  window.__cspViolations.push({
    directive: e.violatedDirective,
    blocked: e.blockedURI,
    sample: (e.sample || '').slice(0, 120)
  });
});
"""


def _run(*cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def _wait_healthy(base_url: str, timeout_s: int = 120) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/healthz", timeout=3) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(2)
    raise SystemExit("App 未起来")


def _order(page: Page) -> list[str]:
    return page.eval_on_selector_all(
        "#costtbl tbody tr", "rows => rows.map(r => r.cells[0].textContent.trim())")


def _column(page: Page, idx: int) -> list[str]:
    return page.eval_on_selector_all(
        "#costtbl tbody tr",
        f"rows => rows.map(r => r.cells[{idx}].getAttribute('data-v'))")


def _check(results: list[dict], name: str, ok: bool, detail: str) -> None:
    results.append({"step": name, "status": "PASS" if ok else "FAIL", "detail": detail})
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")


def run_flow(page: Page, base_url: str, results: list[dict]) -> None:
    page.add_init_script(CSP_WATCHER)
    response = page.goto(f"{base_url}{COST_PATH}", wait_until="load", timeout=30_000)
    _check(results, "页面能打开", bool(response and response.status == 200),
           f"HTTP {response.status if response else '无响应'}")

    # ① 整页不许有 CSP 违规。这一条是通用的：脚本、样式、图片、字体都算。
    violations = page.evaluate("() => window.__cspViolations || []")
    _check(results, "没有 CSP 违规", not violations,
           "无" if not violations else json.dumps(violations, ensure_ascii=False))

    # ② 脚本真的跑过了。role/tabIndex 是脚本挂上去的——出问题时线上正是 null / -1。
    role = page.get_attribute('#costtbl thead th[data-s="n"]', "role")
    tab_index = page.evaluate(
        "() => document.querySelector('#costtbl thead th[data-s=\\'n\\']').tabIndex")
    _check(results, "排序脚本已执行", role == "button" and tab_index == 0,
           f"role={role!r} tabIndex={tab_index}（脚本没跑时是 null / -1）")

    headers = [text.strip() for text in page.locator("#costtbl thead th").all_inner_texts()]
    forbidden_headers = {
        "支付观察",
        "主营成本结转",
        "状态表观察",
        "过账应计",
        "合格应计",
    }
    _check(results, "毛利率列明确展示", "毛利率" in headers, f"表头={headers}")
    _check(
        results,
        "已删除指定观察与应计列",
        forbidden_headers.isdisjoint(headers),
        f"表头={headers}",
    )

    before = _order(page)
    header = page.locator("#costtbl thead th").nth(REVENUE_COL)

    # ③ 点一下：顺序必须真的变，而且是**按数值**降序。
    header.click()
    desc = _order(page)
    desc_values = [v for v in _column(page, REVENUE_COL) if v not in (None, "")]
    numeric_desc = [float(v) for v in desc_values]
    _check(results, "点表头之后顺序真的变了", desc != before,
           f"{before} → {desc}")
    _check(results, "降序是按数值不是按字符串",
           numeric_desc == sorted(numeric_desc, reverse=True),
           f"{numeric_desc}")

    # ④ 再点一下：反向，且空值**仍然**沉底（不能因为升序就冒充最小值）。
    header.click()
    asc_values_raw = _column(page, REVENUE_COL)
    asc_numeric = [float(v) for v in asc_values_raw if v not in (None, "")]
    empties_at = [i for i, v in enumerate(asc_values_raw) if v in (None, "")]
    _check(results, "再点一次是升序", asc_numeric == sorted(asc_numeric),
           f"{asc_numeric}")
    _check(results, "升序时空值仍然沉底",
           all(i >= len(asc_numeric) for i in empties_at),
           f"空值在第 {empties_at} 行，共 {len(asc_values_raw)} 行")

    # ⑤ 文本列也要能排（走的是 localeCompare 分支，跟数值列不是同一段代码）。
    name_before = _order(page)
    page.locator("#costtbl thead th").nth(0).click()
    _check(results, "文本列也能排", _order(page) != name_before,
           f"{name_before} → {_order(page)}")

    # ⑥ 「重新计算」必须**有结论**。
    # 注意别只等「文本非空」——按下去立刻会显示「正在提交…」，那是过渡态，
    # 真卡住时它会一直停在那儿，而「等非空」会当场变绿。要等的是**终态**。
    page.locator("#recalc").click()
    try:
        page.wait_for_function(
            "() => { var t = document.getElementById('recalcmsg').textContent.trim();"
            "        return t.length > 0 && t !== '正在提交…'; }",
            timeout=20_000)
        msg = page.locator("#recalcmsg").inner_text().strip()
    except PlaywrightTimeout:
        # 超时本身就是结论之一（按钮是死的 / 请求挂住了），要落成**这一步**的红，
        # 而不是抛出去让整套在这里断掉——那样报告里看不出是哪一步坏的。
        msg = page.locator("#recalcmsg").inner_text().strip()
        _check(results, "重新计算有结论（不是停在「正在提交…」）", False,
               f"等了 20 秒没等到终态，当前文案：{msg[:80]!r}（空=按钮根本没响应）")
        return
    _check(results, "重新计算有结论（不是停在「正在提交…」）",
           bool(msg) and msg != "正在提交…", msg[:140])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--container-name", default="kmfa-cost-e2e")
    parser.add_argument("--port", type=int, default=18106)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    state_dir = Path(tempfile.mkdtemp(prefix="kmfa-cost-e2e-"))
    artifact = state_dir / "recent_completed.json"
    artifact.write_text(json.dumps(SAMPLE, ensure_ascii=False), encoding="utf-8")
    artifact.chmod(0o644)
    state_dir.chmod(0o755)

    base_url = f"http://localhost:{args.port}"
    _run("docker", "rm", "-f", args.container_name, check=False)
    _run(
        "docker", "run", "-d", "--name", args.container_name,
        "-p", f"{args.port}:8000",
        "-e", "KMFA_RECENT_COST=/var/lib/kmfa/state/recent_completed.json",
        "-v", f"{state_dir}:/var/lib/kmfa/state",
        args.image,
    )

    results: list[dict] = []
    try:
        _wait_healthy(base_url)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page()
                run_flow(page, base_url, results)
            finally:
                browser.close()
    except Exception as exc:  # noqa: BLE001 —— 任何异常都要落进产物再判红
        _check(results, "流程未抛异常", False, f"{type(exc).__name__}: {exc}")
        logs = _run("docker", "logs", args.container_name, check=False)
        (args.out_dir / "container.log").write_text(
            (logs.stdout or "") + (logs.stderr or ""), encoding="utf-8")
    finally:
        _run("docker", "rm", "-f", args.container_name, check=False)

    (args.out_dir / "project_cost_page_e2e.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    failed = [r for r in results if r["status"] == "FAIL"]
    if failed or not results:
        print(f"\n❌ {len(failed)} 步失败" if failed else "\n❌ 一步都没跑到")
        return 1
    print(f"\n✅ {len(results)} 步全通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
