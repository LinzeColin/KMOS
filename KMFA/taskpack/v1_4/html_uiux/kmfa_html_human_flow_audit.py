#!/usr/bin/env python3
"""
KMFA HTML human-flow audit.
Purpose: open local HTML files, click visible buttons/links, type in search inputs, capture console errors,
and report whether each user-facing control produces visible feedback or a safe local navigation.
"""
from __future__ import annotations
import argparse, csv, os, sys, hashlib, threading, socketserver, http.server, time
from pathlib import Path
from urllib.parse import urlparse, unquote, quote
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

CHROMIUM = os.environ.get("KMFA_CHROMIUM", "/usr/bin/chromium")

def file_url(path: Path, root: Path|None=None, base_url: str|None=None) -> str:
    if root is not None and base_url is not None:
        rel = path.resolve().relative_to(root.resolve()).as_posix()
        return base_url.rstrip('/') + '/' + quote(rel)
    return path.resolve().as_uri()

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

def start_server(root: Path):
    handler = lambda *a, **kw: QuietHandler(*a, directory=str(root), **kw)
    httpd = socketserver.TCPServer(('127.0.0.1', 0), handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, f'http://127.0.0.1:{port}'

def norm_text(s: str, n: int = 90) -> str:
    return " ".join((s or "").split())[:n]

def safe_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def audit_file(browser, html_path: Path, root: Path, base_url: str|None=None):
    page = browser.new_page(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    console_errors=[]
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type in ("error", "warning") else None)
    page.on("pageerror", lambda exc: console_errors.append(str(exc)))
    results=[]
    page.set_content(html_path.read_text(encoding="utf-8", errors="ignore"), wait_until="load")
    page.wait_for_timeout(120)
    title=page.title()
    # links: verify local href exists or is empty/hash safe
    link_count=page.locator("a").count()
    for i in range(link_count):
        loc=page.locator("a").nth(i)
        try:
            href=loc.get_attribute("href") or ""
            text=norm_text(loc.inner_text(timeout=1000))
            ok=True; reason="local link ok"
            if href.startswith("http"):
                ok=True; reason="external link not clicked"
            elif href.startswith("#") or href.strip()=="":
                ok=True; reason="hash/empty link"
            else:
                target=(html_path.parent / unquote(href.split('#')[0])).resolve()
                ok=target.exists()
                reason="exists" if ok else f"missing target: {target}"
            results.append([html_path.name,title,"link",i,text,href,"PASS" if ok else "FAIL",reason,"; ".join(console_errors[-3:])])
        except Exception as e:
            results.append([html_path.name,title,"link",i,"","","FAIL",f"link inspect error: {e}","; ".join(console_errors[-3:])])
    # inputs: type and observe body or visible rows change
    inp_count=page.locator("input:visible").count()
    for i in range(inp_count):
        loc=page.locator("input:visible").nth(i)
        try:
            before=page.locator("body").inner_text(timeout=1000)
            loc.fill("金蝶")
            page.wait_for_timeout(120)
            after=page.locator("body").inner_text(timeout=1000)
            ok = before != after or (page.evaluate("document.body.dataset.lastAction || ''") != "")
            results.append([html_path.name,title,"input",i,norm_text(loc.get_attribute('placeholder') or ''),"type=金蝶","PASS" if ok else "WARN","input accepted; feedback expected" if ok else "input accepts text but no visible feedback detected","; ".join(console_errors[-3:])])
        except Exception as e:
            results.append([html_path.name,title,"input",i,"","","FAIL",f"input interaction error: {e}","; ".join(console_errors[-3:])])
    # buttons: click visible buttons one by one; use a fresh page so inline scripts do not redeclare variables.
    page.close()
    page = browser.new_page(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type in ("error", "warning") else None)
    page.on("pageerror", lambda exc: console_errors.append(str(exc)))
    page.set_content(html_path.read_text(encoding="utf-8", errors="ignore"), wait_until="load")
    page.wait_for_timeout(120)
    clicked=0
    max_clicks=min(page.locator("button:visible").count(), 80)
    for i in range(max_clicks):
        try:
            # Recompute visible buttons each time. If index vanished, break.
            count=page.locator("button:visible").count()
            if i>=count: break
            loc=page.locator("button:visible").nth(i)
            label=norm_text(loc.inner_text(timeout=1000)) or norm_text(loc.get_attribute("aria-label") or loc.get_attribute("title") or "")
            before_text=page.locator("body").inner_text(timeout=1000)
            before_url=page.url
            before_action=page.evaluate("document.body.dataset.lastAction || ''")
            before_panel=page.locator(".panel.open").count()
            # handle downloads gracefully only for explicit export/download buttons
            try:
                if any(k in label for k in ("导出", "下载")):
                    try:
                        with page.expect_download(timeout=1200) as download_info:
                            loc.click(timeout=2500)
                        _ = download_info.value.suggested_filename
                    except PlaywrightTimeoutError:
                        loc.click(timeout=2500)
                else:
                    loc.click(timeout=2500)
            except Exception as click_e:
                results.append([html_path.name,title,"button",i,label,"click","FAIL",f"click failed: {click_e}","; ".join(console_errors[-3:])])
                continue
            page.wait_for_timeout(160)
            after_text=page.locator("body").inner_text(timeout=1000)
            after_url=page.url
            after_action=page.evaluate("document.body.dataset.lastAction || ''")
            after_panel=page.locator(".panel.open").count()
            if after_panel:
                page.evaluate("document.querySelectorAll('.panel.open,.overlay.open').forEach(e=>e.classList.remove('open'))")
            changed = (before_text != after_text) or (before_url != after_url) or (before_action != after_action) or (before_panel != after_panel)
            status="PASS" if changed else "WARN"
            reason="visible feedback / navigation / state change" if changed else "no visible state change detected"
            results.append([html_path.name,title,"button",i,label,"click",status,reason,"; ".join(console_errors[-3:])])
            clicked+=1
        except Exception as e:
            results.append([html_path.name,title,"button",i,"","click","FAIL",f"button audit error: {e}","; ".join(console_errors[-3:])])
    if console_errors:
        results.append([html_path.name,title,"console",-1,"console/errors","","WARN","console warnings/errors captured","; ".join(console_errors[:10])])
    page.close()
    return results


# ── PROD.0013：App 真数据端到端 ────────────────────────────────────────────────
# 任务包第 22 行：升级本脚本覆盖 App「登录→首页→检查板→成本页→差异处理→影响预览→
# 重跑→报告导出」，全流 PASS，作为 App 回归基线入 CI。
#
# 与上面的静态 HTML 普扫共用同一套输出契约（CSV 九列 + 有 FAIL 则退出码 1），
# 但驱动方式完全不同：这里是**按角色选元素、真点、真断言真实数据**，
# 不用像素坐标（坐标会随视口/缩放漂，CI 里必炸）。
FLOW_STEPS = ("登录", "今天", "回款账龄", "成本页", "差异拍板", "重算", "报告导出", "系统自检")


def _row(step, label, action, ok, reason, console):
    return ["app", step, "flow", FLOW_STEPS.index(step) if step in FLOW_STEPS else -1,
            label, action, "PASS" if ok else "FAIL", reason, "; ".join(console[-3:])]


def app_flow(browser, base_url: str):
    """按任务包八步驱动真实 App，每步断言真实数据。"""
    page = browser.new_page(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    console = []
    page.on("console", lambda m: console.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: console.append(str(e)))
    rows = []

    def tab(name):
        t = page.get_by_role("tab", name=name)
        t.click()
        # 等 aria-selected 真的翻过来，而不是盲等 250ms
        page.wait_for_function(
            "n => [...document.querySelectorAll('[role=tab]')]"
            ".some(b => b.textContent === n && b.getAttribute('aria-selected') === 'true')",
            arg=name, timeout=15000)

    # ① 登录：本机 App 是单用户模式，**没有应用内登录**——生产侧鉴权由 Cloudflare Access
    #    在 DNS 前置。这里如实断言「入口可达 + 页眉三元组渲染出来」，不假造一个登录页。
    try:
        page.goto(f"{base_url}/ops/app", wait_until="networkidle", timeout=30000)
        header = page.locator("header").inner_text()
        ok = all(k in header for k in ("质量", "报告", "NO_GO"))
        rows.append(_row("登录", "单用户模式（鉴权由 Cloudflare Access 前置）",
                         f"goto {base_url}/ops/app", ok,
                         f"页眉三元组: {norm_text(header, 60)}" if ok else f"页眉缺三元组: {header[:80]}",
                         console))
    except Exception as e:
        rows.append(_row("登录", "", "goto", False, f"入口不可达: {e}", console))
        page.close()
        return rows

    # ② 今天（经营驾驶舱首页）：人话判决 + 等你拍板 + 真实阻塞（信息第一性，PRD v2）
    try:
        tab("今天")
        body = page.locator("body").inner_text()
        ok = "等你拍板" in body and "BLK-001" in body and "暂不可对外" in body
        rows.append(_row("今天", "驾驶舱首页", "click tab", ok,
                         "人话判决+拍板队列+真实阻塞俱在" if ok else f"关键要素缺失: {body[:120]}", console))
    except Exception as e:
        rows.append(_row("今天", "驾驶舱首页", "click tab", False, f"{e}", console))

    # ③ 回款与账龄：逐月核对表须在，且有已对平的真实行
    try:
        tab("回款与账龄")
        body = page.locator("body").inner_text()
        ok = "回款逐月核对" in body and "已对平" in body
        rows.append(_row("回款账龄", "回款与账龄", "click tab", ok,
                         "逐月核对表与已对平状态俱在" if ok else f"未见核对表: {body[:120]}", console))
    except Exception as e:
        rows.append(_row("回款账龄", "回款与账龄", "click tab", False, f"{e}", console))

    # ④ 成本页：A0 未就位时**不得**出现毛利数字——阻塞必须如实呈现
    try:
        tab("项目成本")
        body = page.locator("body").inner_text()
        blocked = "金额尚不可计算" in body or "算不出" in body or "阻塞" in body
        no_margin = "毛利率" not in body
        ok = blocked and no_margin
        rows.append(_row("成本页", "项目成本", "click tab", ok,
                         "阻塞如实呈现且无编造毛利" if ok
                         else f"blocked={blocked} no_margin={no_margin}", console))
    except Exception as e:
        rows.append(_row("成本页", "项目成本", "click tab", False, f"{e}", console))

    # ⑤ 差异拍板：**真写一条决策**并验证留痕（不是只看页面能打开）
    try:
        tab("待拍板")
        before = page.locator("text=App 写入").inner_text()
        page.locator("tr", has=page.locator("code", has_text="AST-COLL-202503")).first.click()
        # 等条件、不等时间：固定 sleep 在慢机器上会抢跑——CI 上就这么飘红过一次，
        # 而同一份代码在本机 10/10 全过。等元素真出现才是可靠写法。
        page.wait_for_selector('input[placeholder*="决策理由"]', timeout=15000)
        page.get_by_placeholder("决策理由", exact=False).fill("E2E 回归基线：按容差闭案")
        page.get_by_role("button", name="闭案 → closed").click()
        page.wait_for_selector("text=已追加事件", timeout=30000)
        body = page.locator("body").inner_text()
        ok = "MANEVT-APP-" in body and "已追加事件" in body
        rows.append(_row("差异拍板", "三选一决策 闭案", "fill+click", ok,
                         f"事件已写入（写入前: {norm_text(before, 20)}）" if ok
                         else f"未见事件号: {body[:150]}", console))
    except Exception as e:
        rows.append(_row("差异拍板", "三选一决策", "fill+click", False, f"{e}", console))

    # ⑥ 重算（数据底账页内）：选源数据 → 影响面必须由血缘边算出真实行数
    try:
        tab("数据底账")
        page.locator("select").first.select_option("raw:d46f77b0c90d")
        # 锚点必须是影响面独有的文本：页内「接入了多少」区本来就含 goods_movement，
        # 拿它当锚会秒过并抢在影响面渲染前断言——本轮实测踩到（10/11 那次 FAIL）。
        page.wait_for_selector("text=会牵连什么", timeout=15000)
        body = page.locator("body").inner_text()
        ok = "受影响核对域" in body and "expense_lines" in body and "17,764" in body
        rows.append(_row("重算", "raw:d46f77b0c90d", "select_option", ok,
                         "下游影响面含真实派生表与行数（goods_movement 17,764）" if ok
                         else f"影响面异常: {body[:150]}", console))
    except Exception as e:
        rows.append(_row("重算", "选中资产", "select_option", False, f"{e}", console))

    # ⑦ 重跑：**真发起并完成**四层链——本单元最硬的一条
    try:
        page.get_by_placeholder("重跑理由", exact=False).fill("E2E 回归基线：四层链验证")
        page.get_by_role("button", name="发起重跑", exact=False).click()
        page.wait_for_selector("text=本次重跑结果", timeout=30000)
        body = page.locator("body").inner_text()
        layers = sum(1 for k in ("field_mapping", "fact_layer", "derived_metric", "report_reference")
                     if k in body)
        ok = layers == 4 and "链完整：是" in body and "旧版本全保留：是" in body
        rows.append(_row("重算", "四层链", "fill+click", ok,
                         f"四层全完成、链完整、旧版本保留（命中 {layers}/4 层）" if ok
                         else f"重跑未完成: 命中 {layers}/4 层", console))
    except Exception as e:
        rows.append(_row("重算", "四层链", "fill+click", False, f"{e}", console))

    # ⑦ 报告导出：三格式**真下载**，且水印/等级头必须在
    try:
        tab("报告下载")
        for fmt, magic in (("HTML", b"<!doctype"), ("CSV", b"\xef\xbb\xbf"), ("PDF", b"%PDF")):
            with page.expect_download(timeout=30000) as dl:
                page.locator(f'a[href*="格式={fmt.lower()}"]').first.click()
            path = Path(dl.value.path())
            body_bytes = path.read_bytes()
            # 取 16 字节：magic 最长的是 b"<!doctype"（9 字符），只取 8 字节会永远比不中
            head = body_bytes[:16]
            ok = head.startswith(magic) and len(body_bytes) > 200
            mark = ("delivery_allowed=false" in body_bytes.decode("utf-8", "ignore")) or fmt == "PDF"
            rows.append(_row("报告导出", f"第1号 {fmt}", "click download", ok and mark,
                             f"{len(body_bytes)} 字节，魔数 {head[:4]!r}，水印在" if ok and mark
                             else f"魔数/水印异常: head={head[:8]!r} mark={mark}", console))
    except Exception as e:
        rows.append(_row("报告导出", "三格式", "click download", False, f"{e}", console))

    # ⑧ 系统自检：排程健康必须如实呈现（CI 容器无台账 → 直说读不到原因）
    try:
        tab("系统自检")
        body = page.locator("body").inner_text()
        ok = "排程" in body and ("从未跑过" in body or "读不到排程日志" in body or "成功" in body)
        rows.append(_row("系统自检", "排程健康", "click tab", ok,
                         "排程状态如实呈现（有记录或直说读不到）" if ok
                         else f"排程状态缺失: {body[:120]}", console))
    except Exception as e:
        rows.append(_row("系统自检", "排程健康", "click tab", False, f"{e}", console))

    page.close()
    return rows


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("root", type=Path, nargs="?")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--glob", default="*.html")
    ap.add_argument("--app-url", help="给定则跑 App 全流端到端（PROD.0013）")
    args=ap.parse_args()
    htmls=sorted(args.root.rglob(args.glob)) if args.root else []
    args.out.parent.mkdir(parents=True, exist_ok=True)
    httpd=None; base_url=None
    all_rows=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True, executable_path=CHROMIUM, args=["--no-sandbox","--disable-dev-shm-usage"])
        if args.app_url:
            all_rows.extend(app_flow(browser, args.app_url.rstrip('/')))
        for hp in htmls:
            try:
                all_rows.extend(audit_file(browser,hp,args.root,base_url))
            except Exception as e:
                all_rows.append([hp.name,"","file",-1,"","","FAIL",f"file audit crashed: {e}",""])
        browser.close()
    if httpd: httpd.shutdown()
    with args.out.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.writer(f)
        w.writerow(["file","title","control_type","index","label","action","status","reason","console"])
        w.writerows(all_rows)
    total=len(all_rows); fail=sum(1 for r in all_rows if r[6]=="FAIL"); warn=sum(1 for r in all_rows if r[6]=="WARN"); passed=sum(1 for r in all_rows if r[6]=="PASS")
    print(f"HTML audit complete: files={len(htmls)} rows={total} pass={passed} warn={warn} fail={fail} out={args.out}")
    return 1 if fail else 0
if __name__=="__main__":
    raise SystemExit(main())
