#!/usr/bin/env python3
"""TEST-PUB-005: three-engine accessibility and public-index boundary oracle.

Artifacts contain only the intentionally public homepage, synthetic canary
paths and aggregate accessibility results. No private response body is saved.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree

from playwright.sync_api import Browser, Page, Playwright, sync_playwright

AXE_TAGS = ("wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa")
ENGINES = ("chromium", "firefox", "webkit")
ENTRY_KEYS = ("project", "upload", "search", "progress", "report", "help")
ENTRY_NAMES = ("项目", "上传", "搜索", "进度", "报告", "帮助")
CANONICAL_ROOT = "https://kmfa.linzezhang.com/"
UNPUBLISHED_CANARY = "/unpublished/__kmfa_publication_canary__/private-file"
NO_INDEX = "noindex, nofollow, noarchive"


def _goto_home(page: Page, base_url: str) -> None:
    response = page.goto(f"{base_url}/", wait_until="networkidle", timeout=30_000)
    assert response and response.status == 200
    page.locator('[data-shell-ready="true"]').wait_for(timeout=10_000)
    page.locator('[data-system-state="online"]').wait_for(timeout=10_000)


def _trim_axe_rule(rule: dict[str, object]) -> dict[str, object]:
    nodes = []
    for node in rule.get("nodes", []):
        nodes.append(
            {
                "impact": node.get("impact"),
                "target": node.get("target"),
                "html": str(node.get("html", ""))[:500],
                "failure_summary": node.get("failureSummary"),
            }
        )
    return {
        "id": rule.get("id"),
        "impact": rule.get("impact"),
        "help": rule.get("help"),
        "help_url": rule.get("helpUrl"),
        "nodes": nodes,
    }


def _run_axe(page: Page, axe_script: Path, label: str) -> dict[str, object]:
    if not page.evaluate("() => typeof window.axe !== 'undefined'"):
        page.add_script_tag(path=str(axe_script))
    result = page.evaluate(
        """async (tags) => {
          const result = await window.axe.run(document, {
            runOnly: {type: 'tag', values: tags},
            resultTypes: ['violations', 'incomplete']
          });
          return {
            testEngine: result.testEngine,
            testEnvironment: result.testEnvironment,
            violations: result.violations,
            incomplete: result.incomplete
          };
        }""",
        list(AXE_TAGS),
    )
    violations = [_trim_axe_rule(rule) for rule in result["violations"]]
    incomplete = [_trim_axe_rule(rule) for rule in result["incomplete"]]
    severe = [rule for rule in violations if rule["impact"] in {"critical", "serious"}]
    severe_incomplete = [
        rule for rule in incomplete if rule["impact"] in {"critical", "serious"}
    ]
    assert not severe, f"{label}: critical/serious axe violations: {severe}"
    assert not severe_incomplete, (
        f"{label}: unresolved critical/serious axe checks: {severe_incomplete}"
    )
    return {
        "label": label,
        "engine": result["testEngine"],
        "environment": result["testEnvironment"],
        "critical_serious": 0,
        "violation_count": len(violations),
        "incomplete_count": len(incomplete),
        "violations": violations,
        "incomplete": incomplete,
    }


def _screen_reader_contract(page: Page) -> dict[str, object]:
    assert page.locator("html").get_attribute("lang") == "zh-CN"
    assert page.get_by_role("banner").count() == 1
    assert page.get_by_role("navigation", name="主要功能").count() == 1
    assert page.get_by_role("main").count() == 1
    assert page.get_by_role("contentinfo").count() == 1
    assert (
        page.get_by_role(
            "heading",
            name="一个入口，通往项目、文件与可验证进度。",
            exact=True,
        ).count()
        == 1
    )
    assert page.get_by_role("status").count() == 1
    assert page.get_by_role("link", name=re.compile(r"^系统状态：")).count() == 1

    card_names = []
    for name in ENTRY_NAMES:
        control = page.get_by_role("button", name=re.compile(rf"^{name}："))
        assert control.count() == 1
        card_names.append(control.get_attribute("aria-label"))

    page.get_by_role("button", name=re.compile(r"^搜索：")).click()
    assert page.get_by_role("search").count() == 1
    assert page.get_by_label("搜索本页公开说明", exact=True).count() == 1
    return {
        "language": "zh-CN",
        "landmarks": ["banner", "navigation:主要功能", "main", "contentinfo"],
        "primary_heading": "一个入口，通往项目、文件与可验证进度。",
        "live_status": True,
        "search_label": "搜索本页公开说明",
        "card_accessible_names": card_names,
        "status": "PASS",
    }


def _keyboard_contract(
    page: Page,
    base_url: str,
    engine: str,
) -> dict[str, object]:
    # macOS Safari/WebKit may require Option+Tab for full-page link traversal
    # when the OS "Press Tab to highlight each item" preference is off. Linux
    # WebKit uses ordinary Tab, so detect the real behavior instead of assuming.
    tab_key = "Tab"
    _goto_home(page, base_url)
    page.keyboard.press(tab_key)
    focused = page.evaluate(
        """() => ({
          className: document.activeElement.className,
          text: document.activeElement.textContent.trim(),
          rect: document.activeElement.getBoundingClientRect().toJSON()
        })"""
    )
    if focused["className"] != "public-skip-link" and engine == "webkit":
        tab_key = "Alt+Tab"
        _goto_home(page, base_url)
        page.keyboard.press(tab_key)
        focused = page.evaluate(
            """() => ({
              className: document.activeElement.className,
              text: document.activeElement.textContent.trim(),
              rect: document.activeElement.getBoundingClientRect().toJSON()
            })"""
        )
    assert focused["className"] == "public-skip-link"
    assert focused["text"] == "跳到主要内容"
    assert focused["rect"]["width"] > 1 and focused["rect"]["height"] > 1
    page.keyboard.press("Enter")
    page.wait_for_timeout(100)
    assert page.evaluate("() => document.activeElement.id") == "main-content"

    _goto_home(page, base_url)
    seen: list[str] = []
    focus_sequence: list[dict[str, str | None]] = []
    for _ in range(40):
        page.keyboard.press(tab_key)
        item = page.evaluate(
            r"""() => ({
              tag: document.activeElement.tagName,
              name: document.activeElement.getAttribute('aria-label')
                || document.activeElement.textContent.trim().replace(/\s+/g, ' '),
              entry: document.activeElement.dataset.shellEntry || null
            })"""
        )
        focus_sequence.append(item)
        key = item["entry"]
        if key and key not in seen:
            page.keyboard.press("Enter")
            page.wait_for_function(
                "(expected) => document.querySelector('#module-detail')"
                "?.dataset.activeModule === expected",
                arg=key,
            )
            seen.append(key)
        if len(seen) == len(ENTRY_KEYS):
            break
    assert seen == list(ENTRY_KEYS), f"keyboard card order mismatch: {seen}"
    return {
        "skip_link_visible_on_focus": True,
        "skip_target": "main-content",
        "forward_focus_key": "Option+Tab" if tab_key == "Alt+Tab" else "Tab",
        "operated_entries": seen,
        "tab_stops_observed": len(focus_sequence),
        "status": "PASS",
    }


def _responsive_contract(
    page: Page,
    base_url: str,
    out_dir: Path,
    engine: str,
    viewport: dict[str, int],
) -> dict[str, object]:
    page.set_viewport_size(viewport)
    _goto_home(page, base_url)
    overflow = page.evaluate(
        "() => document.documentElement.scrollWidth - window.innerWidth"
    )
    assert overflow <= 1, f"{engine} {viewport['width']}px overflow: {overflow}"
    cards = page.locator("[data-shell-entry]").evaluate_all(
        """nodes => nodes.map(node => {
          const r = node.getBoundingClientRect();
          return {key: node.dataset.shellEntry, x: r.x, width: r.width, height: r.height};
        })"""
    )
    assert [card["key"] for card in cards] == list(ENTRY_KEYS)
    for card in cards:
        assert card["x"] >= -1
        assert card["x"] + card["width"] <= viewport["width"] + 1
        assert card["width"] >= 24 and card["height"] >= 24
    shot = f"{engine}-{viewport['width']}x{viewport['height']}.png"
    page.screenshot(path=out_dir / shot, full_page=True)
    return {
        "viewport": viewport,
        "document_overflow_px": overflow,
        "entries_inside_viewport": len(cards),
        "minimum_target_px": 24,
        "screenshot": shot,
        "status": "PASS",
    }


def _run_browser(
    playwright: Playwright,
    engine: str,
    base_url: str,
    axe_script: Path,
    out_dir: Path,
) -> dict[str, object]:
    browser: Browser = getattr(playwright, engine).launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1440, "height": 1000},
        locale="zh-CN",
        reduced_motion="reduce",
    )
    page = context.new_page()
    try:
        _goto_home(page, base_url)
        labels = _screen_reader_contract(page)
        axe_runs = []
        for key in ENTRY_KEYS:
            # Reload each state so axe never reuses a browser style snapshot
            # from the previously selected card (observed in WebKit).
            response = page.goto(
                f"{base_url}/?test-pub-005-state={key}#{key}",
                wait_until="networkidle",
                timeout=30_000,
            )
            assert response and response.status == 200
            page.locator('[data-shell-ready="true"]').wait_for(timeout=10_000)
            page.locator('[data-system-state="online"]').wait_for(timeout=10_000)
            page.locator(f'[data-active-module="{key}"]').wait_for()
            page.wait_for_function(
                "(expected) => [...document.querySelectorAll('[data-shell-entry]')]"
                ".every(node => (node.getAttribute('aria-pressed') === 'true')"
                " === (node.dataset.shellEntry === expected))",
                arg=key,
            )
            # Flush computed styles before axe samples contrast across engines.
            page.wait_for_timeout(50)
            if key == "search":
                page.locator('[data-public-search="true"]').fill("上传")
                page.locator('[data-search-results="true"]').wait_for()
            axe_runs.append(_run_axe(page, axe_script, f"{engine}:desktop:{key}"))
        page.screenshot(path=out_dir / f"{engine}-desktop.png", full_page=True)

        keyboard = _keyboard_contract(page, base_url, engine)
        mobile = _responsive_contract(
            page,
            base_url,
            out_dir,
            engine,
            {"width": 390, "height": 844},
        )
        axe_runs.append(_run_axe(page, axe_script, f"{engine}:mobile:390"))

        compact = None
        if engine == "chromium":
            compact = _responsive_contract(
                page,
                base_url,
                out_dir,
                engine,
                {"width": 320, "height": 700},
            )
            axe_runs.append(_run_axe(page, axe_script, "chromium:mobile:320"))

        return {
            "engine": engine,
            "browser_version": browser.version,
            "screen_reader_contract": labels,
            "keyboard_contract": keyboard,
            "responsive_390": mobile,
            "responsive_320": compact,
            "axe_runs": axe_runs,
            "critical_serious": sum(int(run["critical_serious"]) for run in axe_runs),
            "status": "PASS",
        }
    finally:
        context.close()
        browser.close()


def _robot_pattern_matches(pattern: str, path: str) -> bool:
    end_anchored = pattern.endswith("$")
    raw = pattern[:-1] if end_anchored else pattern
    regex = re.escape(raw).replace(r"\*", ".*")
    suffix = "$" if end_anchored else ""
    return re.match(f"^{regex}{suffix}", path) is not None


def _robots_allows(body: str, path: str) -> bool:
    active = False
    rules: list[tuple[int, bool]] = []
    for raw_line in body.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, value = (part.strip() for part in line.split(":", 1))
        field = field.lower()
        if field == "user-agent":
            active = value == "*"
        elif active and field in {"allow", "disallow"} and value:
            if _robot_pattern_matches(value, path):
                effective_length = len(value.rstrip("$").replace("*", ""))
                rules.append((effective_length, field == "allow"))
    if not rules:
        return True
    longest = max(length for length, _ in rules)
    return any(allowed for length, allowed in rules if length == longest)


def _crawler_contract(playwright: Playwright, base_url: str) -> dict[str, object]:
    request = playwright.request.new_context(
        base_url=base_url,
        extra_http_headers={
            "User-Agent": "KMFA-TEST-PUB-005-Crawler/1.0",
            "Accept": "text/html,application/xml,text/plain",
        },
    )
    try:
        root = request.get("/", max_redirects=0)
        root_headers = {key.lower(): value for key, value in root.headers.items()}
        root_html = root.text()
        assert root.status == 200
        assert root_headers["x-kmfa-index-mode"] == "public-root"
        assert "noindex" not in root_headers.get("x-robots-tag", "")
        assert '<link rel="canonical" href="https://kmfa.linzezhang.com/">' in root_html
        assert '<meta name="robots" content="index,follow,max-snippet:-1">' in root_html

        robots_response = request.get("/robots.txt", max_redirects=0)
        robots = robots_response.text()
        assert robots_response.status == 200
        assert _robots_allows(robots, "/")
        assert _robots_allows(robots, "/assets/app-hash.js")
        assert _robots_allows(robots, "/robots.txt")
        assert _robots_allows(robots, "/sitemap.xml")
        for denied in (
            "/api",
            "/ops/app",
            "/ui",
            "/healthz",
            UNPUBLISHED_CANARY,
        ):
            assert not _robots_allows(robots, denied), denied

        sitemap_response = request.get("/sitemap.xml", max_redirects=0)
        sitemap = sitemap_response.text()
        assert sitemap_response.status == 200
        root_element = ElementTree.fromstring(sitemap)
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locations = [
            node.text for node in root_element.findall("sm:url/sm:loc", namespace)
        ]
        assert locations == [CANONICAL_ROOT]

        response_checks = {}
        for path, expected_status in (
            (UNPUBLISHED_CANARY, 404),
            ("/ops/app", 200),
            ("/ui/unpublished", 308),
            ("/healthz", 200),
        ):
            response = request.get(path, max_redirects=0)
            headers = {key.lower(): value for key, value in response.headers.items()}
            assert response.status == expected_status
            assert headers.get("x-robots-tag") == NO_INDEX
            assert headers.get("cache-control") == "private, no-store"
            response_checks[path] = {
                "status": response.status,
                "x_robots_tag": headers.get("x-robots-tag"),
                "cache_control": headers.get("cache-control"),
                "body_persisted": False,
            }

        canary = response_checks[UNPUBLISHED_CANARY]
        canary_signals = {
            "in_sitemap": UNPUBLISHED_CANARY in sitemap,
            "allowed_by_robots": _robots_allows(robots, UNPUBLISHED_CANARY),
            "successful_response": canary["status"] == 200,
            "noindex_header": "noindex" in str(canary["x_robots_tag"]),
            "cacheable": "no-store" not in str(canary["cache_control"]),
        }
        index_hits = int(
            canary_signals["in_sitemap"]
            or canary_signals["allowed_by_robots"]
            or canary_signals["successful_response"]
            or not canary_signals["noindex_header"]
            or canary_signals["cacheable"]
        )
        assert index_hits == 0
        return {
            "mode": "public-root",
            "robots": robots,
            "sitemap_locations": locations,
            "allowed_paths": [
                "/",
                "/assets/app-hash.js",
                "/robots.txt",
                "/sitemap.xml",
            ],
            "denied_paths": [
                "/api",
                "/ops/app",
                "/ui",
                "/healthz",
                UNPUBLISHED_CANARY,
            ],
            "response_checks": response_checks,
            "unpublished_canary": canary_signals,
            "local_index_candidate_hits": index_hits,
            "private_response_bodies_persisted": 0,
            "status": "PASS",
        }
    finally:
        request.dispose()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument(
        "--axe-script",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "frontend"
        / "node_modules"
        / "axe-core"
        / "axe.min.js",
    )
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    assert args.axe_script.is_file(), f"axe-core script missing: {args.axe_script}"
    base_url = args.base_url.rstrip("/")
    parsed = urlsplit(base_url)
    assert parsed.scheme in {"http", "https"} and parsed.netloc

    with sync_playwright() as playwright:
        crawler = _crawler_contract(playwright, base_url)
        browsers = [
            _run_browser(
                playwright,
                engine,
                base_url,
                args.axe_script,
                args.out_dir,
            )
            for engine in ENGINES
        ]

    result = {
        "contract": "S03/P3.3 TEST-PUB-005",
        "base_url": base_url,
        "wcag_tags": list(AXE_TAGS),
        "browser_results": browsers,
        "crawler_boundary": crawler,
        "critical_serious_a11y": sum(
            int(browser["critical_serious"]) for browser in browsers
        ),
        "unpublished_canary_index_hits": crawler["local_index_candidate_hits"],
        "status": "PASS",
    }
    (args.out_dir / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "contract": result["contract"],
                "engines": [browser["engine"] for browser in browsers],
                "critical_serious_a11y": result["critical_serious_a11y"],
                "unpublished_canary_index_hits": result[
                    "unpublished_canary_index_hits"
                ],
                "status": result["status"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
