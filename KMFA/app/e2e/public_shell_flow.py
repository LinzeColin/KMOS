#!/usr/bin/env python3
"""S03/P3.2 public App Shell browser oracle.

Exercises desktop, mobile, JavaScript-disabled, and shallow-health-degraded modes.
Artifacts contain only the public shell DOM/screenshots/traces and belong in a CI or /tmp
directory, never in the repository evidence tree.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Browser, Page, sync_playwright

ENTRY_KEYS = ("project", "upload", "search", "progress", "report", "help")
PRIVATE_PREFIXES = ("/api", "/ops")


def _is_private_request(url: str) -> bool:
    path = urlsplit(url).path
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in PRIVATE_PREFIXES)


def _write_dom(page: Page, path: Path) -> None:
    path.write_text(page.content(), encoding="utf-8")


def _exercise_entries(page: Page) -> None:
    entries = page.locator("[data-shell-entry]")
    assert entries.count() == 6, f"expected six shell entries, got {entries.count()}"
    assert entries.evaluate_all("nodes => nodes.map(node => node.dataset.shellEntry)") == list(ENTRY_KEYS)

    for key in ENTRY_KEYS:
        page.locator(f'[data-shell-entry="{key}"]').click()
        page.locator(f'[data-active-module="{key}"]').wait_for(state="visible")
        assert urlsplit(page.url).fragment == key
        assert page.locator(f'[data-shell-entry="{key}"]').get_attribute("aria-pressed") == "true"


def _assert_public_network(requests: list[str], statuses: list[int]) -> None:
    private = [url for url in requests if _is_private_request(url)]
    assert not private, f"public shell requested private plane: {private}"
    private_bundles = [url for url in requests if "/assets/App-" in urlsplit(url).path]
    assert not private_bundles, f"public shell loaded private dashboard bundle: {private_bundles}"
    assert not ({401, 403} & set(statuses)), f"anonymous shell saw permission response: {statuses}"


def _run_interactive(
    browser: Browser,
    base_url: str,
    out_dir: Path,
    name: str,
    viewport: dict[str, int],
) -> dict[str, object]:
    context = browser.new_context(viewport=viewport, locale="zh-CN")
    context.tracing.start(screenshots=True, snapshots=True, sources=False)
    page = context.new_page()
    requests: list[str] = []
    statuses: list[int] = []
    console_errors: list[str] = []
    page_errors: list[str] = []
    page.on("request", lambda request: requests.append(request.url))
    page.on("response", lambda response: statuses.append(response.status))
    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    try:
        response = page.goto(f"{base_url}/", wait_until="networkidle", timeout=30_000)
        assert response and response.status == 200
        page.locator('[data-shell-ready="true"]').wait_for()
        page.locator('[data-system-state="online"]').wait_for(timeout=10_000)
        _exercise_entries(page)

        assert page.locator('input[type="password"], input[type="email"]').count() == 0
        control_labels = page.locator("a, button").all_inner_texts()
        assert not any(token in label for label in control_labels for token in ("登录", "注册", "OAuth"))
        body_text = page.locator("body").inner_text()
        assert not any(marker in body_text for marker in ("BLK-001", "NO_GO", "质量 Q3", "回款账龄"))

        page.locator('[data-shell-entry="search"]').click()
        search = page.locator('[data-public-search="true"]')
        search.fill("上传")
        results = page.locator('[data-search-results="true"]')
        results.wait_for()
        assert "上传" in results.inner_text()
        assert "仅本页六项公开说明" in page.locator("#module-detail").inner_text()

        if viewport["width"] <= 480:
            overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            assert overflow <= 1, f"mobile horizontal overflow: {overflow}px"

        _assert_public_network(requests, statuses)
        assert not console_errors, f"public shell console errors: {console_errors}"
        assert not page_errors, f"public shell page errors: {page_errors}"
        page.evaluate("window.scrollTo(0, 0)")
        page.screenshot(path=out_dir / f"{name}.png", full_page=True)
        _write_dom(page, out_dir / f"{name}.html")
        return {
            "name": name,
            "viewport": viewport,
            "entries": list(ENTRY_KEYS),
            "system_state": "online",
            "private_requests": 0,
            "permission_errors": 0,
            "runtime_errors": 0,
            "status": "PASS",
        }
    finally:
        context.tracing.stop(path=out_dir / f"{name}.trace.zip")
        context.close()


def _run_no_javascript(browser: Browser, base_url: str, out_dir: Path) -> dict[str, object]:
    context = browser.new_context(
        java_script_enabled=False,
        viewport={"width": 1280, "height": 900},
        locale="zh-CN",
    )
    page = context.new_page()
    page_errors: list[str] = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    try:
        response = page.goto(f"{base_url}/", wait_until="load", timeout=30_000)
        assert response and response.status == 200
        entries = page.locator("[data-static-shell-entry]")
        assert entries.count() == 6
        assert entries.evaluate_all("nodes => nodes.map(node => node.dataset.staticShellEntry)") == list(ENTRY_KEYS)
        no_js = page.locator('[data-no-js-state="visible"]')
        assert no_js.is_visible()
        assert "JavaScript 已停用" in no_js.inner_text()
        assert "静态公共入口已就绪" in page.locator("#static-runtime-status").inner_text()
        assert page.locator('input[type="password"], input[type="email"]').count() == 0
        assert not page_errors
        page.screenshot(path=out_dir / "no-javascript.png", full_page=True)
        _write_dom(page, out_dir / "no-javascript.html")
        return {"name": "no-javascript", "entries": 6, "explicit_state": True, "status": "PASS"}
    finally:
        context.close()


def _run_degraded(browser: Browser, base_url: str, out_dir: Path) -> dict[str, object]:
    context = browser.new_context(viewport={"width": 1280, "height": 900}, locale="zh-CN")
    context.tracing.start(screenshots=True, snapshots=True, sources=False)
    page = context.new_page()
    requests: list[str] = []
    statuses: list[int] = []
    page_errors: list[str] = []
    page.on("request", lambda request: requests.append(request.url))
    page.on("response", lambda response: statuses.append(response.status))
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.route(
        "**/healthz",
        lambda route: route.fulfill(
            status=503,
            content_type="application/json",
            body='{"status":"unavailable"}',
        ),
    )
    try:
        response = page.goto(f"{base_url}/", wait_until="networkidle", timeout=30_000)
        assert response and response.status == 200
        page.locator('[data-system-state="degraded"]').wait_for(timeout=10_000)
        assert "基础服务暂不可确认" in page.locator("#system-status").inner_text()
        assert "导航与公开说明仍可使用" in page.locator("#system-status").inner_text()
        _exercise_entries(page)
        _assert_public_network(requests, statuses)
        assert not page_errors, f"degraded shell page errors: {page_errors}"
        page.evaluate("window.scrollTo(0, 0)")
        page.screenshot(path=out_dir / "degraded.png", full_page=True)
        _write_dom(page, out_dir / "degraded.html")
        return {"name": "degraded", "entries": 6, "explicit_state": True, "status": "PASS"}
    finally:
        context.tracing.stop(path=out_dir / "degraded.trace.zip")
        context.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    base_url = args.base_url.rstrip("/")

    results: list[dict[str, object]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            results.append(_run_interactive(browser, base_url, args.out_dir, "desktop", {"width": 1440, "height": 1000}))
            results.append(_run_interactive(browser, base_url, args.out_dir, "mobile", {"width": 390, "height": 844}))
            results.append(_run_no_javascript(browser, base_url, args.out_dir))
            results.append(_run_degraded(browser, base_url, args.out_dir))
        finally:
            browser.close()

    summary = {"contract": "S03/P3.2", "base_url": base_url, "results": results, "status": "PASS"}
    (args.out_dir / "result.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
