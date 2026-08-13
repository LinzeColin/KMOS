#!/usr/bin/env python3
"""T09 每日资金私有投影的真浏览器 Oracle。

这不是接口字符串检查：脚本启动当前 FastAPI 与当前已构建的 React 资产，使用
Playwright 真的打开 ``/ops/app?tab=每日资金``。全部输入均为本文件生成的合成
projection，产物只写入调用方给出的临时目录；它不能也不会读取 DWS、Git、D1、R2、
OCI 或任何原始附件。

覆盖的浏览器可见契约：三个人类状态、30 天默认范围、键盘范围切换、自定义区间、
SVG 趋势图/图例/tooltip、移动端无横向溢出，以及已验证投影不得泄露原始字段。
生产 Access 边界另由后端访问控制测试覆盖；本 Oracle 明确只在临时本地进程中关闭
该边界，以验证已受保护页面本身的渲染行为。
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import Browser, Error as PlaywrightError, Page, TimeoutError as PlaywrightTimeout, sync_playwright


REPO = Path(__file__).resolve().parents[3]
BACKEND = REPO / "KMFA" / "app" / "backend"
RAW_SENTINEL = "RAW_DWS_FIXTURE_MUST_NEVER_ESCAPE"
DAILY_PATHS = (
    "/ops/api/daily-funds/summary?range=30d",
    "/ops/api/daily-funds/timeseries?range=30d",
    "/ops/api/daily-funds/cashflow-observations?range=30d",
    "/ops/api/daily-funds/source-health",
    "/ops/api/daily-funds/thresholds",
    "/ops/api/daily-funds/auth-session",
    "/ops/api/daily-funds/history-probe",
)
STATUS_SCHEDULES = {
    "history_poll": "*/15 * * * * Asia/Shanghai",
    "auth_probe": "* * * * * Asia/Shanghai",
    "keepalive": "0 * * * * Asia/Shanghai",
    "backfill": "5,20,35,50 * * * * Asia/Shanghai",
    "observer": "30 3 * * * Asia/Shanghai",
    "r2_guard": "0 */6 * * * Asia/Shanghai",
    "cold_backup": "10 4 * * * Asia/Shanghai",
    "raw_archive_audit": "20 5 * * * Asia/Shanghai",
    "runtime_audit": "45 5 * * * Asia/Shanghai",
    "restore_drill": "0 5 1 * * Asia/Shanghai",
}


def _write_projection(root: Path, human_status: str, *, restored: bool = False) -> None:
    """Write a strict, synthetic projection accepted by the app read model.

    ``restored`` mirrors the exact post-restore runtime shape written by the
    worker.  That makes the browser Oracle cover both a normal published
    pointer and a recovered pointer without implying that OCI was contacted.
    """

    root.mkdir(parents=True, exist_ok=True)
    current: dict[str, Any] = {
        "schema_version": "kmfa.daily_funds.current_projection.v1",
        "publication": {
            "publication_id": "c" * 64,
            "business_date": "2026-07-30",
            "status": "VALID",
            "source_versions": [{"source_version": "a" * 64}, {"source_version": "b" * 64}],
            "reconciliation_difference_fen": 0,
            "threshold_snapshot": {
                "fixed": {"hard_fen": 60_000_000, "soft_fen": 120_000_000},
                "floating": [{
                    "name": "three_month",
                    "active": True,
                    "threshold_fen": 100_000_000,
                    "start": "2026-04-01",
                    "end": "2026-06-30",
                    "days": 91,
                    "coverage": "1",
                    "direct_observations": 90,
                    "covered_days": 91,
                    "carried_forward_days": 1,
                    "reason": None,
                }],
                "currency": "CNY",
                "fixed_risk": "正常",
                "dynamic_flag": None,
            },
            "created_at": "2026-07-30T12:00:00Z",
            "git_commit_sha": "d" * 40,
            "d1_projection_version": "kmfa.daily_funds.d1.v1",
            "r2_manifest_sha256": "e" * 64,
            "oci_backup_state": "PENDING",
        },
        "summary": {
            "total_available_fen": 157_000_000,
            "risk_label": "正常",
            "dynamic_flag": None,
            "by_company_ending_fen": {"合成公司": 157_000_000},
            "by_bank_ending_fen": {"合成银行": 157_000_000},
            "account_ending_by_hash": {"f" * 64: 157_000_000},
        },
        "daily_balances": [
            {"business_date": "2026-07-28", "ending_available_fen": 150_000_000, "direct_observation": False, "coverage_gap": True, "carried_forward": False},
            {"business_date": "2026-07-29", "ending_available_fen": 150_000_000, "direct_observation": True, "coverage_gap": False, "carried_forward": False},
            {"business_date": "2026-07-30", "ending_available_fen": 157_000_000, "direct_observation": True, "coverage_gap": False, "carried_forward": False},
        ],
        "transactions": [
            {
                "transaction_key_hash": "f" * 64,
                "business_date": "2026-07-30",
                "inflow_fen": 25_000_000,
                "outflow_fen": 0,
                "adjustment_fen": 0,
                "internal_transfer": False,
                "source_version": "a" * 64,
                "message_id_hash": "b" * 64,
            },
            {
                "transaction_key_hash": "9" * 64,
                "business_date": "2026-07-30",
                "inflow_fen": 0,
                "outflow_fen": 18_000_000,
                "adjustment_fen": 0,
                "internal_transfer": False,
                "source_version": "a" * 64,
                "message_id_hash": "a" * 64,
            },
        ],
        "runtime": (
            {
                "oci_backup_state": "OK",
                "restored_at": "2026-07-30T12:06:00Z",
            }
            if restored
            else {
                "oci_backup_state": "OK",
                "git_publication_commit_sha": "f" * 40,
                "oci_restore_manifest_sha": "e" * 64,
            }
        ),
    }
    status = {
        "schema_version": "kmfa.daily_funds.status.v1",
        "human_status": human_status,
        "machine_code": "SYNTHETIC_T09_ONLY",
        "effective_business_date": "2026-07-30",
        "last_verified_at": "2026-07-30T12:00:00Z",
        "publication_id": "c" * 64,
        "updated_at": "2026-07-30T12:00:00Z",
        "schedules": dict(STATUS_SCHEDULES),
        "backup_state": "OK",
    }
    # ``/api/排程健康`` reads this file on app mount.  The marker represents
    # something which a worker might know but the browser must never receive.
    flow_state = {
        "schema_version": "kmfa.daily_funds.flow_state.v1",
        "updated_at": "2026-07-30T12:05:00Z",
        "deployment": {
            "runtime_state": "RUNTIME_AUDITED",
            "instance_state": "OBSERVED",
            "identity_state": "UNKNOWN",
            "runtime_audit_at": "2026-07-30T12:04:00Z",
        },
        "schedules": {"observer": "30 3 * * * Asia/Shanghai"},
        "business_flow": {
            "stage": "POST_DEPLOY_OBSERVING",
            "human_status": human_status,
            "effective_business_date": "2026-07-30",
            "last_verified_at": "2026-07-30T12:05:00Z",
            "last_status_at": "2026-07-30T12:05:00Z",
            "publication_present": True,
        },
        "self_healing": {
            "state": "JOURNAL_READY",
            "restart_recovery": "CURSOR_INBOX_LEASES",
            "restore_drill": "NOT_YET_RUN",
            "restore_drill_at": None,
        },
        "post_deploy_observer": {
            "schedule": "30 3 * * * Asia/Shanghai",
            "state": "OBSERVING",
            "last_comparison": "D1_AND_POINTER_VERIFIED",
            "required_business_days": 5,
            "completed_business_days": 1,
            "baseline_business_date": "2026-07-29",
            "started_at": "2026-07-29T12:00:00Z",
            "last_observed_at": "2026-07-30T12:05:00Z",
            "comparisons": [{
                "business_date": "2026-07-30",
                "observed_at": "2026-07-30T12:05:00Z",
                "comparison_state": "D1_AND_POINTER_VERIFIED",
                "coverage_state": "DIRECT_OBSERVATION",
                "amount_state": "ZERO_FEN",
                "threshold_state": "VALID",
                "retrieval_state": "COMPLETE_PAIR",
                "duplicate_state": "SOURCE_VERSION_UNIQUE",
                "backup_state": "OK",
                "restore_state": "NOT_YET_RUN",
                "latency_minutes": 5,
                "raw_fixture_should_not_escape": RAW_SENTINEL,
            }],
        },
    }
    cashflow_observation = {
        "schema_version": "kmfa.daily_funds.cashflow_observation.v2",
        "generated_at": "2026-07-30T12:05:00Z",
        "parser_version": "kmfa.daily_funds.cashflow_observation.v9",
        "source_coverage": {
            "eligible_documents": 2,
            "parsed_documents": 2,
            "rejected_documents": 0,
            "distinct_business_days": 2,
        },
        "rejection_categories": {},
        "evidence_version": "a" * 12,
        "status": "VERIFIED",
        "machine_code": "CASHFLOW_OBSERVATION_VERIFIED",
        "points": [
            {
                "business_date": "2026-07-29",
                "inflow_fen": 1_000,
                "outflow_fen": 400,
                "net_change_fen": 600,
            },
            {
                "business_date": "2026-07-30",
                "inflow_fen": 800,
                "outflow_fen": 1_200,
                "net_change_fen": -400,
            },
        ],
    }
    for name, payload in (
        ("current.json", current), ("status.json", status), ("flow_state.json", flow_state),
        ("cashflow_observation.json", cashflow_observation),
    ):
        (root / name).write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_archived_needs_review_projection(root: Path) -> None:
    """Model the real safe state: raw proof exists, but no money is publishable."""

    _write_projection(root, "需处理")
    (root / "current.json").unlink()
    flow_path = root / "flow_state.json"
    flow = json.loads(flow_path.read_text(encoding="utf-8"))
    flow["business_flow"] = {
        "stage": "BACKFILL_ARCHIVED_NEEDS_REVIEW",
        "human_status": "需处理",
        "effective_business_date": None,
        "last_verified_at": None,
        "last_status_at": "2026-07-30T12:05:00Z",
        "publication_present": False,
    }
    flow["source_discovery"] = {"state": "GENERIC_DOCUMENT_UNRESOLVED"}
    # This is values-free operational coverage only.  It must stay visibly
    # distinct from the synthetic cashflow chart below: a scanned historical
    # day is not an account snapshot, transaction fact, zero-fen
    # reconciliation, or money publication.
    flow["historical_backfill"] = {
        "state": "NEEDS_ATTENTION",
        "window_days": 360,
        "completed_days": 200,
        "remaining_days": 160,
    }
    flow["operations"] = {
        "backfill": {
            "state": "FAILED",
            "code": "ATTACHMENT_DOWNLOAD_TRANSPORT_FAILED",
            "finished_at": "2026-07-30T12:05:00Z",
        },
    }
    flow["attachment_capabilities"] = [{
        "family": "UNCLASSIFIED",
        "suffix": ".png",
        "declared_mime": "image/png",
        "magic": "PNG",
        "parser_version": "kmfa.daily_funds.parser.v3",
        "outcome": "NEEDS_REVIEW",
        "code": "UNSUPPORTED_ATTACHMENT",
        "count": 1,
        "last_observed_at": "2026-07-30T12:05:00Z",
        "raw_fixture_should_not_escape": RAW_SENTINEL,
    }]
    flow_path.write_text(json.dumps(flow, ensure_ascii=False) + "\n", encoding="utf-8")
    status_path = root / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status.update({
        "machine_code": "UNSUPPORTED_ATTACHMENT",
        "effective_business_date": None,
        "last_verified_at": None,
        "publication_id": None,
    })
    status_path.write_text(json.dumps(status, ensure_ascii=False) + "\n", encoding="utf-8")
    observation_path = root / "cashflow_observation.json"
    observation = json.loads(observation_path.read_text(encoding="utf-8"))
    observation.update({
        "source_coverage": {
            "eligible_documents": 0,
            "parsed_documents": 0,
            "rejected_documents": 0,
            "distinct_business_days": 0,
        },
        "rejection_categories": {},
        "status": "NOT_AVAILABLE",
        "machine_code": "CASHFLOW_OBSERVATION_SOURCE_MISSING",
        "points": [],
    })
    observation_path.write_text(json.dumps(observation, ensure_ascii=False) + "\n", encoding="utf-8")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_healthy(base_url: str, server: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if server.poll() is not None:
            detail = server.stdout.read() if server.stdout else ""
            raise AssertionError(f"本地 KMFA 进程提前退出：{detail[-3000:]}")
        try:
            with urllib.request.urlopen(f"{base_url}/healthz", timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.25)
    raise AssertionError("本地 KMFA /healthz 未在 45 秒内就绪")


def _start_server(publication_dir: Path, control_dir: Path, port: int) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env.update({
        "KMFA_PRIVATE_OPS_REQUIRE_ACCESS": "0",
        "DAILY_FUNDS_PUBLICATION_DIR": str(publication_dir),
        "DAILY_FUNDS_CONTROL_DIR": str(control_dir),
    })
    return subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port),
            # The oracle owns the server process and records its own request
            # evidence.  Disabling Uvicorn's access logger avoids filling a
            # piped diagnostic stream with unrelated local logging failures.
            "--no-access-log",
        ],
        cwd=BACKEND,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _stop_server(server: subprocess.Popen[str] | None) -> str:
    if server is None:
        return ""
    if server.poll() is None:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)
    return server.stdout.read() if server.stdout else ""


def _launch_browser(playwright: Any) -> Browser:
    """Prefer a managed Chrome but retain the normal CI Chromium fallback."""

    try:
        # This macOS runner has Chrome already, so the local Oracle does not
        # download a second browser.  CI images normally expose only the
        # Playwright-managed Chromium, which is equally valid for the test.
        return playwright.chromium.launch(headless=True, channel="chrome")
    except PlaywrightError:
        return playwright.chromium.launch(headless=True)


def _summary_response(response: Any, range_value: str) -> bool:
    parsed = urlsplit(response.url)
    return (
        parsed.path == "/ops/api/daily-funds/summary"
        and parse_qs(parsed.query).get("range") == [range_value]
    )


def _projection_bodies(page: Page) -> dict[str, dict[str, Any]]:
    return page.evaluate(
        """async (paths) => Object.fromEntries(await Promise.all(paths.map(async path => {
          const response = await fetch(path, { cache: 'no-store' });
          return [path, { status: response.status, body: await response.text() }];
        })))""",
        list(DAILY_PATHS),
    )


def _assert_projection_is_redacted(page: Page, *, trusted_projection: bool) -> None:
    bodies = _projection_bodies(page)
    assert set(bodies) == set(DAILY_PATHS)
    # ``ATTACHMENT_DOWNLOAD_*`` is now a finite values-free operational
    # result.  Do not treat the ordinary word ``attachment`` as a raw-data
    # marker; the injected sentinel below proves unknown worker fields still
    # cannot cross this boundary.
    forbidden = tuple(token.lower() for token in (
        RAW_SENTINEL, "source_version", "message_id_hash", "raw/messages",
    ))
    for path, response in bodies.items():
        # An unpublished page receives a values-free, schema-stable response
        # for every daily-funds projection endpoint.  That lets the browser
        # render the waiting chart and frozen policy without turning the
        # normal pre-publication state into an API outage or inventing money.
        expected_status = 200
        assert response["status"] == expected_status, f"{path} returned HTTP {response['status']}"
        assert not any(token in response["body"].lower() for token in forbidden), f"raw marker escaped from {path}"
    dom = page.content().lower()
    assert not any(token in dom for token in forbidden), "raw marker escaped into rendered DOM"


def _assert_chart_interaction(page: Page) -> None:
    chart = page.locator("svg").filter(has_text="可用资金")
    chart.first.wait_for(state="visible", timeout=10_000)
    assert chart.count() == 1, f"expected one daily-funds SVG chart, got {chart.count()}"

    # The page deliberately puts the decision chart before operational details,
    # but it can still sit below the initial viewport on a compact desktop.
    # A raw page-coordinate mouse move then lands outside the browser window and
    # falsely proves nothing.  Scroll the real SVG into view and interact via
    # its coordinate system, exactly as an operator would.
    chart.scroll_into_view_if_needed(timeout=10_000)

    # ECharts SVG legend is a user-facing control.  A true click must change
    # its rendered state; merely finding the label is not sufficient evidence.
    legend = chart.locator("text").filter(has_text="固定高风险线").first
    legend.wait_for(state="visible", timeout=5_000)
    before = chart.inner_html()
    legend.click()
    page.wait_for_timeout(150)
    after = chart.inner_html()
    assert before != after, "fixed-risk legend click did not change SVG state"

    box = chart.bounding_box()
    assert box is not None and box["width"] > 100 and box["height"] > 100
    chart.hover(position={"x": box["width"] * 0.82, "y": box["height"] * 0.5}, timeout=10_000)
    page.get_by_text("数据状态：", exact=False).last.wait_for(state="visible", timeout=5_000)


def _exercise_case(
    browser: Browser,
    *,
    base_url: str,
    publication_dir: Path,
    status: str,
    name: str,
    viewport: dict[str, int],
    color_scheme: str,
    exercise_controls: bool,
    out_dir: Path,
    trusted_projection: bool = True,
    restored_projection: bool = False,
) -> dict[str, Any]:
    if trusted_projection:
        _write_projection(publication_dir, status, restored=restored_projection)
    else:
        _write_archived_needs_review_projection(publication_dir)
    context = browser.new_context(viewport=viewport, color_scheme=color_scheme, locale="zh-CN")
    context.tracing.start(screenshots=True, snapshots=True, sources=False)
    page = context.new_page()
    requests: list[str] = []
    responses: list[tuple[str, int]] = []
    console_errors: list[dict[str, Any]] = []
    page_errors: list[str] = []
    page.add_init_script(
        """window.__dailyFundsCspViolations = [];
        document.addEventListener('securitypolicyviolation', event =>
          window.__dailyFundsCspViolations.push(event.violatedDirective));"""
    )
    page.on("request", lambda request: requests.append(request.url))
    page.on("response", lambda response: responses.append((response.url, response.status)))
    page.on(
        "console",
        lambda message: console_errors.append({"text": message.text, "location": message.location})
        if message.type == "error" else None,
    )
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    try:
        response = page.goto(
            f"{base_url}/ops/app?tab=%E6%AF%8F%E6%97%A5%E8%B5%84%E9%87%91",
            # The shared app deliberately starts independent non-current-page
            # reads too.  Those are not a prerequisite for this tab and may
            # remain in flight on a degraded machine plane, so a global
            # ``networkidle`` would turn an intentional isolation property
            # into a false browser failure.  The daily callout below is the
            # actual readiness oracle.
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        assert response and response.status == 200
        # Before source-health arrives the component intentionally renders a
        # conservative ``需处理`` placeholder.  Wait for a *loaded* callout,
        # otherwise that safe initial state could be mistaken for the actual
        # synthetic status under test.
        callout = page.locator(".callout").filter(has_text=f"运行状态：{status}")
        if trusted_projection:
            callout = callout.filter(has_text="数据日期：2026-07-30")
        else:
            callout = callout.filter(has_text="已归档通用候选附件尚未确认是账户余额或资金流水")
        callout = callout.first
        try:
            callout.wait_for(state="visible", timeout=10_000)
        except PlaywrightTimeout as error:
            body = page.locator("body").inner_text()[:1200]
            raise AssertionError(
                "daily-funds projection did not become ready; "
                f"requests={requests}; responses={responses}; console={console_errors}; "
                f"page_errors={page_errors}; body={body!r}"
            ) from error
        assert f"运行状态：{status}" in callout.inner_text(), callout.inner_text()

        range_group = page.get_by_role("group", name="资金时间范围")
        range_group.wait_for(state="visible", timeout=10_000)
        assert range_group.get_by_role("button", name="30 天").get_attribute("aria-pressed") == "true"

        if exercise_controls:
            # One desktop case proves keyboard range switching, custom range,
            # legend toggling, tooltip behavior, and the Access-gated DWS
            # device-auth UI.  The mobile cases focus on their distinct
            # state/layout contract instead of duplicating an imprecise
            # pointer gesture on a touch-sized viewport.
            auth_start = page.get_by_role("button", name="连接张霖泽的钉钉")
            auth_start.wait_for(state="visible", timeout=10_000)
            with page.expect_response(
                lambda candidate: (
                    urlsplit(candidate.url).path == "/ops/api/daily-funds/auth-session"
                    and candidate.request.method == "POST"
                ),
                timeout=10_000,
            ) as expected:
                auth_start.click()
            assert expected.value.status == 202
            page.get_by_text("已在每日资金专用云端卷发起一次授权请求", exact=False).wait_for(
                state="visible", timeout=10_000,
            )
            auth_cancel = page.get_by_role("button", name="撤销本次授权")
            auth_cancel.wait_for(state="visible", timeout=10_000)
            with page.expect_response(
                lambda candidate: (
                    urlsplit(candidate.url).path == "/ops/api/daily-funds/auth-session"
                    and candidate.request.method == "DELETE"
                ),
                timeout=10_000,
            ) as expected:
                auth_cancel.click()
            assert expected.value.status == 202
            page.get_by_text("已请求撤销本次授权码", exact=False).wait_for(
                state="visible", timeout=10_000,
            )
            probe_start = page.get_by_role("button", name="验证云端历史读取")
            probe_start.wait_for(state="visible", timeout=10_000)
            with page.expect_response(
                lambda candidate: (
                    urlsplit(candidate.url).path == "/ops/api/daily-funds/history-probe"
                    and candidate.request.method == "POST"
                ),
                timeout=10_000,
            ) as expected:
                probe_start.click()
            assert expected.value.status == 202
            page.get_by_text("已向独立云端容器提交一次固定的脱敏历史读取验证", exact=False).wait_for(
                state="visible", timeout=10_000,
            )
            seven_days = range_group.get_by_role("button", name="7 天")
            seven_days.focus()
            with page.expect_response(lambda candidate: _summary_response(candidate, "7d"), timeout=10_000) as expected:
                page.keyboard.press("Enter")
            assert expected.value.status == 200
            assert seven_days.get_attribute("aria-pressed") == "true"

            page.get_by_label("自定义开始日期").fill("2026-07-24")
            page.get_by_label("自定义结束日期").fill("2026-07-30")
            with page.expect_response(lambda candidate: _summary_response(candidate, "custom"), timeout=10_000) as expected:
                range_group.get_by_role("button", name="应用").click()
            assert expected.value.status == 200
            page.get_by_text("自定义区间至少 7 个自然日", exact=False).wait_for(state="visible")
            _assert_chart_interaction(page)
        elif trusted_projection:
            page.locator("svg").filter(has_text="可用资金").first.wait_for(state="visible", timeout=10_000)
        else:
            page.get_by_text("暂无可信 publication，需处理", exact=False).wait_for(state="visible", timeout=10_000)
            page.get_by_text("附件解析能力", exact=False).wait_for(state="visible", timeout=10_000)
            page.get_by_text("尚无已验证资金曲线", exact=False).wait_for(state="visible", timeout=10_000)
            page.get_by_text("历史来源覆盖（不含金额）", exact=True).wait_for(state="visible", timeout=10_000)
            page.get_by_text("已覆盖 200 / 360 天；待覆盖 160 天", exact=True).wait_for(state="visible", timeout=10_000)
            page.get_by_text("云端附件读取传输失败", exact=False).first.wait_for(state="visible", timeout=10_000)
            page.get_by_text("已采集收支流水（非可用资金）", exact=False).wait_for(state="visible", timeout=10_000)
            page.get_by_text("收支流水暂不展示金额", exact=False).wait_for(state="visible", timeout=10_000)
            page.get_by_text("归档待分类", exact=False).first.wait_for(state="visible", timeout=10_000)
            page.get_by_text("尚未确认其为资金流水；因此不写入收支图表或金额", exact=False).wait_for(state="visible", timeout=10_000)
            chart = page.locator("svg").filter(has_text="可用资金")
            chart.first.wait_for(state="visible", timeout=10_000)
            assert chart.count() == 1, f"expected one gated daily-funds SVG chart, got {chart.count()}"
            if viewport["width"] >= 1024:
                box = chart.first.bounding_box()
                assert box is not None and 0 <= box["y"] < viewport["height"], (
                    "gated daily-funds chart must enter the initial desktop viewport; "
                    f"box={box}, viewport={viewport}"
                )
            page.get_by_text("固定高风险线", exact=False).first.wait_for(state="visible", timeout=10_000)
            page.get_by_text("固定关注线", exact=False).first.wait_for(state="visible", timeout=10_000)
            assert "UNSUPPORTED_ATTACHMENT" not in page.content()
        _assert_projection_is_redacted(page, trusted_projection=trusted_projection)
        csp_violations = page.evaluate("() => window.__dailyFundsCspViolations || []")
        assert not csp_violations, f"CSP violations: {csp_violations}"
        allowed_failure_paths = set() if trusted_projection else {
            "/ops/api/daily-funds/summary", "/ops/api/daily-funds/timeseries",
        }
        failed_responses = [
            (url, response_status)
            for url, response_status in responses
            if response_status >= 400 and urlsplit(url).path not in allowed_failure_paths
        ]
        unexpected_console_errors = [
            error
            for error in console_errors
            if not (
                not trusted_projection
                and "Failed to load resource" in str(error.get("text") or "")
                and urlsplit(str((error.get("location") or {}).get("url") or "")).path in allowed_failure_paths
            )
        ]
        assert not unexpected_console_errors, (
            f"console errors: {unexpected_console_errors}; unexpected failed responses: {failed_responses}"
        )
        assert not page_errors, f"page errors: {page_errors}"
        if viewport["width"] <= 480:
            overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            assert overflow <= 1, f"mobile horizontal overflow: {overflow}px"
        page.screenshot(path=out_dir / f"{name}.png", full_page=True)
        (out_dir / f"{name}.html").write_text(page.content(), encoding="utf-8")
        daily_paths = {
            urlsplit(request).path
            for request in requests
            if "/daily-funds/" in urlsplit(request).path
        }
        expected_paths = {
            "/ops/api/daily-funds/summary",
            "/ops/api/daily-funds/timeseries",
            "/ops/api/daily-funds/cashflow-observations",
            "/ops/api/daily-funds/source-health",
            "/ops/api/daily-funds/thresholds",
            "/ops/api/daily-funds/auth-session",
            "/ops/api/daily-funds/history-probe",
        }
        assert expected_paths.issubset(daily_paths), f"missing daily projection requests: {expected_paths - daily_paths}"
        protected_paths = {
            urlsplit(request).path
            for request in requests
            if urlsplit(request).path.startswith(("/api/", "/ops/api/"))
        }
        assert protected_paths == expected_paths, (
            "daily-funds deep link requested unrelated protected paths: "
            f"{sorted(protected_paths - expected_paths)}"
        )
        return {
            "name": name,
            "human_status": status,
            "viewport": viewport,
            "color_scheme": color_scheme,
            "controls_exercised": exercise_controls,
            "trusted_projection": trusted_projection,
            "restored_projection": restored_projection,
            "status": "PASS",
            "daily_projection_requests": sorted(daily_paths),
            "mobile_overflow_checked": viewport["width"] <= 480,
        }
    finally:
        context.tracing.stop(path=out_dir / f"{name}.trace.zip")
        context.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    server: subprocess.Popen[str] | None = None
    server_log = ""
    try:
        with tempfile.TemporaryDirectory(prefix="kmfa-daily-funds-page-e2e-") as temp:
            temp_root = Path(temp)
            publication_dir = temp_root / "publication"
            control_dir = temp_root / "control"
            control_dir.mkdir()
            _write_projection(publication_dir, "已更新")
            port = _free_port()
            base_url = f"http://127.0.0.1:{port}"
            server = _start_server(publication_dir, control_dir, port)
            _wait_healthy(base_url, server)
            with sync_playwright() as playwright:
                browser = _launch_browser(playwright)
                try:
                    results.append(_exercise_case(
                        browser, base_url=base_url, publication_dir=publication_dir,
                        status="已更新", name="updated-desktop", viewport={"width": 1440, "height": 1000},
                        color_scheme="light", exercise_controls=True, out_dir=args.out_dir,
                    ))
                    results.append(_exercise_case(
                        browser, base_url=base_url, publication_dir=publication_dir,
                        status="处理中", name="processing-mobile", viewport={"width": 390, "height": 844},
                        color_scheme="dark", exercise_controls=False, out_dir=args.out_dir,
                    ))
                    results.append(_exercise_case(
                        browser, base_url=base_url, publication_dir=publication_dir,
                        status="需处理", name="action-needed-desktop", viewport={"width": 1280, "height": 900},
                        color_scheme="light", exercise_controls=False, out_dir=args.out_dir,
                    ))
                    results.append(_exercise_case(
                        browser, base_url=base_url, publication_dir=publication_dir,
                        status="已更新", name="restored-desktop", viewport={"width": 1280, "height": 900},
                        color_scheme="light", exercise_controls=False, out_dir=args.out_dir,
                        restored_projection=True,
                    ))
                    results.append(_exercise_case(
                        browser, base_url=base_url, publication_dir=publication_dir,
                        status="需处理", name="archived-needs-review-desktop", viewport={"width": 1280, "height": 1000},
                        color_scheme="light", exercise_controls=False, out_dir=args.out_dir,
                        trusted_projection=False,
                    ))
                    results.append(_exercise_case(
                        browser, base_url=base_url, publication_dir=publication_dir,
                        status="需处理", name="archived-needs-review-mobile", viewport={"width": 390, "height": 844},
                        color_scheme="dark", exercise_controls=False, out_dir=args.out_dir,
                        trusted_projection=False,
                    ))
                finally:
                    browser.close()
    except Exception as error:  # noqa: BLE001 - write an auditable failure record first.
        results.append({"status": "FAIL", "error": f"{type(error).__name__}: {error}"})
    finally:
        server_log = _stop_server(server)

    failed = [result for result in results if result.get("status") != "PASS"]
    summary = {
        "contract": "T09-daily-funds-page-browser-oracle",
        "fixture": "synthetic-only",
        "production_identity": "NOT_EVALUATED",
        "results": results,
        "status": "PASS" if results and not failed else "FAIL",
    }
    (args.out_dir / "result.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    if failed and server_log:
        (args.out_dir / "server.log").write_text(server_log, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
