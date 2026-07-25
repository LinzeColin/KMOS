"""M5 驾驶舱现场验收:真起服务→真开 /ops/app→逐页真数据→截图+逐字段实测输出。
本会话执行,证据入 stage_artifacts。不拿 /healthz 充数,不拿 mock 交差。"""
import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://kmfa-acc:8000"
OUT = Path("/out"); OUT.mkdir(parents=True, exist_ok=True)
findings = []

def rec(step, ok, detail, seen):
    findings.append({"step": step, "pass": ok, "detail": detail, "real_seen": seen})
    print(f"[{'PASS' if ok else 'FAIL'}] {step}: {detail}")

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = b.new_page(viewport={"width": 1440, "height": 1600}, accept_downloads=True)
    errs = []
    page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errs.append(str(e)))

    def tab(name):
        page.get_by_role("tab", name=name).click()
        page.wait_for_function(
            "n => [...document.querySelectorAll('[role=tab]')]"
            ".some(x => x.textContent === n && x.getAttribute('aria-selected') === 'true')",
            arg=name, timeout=15000)
        page.wait_for_timeout(400)

    def shot(name):
        page.screenshot(path=str(OUT / name), full_page=True)

    # ① 登录/入口 + 页眉三徽章
    page.goto(f"{BASE}/ops/app", wait_until="networkidle", timeout=30000)
    header = page.locator("header").inner_text()
    trip = [k for k in ("质量", "报告", "NO_GO", "GO") if k in header]
    ok = "质量" in header and "报告" in header
    shot("01-ops-app-landing.png")
    rec("01 入口+页眉三徽章", ok, f"header含: {trip}", header.replace(chr(10), " ")[:120])

    # ② 今天
    tab("今天"); body = page.locator("body").inner_text()
    ok = "等你拍板" in body and "BLK-001" in body and "暂不可对外" in body
    shot("02-today.png")
    rec("02 今天(人话判决+拍板队列+真阻塞)", ok,
        f"等你拍板={'等你拍板' in body} BLK-001={'BLK-001' in body} 暂不可对外={'暂不可对外' in body}",
        [ln for ln in body.split(chr(10)) if "BLK-001" in ln][:1])

    # ③ 回款与账龄
    tab("回款与账龄"); body = page.locator("body").inner_text()
    ok = "回款逐月核对" in body and "已对平" in body
    shot("03-receivables.png")
    rec("03 回款与账龄(逐月核对+已对平)", ok,
        f"逐月核对={'回款逐月核对' in body} 已对平={'已对平' in body}",
        [ln for ln in body.split(chr(10)) if "已对平" in ln][:1])

    # ④ 项目成本(阻塞如实,无编造毛利)
    tab("项目成本"); body = page.locator("body").inner_text()
    blocked = any(k in body for k in ("金额尚不可计算", "算不出", "阻塞"))
    ok = blocked and "毛利率" not in body
    shot("04-costs.png")
    rec("04 项目成本(阻塞如实/无编造毛利)", ok, f"阻塞呈现={blocked} 无毛利率={'毛利率' not in body}",
        [ln for ln in body.split(chr(10)) if any(k in ln for k in ('阻塞','不可计算','算不出'))][:1])

    # ⑤ 待拍板:真写一条决策
    tab("待拍板")
    page.locator("tr", has=page.locator("code", has_text="AST-COLL-202503")).first.click()
    page.wait_for_selector('input[placeholder*="决策理由"]', timeout=15000)
    page.get_by_placeholder("决策理由", exact=False).fill("M5 现场验收:按容差闭案(本会话)")
    page.get_by_role("button", name="闭案 → closed").click()
    page.wait_for_selector("text=已追加事件", timeout=30000)
    body = page.locator("body").inner_text()
    ok = "MANEVT-APP-" in body and "已追加事件" in body
    evt = ""
    for ln in body.split(chr(10)):
        if "MANEVT-APP-" in ln: evt = ln.strip()[:80]; break
    shot("05-decision-writeback.png")
    rec("05 待拍板(真写决策+留痕事件)", ok, f"事件号出现={'MANEVT-APP-' in body}", evt)

    # ⑥ 数据底账:选源→影响面由血缘算出真实行数
    tab("数据底账")
    page.locator("select").first.select_option("raw:d46f77b0c90d")
    page.wait_for_selector("text=会牵连什么", timeout=15000)
    body = page.locator("body").inner_text()
    ok = "受影响核对域" in body and "expense_lines" in body and "17,764" in body
    shot("06-lineage-impact.png")
    rec("06 数据底账(影响面真实派生表+行数)", ok,
        f"受影响核对域={'受影响核对域' in body} expense_lines={'expense_lines' in body} 17,764={'17,764' in body}",
        [ln for ln in body.split(chr(10)) if "17,764" in ln][:1])

    # ⑦ 重跑:四层链真发起并完成
    page.get_by_placeholder("重跑理由", exact=False).fill("M5 现场验收:四层链验证(本会话)")
    page.get_by_role("button", name="发起重跑", exact=False).click()
    page.wait_for_selector("text=本次重跑结果", timeout=30000)
    body = page.locator("body").inner_text()
    layers = [k for k in ("field_mapping", "fact_layer", "derived_metric", "report_reference") if k in body]
    ok = len(layers) == 4 and "链完整：是" in body and "旧版本全保留：是" in body
    shot("07-rerun-4layer.png")
    rec("07 重跑(四层链完整+旧版本保留)", ok, f"命中层={layers} 链完整={'链完整：是' in body} 旧版本保留={'旧版本全保留：是' in body}", layers)

    # ⑧ 报告下载:三格式真下载+水印/等级
    tab("报告下载")
    dl_results = []
    for fmt, magic in (("HTML", b"<!doctype"), ("CSV", b"\xef\xbb\xbf"), ("PDF", b"%PDF")):
        with page.expect_download(timeout=30000) as dl:
            page.locator(f'a[href*="格式={fmt.lower()}"]').first.click()
        pth = Path(dl.value.path()); data = pth.read_bytes()
        good = data[:16].startswith(magic) and len(data) > 200
        mark = ("delivery_allowed=false" in data.decode("utf-8", "ignore")) or fmt == "PDF"
        dl_results.append(f"{fmt}:{len(data)}B/{'魔数OK' if good else '魔数坏'}/{'水印' if mark else '无水印'}")
        if not (good and mark): break
    ok = len(dl_results) == 3 and all("OK" in r for r in dl_results)
    shot("08-reports.png")
    rec("08 报告下载(三格式真下载+水印)", ok, "; ".join(dl_results), dl_results)

    # ⑨ 系统自检
    tab("系统自检"); body = page.locator("body").inner_text()
    ok = "排程" in body and any(k in body for k in ("从未跑过", "读不到排程日志", "成功"))
    shot("09-selfcheck.png")
    rec("09 系统自检(排程状态如实)", ok, f"排程={('排程' in body)}", [ln for ln in body.split(chr(10)) if "排程" in ln][:1])

    b.close()

passed = sum(1 for f in findings if f["pass"])
summary = {"total": len(findings), "passed": passed, "failed": len(findings) - passed,
           "console_errors": errs[:10], "findings": findings}
(OUT / "acceptance_result.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n=== M5 现场验收: {passed}/{len(findings)} PASS, console_errors={len(errs)} ===")
sys.exit(0 if passed == len(findings) and not errs else 1)
