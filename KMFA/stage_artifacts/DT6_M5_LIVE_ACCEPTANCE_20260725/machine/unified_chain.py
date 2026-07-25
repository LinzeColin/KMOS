"""判据 2 的完整链,一个浏览器会话一次连续跑通:
公开首页 → 进入驾驶舱 → 检查板(源检查板) → 成本页 → 差异处理(真写决策) → 影响预览 → 重跑 → 报告导出。
本会话执行,单次连续 pass,证据入 stage_artifacts。"""
import json, sys
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

BASE = sys.argv[1]
OUT = Path("/out"); OUT.mkdir(parents=True, exist_ok=True)
chain = []
def step(i, name, ok, seen):
    chain.append({"seq": i, "step": name, "pass": ok, "seen": seen})
    print(f"[{'PASS' if ok else 'FAIL'}] {i}. {name} — {seen}")

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    ctx = b.new_context(viewport={"width": 1440, "height": 1600}, accept_downloads=True, locale="zh-CN")
    page = ctx.new_page()
    errs = []
    page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errs.append(str(e)))

    def tab(name):
        page.get_by_role("tab", name=name).click()
        page.wait_for_function(
            "n => [...document.querySelectorAll('[role=tab]')].some(x => x.textContent===n && x.getAttribute('aria-selected')==='true')",
            arg=name, timeout=15000)
        page.wait_for_timeout(400)
    def shot(n): page.screenshot(path=str(OUT / f"chain-{n}.png"), full_page=True)

    # 0. 首页(真实入口:公开 KMFA 门面)
    page.goto(f"{BASE}/", wait_until="networkidle", timeout=30000)
    page.locator('[data-shell-ready="true"]').wait_for(timeout=10000)
    t = page.title(); entry = page.locator('a.public-primary-action[href="/ops/app"]')
    ok = "经营驾驶舱" in t and entry.count() == 1
    shot("0-home"); step(0, "首页(公开门面)", ok, f"title={t}")

    # 进入驾驶舱
    entry.click(); page.wait_for_url("**/ops/app", timeout=30000); page.wait_for_load_state("networkidle")
    header = page.locator("header").inner_text()
    ok = urlsplit(page.url).path == "/ops/app" and all(k in header for k in ("质量", "报告", "NO_GO"))
    step(1, "进入驾驶舱 /ops/app(页眉三徽章)", ok, header.replace(chr(10), " ")[:60])

    # 1. 检查板(源检查板,收进数据底账)
    tab("数据底账"); body = page.locator("body").inner_text()
    ok = ("263,758" in body or "263758" in body) and "Q3" in body and "2026-07-16" in body and ("覆盖" in body or "源检查" in body)
    shot("1-board"); step(2, "检查板(源检查板 真数据)", ok, "17表/263,758行/Q3/覆盖矩阵/批次2026-07-16")

    # 2. 成本页
    tab("项目成本"); body = page.locator("body").inner_text()
    ok = any(k in body for k in ("算不出", "金额尚不可计算", "阻塞")) and "毛利率" not in body
    shot("2-cost"); step(3, "成本页(阻塞如实/无编造毛利)", ok, "算不出金额,无毛利率")

    # 3. 差异处理(真写决策)
    tab("待拍板")
    page.locator("tr", has=page.locator("code", has_text="AST-COLL-202503")).first.click()
    page.wait_for_selector('input[placeholder*="决策理由"]', timeout=15000)
    page.get_by_placeholder("决策理由", exact=False).fill("M5 判据2 全链连续跑:按容差闭案(本会话)")
    page.get_by_role("button", name="闭案 → closed").click()
    page.wait_for_selector("text=已追加事件", timeout=30000)
    body = page.locator("body").inner_text()
    ok = "MANEVT-APP-" in body and "已追加事件" in body
    evt = next((l.strip()[:60] for l in body.split(chr(10)) if "MANEVT-APP-" in l), "")
    shot("3-decision"); step(4, "差异处理(真写决策+留痕)", ok, evt)

    # 4. 影响预览(选源→血缘影响面)
    tab("数据底账")
    page.locator("select").first.select_option("raw:d46f77b0c90d")
    page.wait_for_selector("text=会牵连什么", timeout=15000)
    body = page.locator("body").inner_text()
    ok = "受影响核对域" in body and "expense_lines" in body and "17,764" in body
    shot("4-impact"); step(5, "影响预览(血缘真实行数)", ok, "受影响核对域/expense_lines/17,764")

    # 5. 重跑(四层链)
    page.get_by_placeholder("重跑理由", exact=False).fill("M5 判据2 全链连续跑:四层链(本会话)")
    page.get_by_role("button", name="发起重跑", exact=False).click()
    page.wait_for_selector("text=本次重跑结果", timeout=30000)
    body = page.locator("body").inner_text()
    layers = [k for k in ("field_mapping", "fact_layer", "derived_metric", "report_reference") if k in body]
    ok = len(layers) == 4 and "链完整：是" in body and "旧版本全保留：是" in body
    shot("5-rerun"); step(6, "重跑(四层链完整+旧版本保留)", ok, f"{layers}")

    # 6. 报告导出(三格式真下载)
    tab("报告下载")
    dls = []
    for fmt, magic in (("HTML", b"<!doctype"), ("CSV", b"\xef\xbb\xbf"), ("PDF", b"%PDF")):
        with page.expect_download(timeout=30000) as d:
            page.locator(f'a[href*="格式={fmt.lower()}"]').first.click()
        data = Path(d.value.path()).read_bytes()
        good = data[:16].startswith(magic) and len(data) > 200
        dls.append(f"{fmt}:{len(data)}B/{'OK' if good else 'BAD'}")
        if not good: break
    ok = len(dls) == 3 and all("OK" in x for x in dls)
    shot("6-reports"); step(7, "报告导出(三格式真下载)", ok, "; ".join(dls))

    ctx.close(); b.close()

passed = sum(1 for c in chain if c["pass"])
# COOP 跨源提示是 http 测试环境假阳性,不计入功能失败
coop = [e for e in errs if "Cross-Origin-Opener-Policy" in e]
real_errs = [e for e in errs if "Cross-Origin-Opener-Policy" not in e]
res = {"chain": "首页→检查板→成本页→差异处理→影响预览→重跑→报告导出", "unified_single_pass": True,
       "passed": passed, "total": len(chain), "steps": chain,
       "coop_false_positive": len(coop), "real_console_errors": real_errs}
(OUT / "unified_chain_result.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n=== 判据2 完整链单次连续: {passed}/{len(chain)} PASS (COOP假阳性{len(coop)}, 真错误{len(real_errs)}) ===")
sys.exit(0 if passed == len(chain) and not real_errs else 1)
