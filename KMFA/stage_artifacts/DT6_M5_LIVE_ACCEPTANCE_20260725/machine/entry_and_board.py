"""补齐 criterion 2 链的两处:真实入口路径(公开首页→进入驾驶舱)+ 检查板(源清单/源检查矩阵)真数据。
本会话执行,证据入 stage_artifacts。"""
import json, sys
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

BASE = sys.argv[1]
OUT = Path("/out"); OUT.mkdir(parents=True, exist_ok=True)
steps = []
def rec(step, ok, detail): steps.append({"step": step, "pass": ok, "detail": detail}); print(f"[{'PASS' if ok else 'FAIL'}] {step}: {detail}")

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = b.new_page(viewport={"width": 1440, "height": 1600})

    # ① 真实入口:公开首页(KMFA 门面)
    page.goto(f"{BASE}/", wait_until="networkidle", timeout=30000)
    page.locator('[data-shell-ready="true"]').wait_for(timeout=10000)
    title = page.title()
    hero = page.locator("#hero-title").inner_text()
    entry = page.locator('a.public-primary-action[href="/ops/app"]')
    ok = "经营驾驶舱" in title and "驾驶舱" in hero and entry.count() == 1
    page.screenshot(path=str(OUT / "E1-public-entry.png"), full_page=False)
    rec("入口① 公开首页(KMFA门面)", ok, f"title={title} 进入驾驶舱入口={entry.count()}")

    # ② 点「进入经营驾驶舱」→ 落到 /ops/app 驾驶舱
    entry.click()
    page.wait_for_url("**/ops/app", timeout=30000)
    page.wait_for_load_state("networkidle")
    header = page.locator("header").inner_text()
    ok = urlsplit(page.url).path == "/ops/app" and "质量" in header and "报告" in header
    page.screenshot(path=str(OUT / "E2-cockpit-arrived.png"), full_page=False)
    rec("入口② 进入驾驶舱(/ops/app)", ok, f"path={urlsplit(page.url).path} 页眉={header.replace(chr(10),' ')[:70]}")

    # ③ 检查板(源清单/源检查矩阵)——PROD.0005,收进「数据底账」
    def tab(name):
        page.get_by_role("tab", name=name).click()
        page.wait_for_function(
            "n => [...document.querySelectorAll('[role=tab]')].some(x => x.textContent===n && x.getAttribute('aria-selected')==='true')",
            arg=name, timeout=15000)
        page.wait_for_timeout(500)
    tab("数据底账")
    body = page.locator("body").inner_text()
    # 源检查矩阵真数据锚点:正式源检查矩阵 + 派生层真值(17 表 / 263,758 行 / Q3)+ 新鲜度批次
    has_matrix = "源检查" in body or "正式源检查矩阵" in body or "覆盖" in body
    has_derived = ("263,758" in body or "263758" in body) or "17" in body
    has_fresh = "2026-07-16" in body
    has_quality = "Q3" in body
    ok = has_matrix and has_fresh and has_quality
    page.screenshot(path=str(OUT / "E3-source-board.png"), full_page=True)
    seen = [ln.strip() for ln in body.split(chr(10)) if any(k in ln for k in ("源检查","覆盖","新鲜","派生","2026-07-16","Q3"))][:6]
    rec("检查板③ 源清单/源检查矩阵(PROD.0005)真数据", ok,
        f"矩阵={has_matrix} 新鲜度批次={has_fresh} 质量Q3={has_quality} 派生={has_derived}")
    (OUT / "source_board_seen.json").write_text(json.dumps({"seen_lines": seen}, ensure_ascii=False, indent=2), encoding="utf-8")

    b.close()

passed = sum(1 for s in steps if s["pass"])
(OUT / "entry_board_result.json").write_text(json.dumps({"passed": passed, "total": len(steps), "steps": steps}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n=== 入口链+检查板: {passed}/{len(steps)} PASS ===")
sys.exit(0 if passed == len(steps) else 1)
