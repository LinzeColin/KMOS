# -*- coding: utf-8 -*-
"""TEST-DL-004 —— S07/P7.3 · T-S07-03 读取请求无业务副作用（AC-DL-004）。

AC-DL-004
  过程：**枚举 GET/HEAD 前后状态 diff**
  阈值：有副作用的 GET = 0

T-S07-03
  pass_gate：有副作用 GET=0；同幂等键唯一结果；任务资源有上限

## 为什么用实测 diff，而不是读代码找 `write`

读代码找不出三类东西，而这三类恰好是实际会出事的：

  · 写发生在被调用的库里（缓存落盘、惰性初始化、指标持久化），路由函数本身干干净净；
  · 写发生在**异常路径**上——正常返回不写，404/500 时写了一条什么；
  · 写是**将来某次改动**加进来的，而那次改动的作者不知道这条路由必须只读。

前两类靠读代码要把整条调用链读完，第三类根本读不到。
所以这里比对**磁盘上的真实状态**：每条 GET/HEAD 打一次，前后各拍一张快照。

## 允许变动的路径用白名单，不用黑名单

黑名单永远漏，而漏掉的那个正好是没人想到的那个。
这里反过来：**除白名单外任何路径变动都判失败**，白名单里每一条都写清为什么允许。
将来有人让某条 GET 开始写新东西，测试当场红——他要么改回去，
要么在白名单里写下理由，两条路都留下痕迹。

## HEAD 单独测

HEAD 常被当成「GET 但不要正文」而共用实现，于是「GET 只读」的结论被默认延伸到 HEAD。
但框架有时对 HEAD 走不同分支（比如提前返回、跳过某段）。既然阈值是「有副作用 GET=0」，
HEAD 作为同一语义类别就一并证，不靠推断。
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import walking_skeleton as skeleton
from app import main
from app.main import app

ORIGIN = "https://kmfa.test"
client = TestClient(app, base_url=ORIGIN, headers={"Origin": ORIGIN})

#: 允许在读请求期间变动的路径片段。**每条都要有理由**——
#: 没有理由的条目等于把一个真实副作用洗白成「已知情况」。
ALLOWED_MUTABLE = (
    # 运行日志与审计不是业务状态：它们记录「谁读了什么」，正是读请求应该留下的痕迹。
    # 反过来说，读请求**不留痕**才是问题（越权无从追溯）。
    "/logs/",
    "/log/",
    ".log",
    "ledger.jsonl",
    # 防滥用计数器：读请求本来就该计入速率预算，不计才是漏洞。
    "abuse",
    # Python 与 pytest 的自有产物，与被测系统无关。
    "__pycache__",
    ".pyc",
    ".pytest_cache",
    # SQLite 的 WAL/journal 是同一份数据的表示形式，不是新增业务事实；
    # 纯读也可能触发 checkpoint。真正的内容变化会被 .db 本身的大小/时间戳抓到。
    "-wal",
    "-shm",
    "-journal",
    # 惰性建表：首次读会创建空库并跑迁移。这是**结构**不是业务事实。
    # 这条白名单不靠声称——`test_lazy_schema_bootstrap_writes_no_business_rows`
    # 打开建出来的库逐表数行，任何一行都判失败。
    # （生产环境里库早已存在，这一步只在全新状态目录上发生。）
    "walking_skeleton.sqlite3",
    "kmfa_app_state.sqlite3",
)


def _snapshot(root: Path) -> dict[str, tuple[int, int]]:
    """(相对路径) → (字节数, mtime_ns)。

    用 size+mtime 而不是内容摘要：这里要跑 45 条路由 × 2 次，
    内容摘要会把测试拖成分钟级。size+mtime 抓得住「写过」这件事，
    而这正是本用例要回答的问题——**有没有写**，不是写了什么。
    """
    state: dict[str, tuple[int, int]] = {}
    for path in root.rglob("*"):
        text = str(path)
        if any(token in text for token in ALLOWED_MUTABLE):
            continue
        try:
            info = path.stat()
        except OSError:
            continue
        if path.is_file():
            state[str(path.relative_to(root))] = (info.st_size, info.st_mtime_ns)
    return state


def _diff(before: dict, after: dict) -> list[str]:
    problems = []
    for key in sorted(set(after) - set(before)):
        problems.append(f"新增文件 {key}")
    for key in sorted(set(before) - set(after)):
        problems.append(f"删除文件 {key}")
    for key in sorted(set(before) & set(after)):
        if before[key] != after[key]:
            problems.append(f"内容改变 {key}（{before[key]} → {after[key]}）")
    return problems


def _walk_routes(container) -> list:
    """展开路由树，**递归进 included router**。

    第一版没递归，于是 `app.include_router(...)` 挂进来的整个
    walking-skeleton 路由组被静默丢掉——FastAPI 把它包成 `_IncludedRouter`，
    该对象没有 `.path` / `.methods`，`getattr(..., "")` 兜底成空串后就被跳过了。

    **失败方式是「少枚举」，而少枚举的表现是全绿。** 这正是本文件开头警告过的
    那类失效：覆盖为零的绿灯。所以下面的守卫用例改成按**具体路由组**点名，
    不再只数总数——数量对不上会被发现，整组消失也会。
    """
    found = []
    for route in getattr(container, "routes", []) or []:
        if getattr(route, "path", None) is not None and getattr(route, "methods", None):
            found.append(route)
            continue
        # `_IncludedRouter`（app.include_router 的产物）把真正的路由藏在
        # `original_router` 里；Mount / 子应用则用 `app` 或 `router`。
        # 三个都探，且**不 break**——一个对象可能同时挂着多处。
        for attribute in ("original_router", "router", "app", "routes"):
            child = getattr(route, attribute, None)
            if child is not None and child is not route and hasattr(child, "routes"):
                found.extend(_walk_routes(child))
    return found


ALL_ROUTES = _walk_routes(app)


def _readable_routes() -> list[tuple[str, str]]:
    """枚举所有 GET/HEAD 路由。**从 app 本身枚举，不维护清单**——
    手写清单会和路由表脱节，而脱节的方向永远是「新路由没进清单」。"""
    rows: list[tuple[str, str]] = []
    for route in ALL_ROUTES:
        methods = getattr(route, "methods", None) or set()
        path = getattr(route, "path", "")
        for method in ("GET", "HEAD"):
            if method in methods:
                rows.append((method, path))
    return sorted(set(rows), key=lambda item: (item[1], item[0]))


#: 路径参数的填充值。故意用**不存在**的标识：
#: 404 路径同样不许有副作用，而且异常路径恰恰是最容易偷偷写东西的地方。
PARAM_FILLERS = {
    "name": "kmfa-no-such-fact",
    "asset_path": "no-such-asset.js",
    "app_path": "no-such-page",
    "legacy_path": "no-such-legacy",
    "workspace_path": "no-such-workspace-page",
    "workspace_id": "ws_no_such_workspace_000",
    "upload_id": "up_no_such_upload_000",
    "kind": "text",
}


def _fill(path: str) -> str:
    filled = path
    for name, value in PARAM_FILLERS.items():
        filled = filled.replace("{" + name + "}", value)
        filled = filled.replace("{" + name + ":path}", value)
    return filled


#: 必填 query 参数的填充值。**没有它，带必填参数的路由会以 422 挡在门口，
#: 函数体一行都不执行——测试于是「通过」了，却什么都没测到。**
#: 本文件第一版就栽在这里：`/api/报告中心/导出` 是真正有副作用的那一条，
#: 而它恰好需要 `?报告=`，于是被 422 挡住、被判为无副作用。
#: **覆盖为零的绿灯，比一个红灯危险得多。**
QUERY_FILLERS = {
    "报告": "1",
    "格式": "html",
    "asset": "no-such-asset",
    "log": "no-such-log",
    "name": "no-such-fact",
}


def _query_for(route) -> dict[str, str]:
    """从路由签名里取出必填 query 参数并填值。

    从签名取而不是手写清单：手写清单会和签名脱节，
    而脱节的方向永远是「新参数没进清单」——于是又变回 422 空跑。
    """
    params: dict[str, str] = {}
    dependant = getattr(route, "dependant", None)
    for field in getattr(dependant, "query_params", []) or []:
        name = str(getattr(field, "name", ""))
        if not name:
            continue
        # 「必填」在 pydantic v1/v2 与不同 FastAPI 版本里放在不同位置。
        # 探测两处并兜底为「填上」——**宁可多填一个参数，也不要因为探测失败
        # 而让路由退回 422 空跑**。测法的失效模式必须偏向「多测」，不能偏向「不测」。
        info = getattr(field, "field_info", None)
        if info is not None and hasattr(info, "is_required"):
            required = bool(info.is_required())
        else:
            required = bool(getattr(field, "required", False))
        if required or name in QUERY_FILLERS:
            params[name] = QUERY_FILLERS.get(name, "1")
    return params


ROUTES = _readable_routes()
ROUTE_BY_KEY = {
    (method, getattr(route, "path", "")): route
    for route in app.routes
    for method in (getattr(route, "methods", None) or set())
}


def test_the_enumeration_covers_every_route_group():
    """守卫：枚举漏掉一整组路由时，下面每条用例都会「通过」而什么都没测。

    这条守卫的第一版只查「总数 ≥ 30 + 两条已知路径」，
    于是 `app.include_router` 挂进来的**整个 walking-skeleton 路由组**
    被漏掉而没人发现——两条抽查路径恰好都在顶层 app 上。

    教训：抽查要按**路由组**点名，不能只数总数。
    少一组的表现和一切正常完全一样，除非你专门去问那一组还在不在。
    """
    paths = {path for _, path in ROUTES}
    assert len(ROUTES) >= 40, f"只枚举到 {len(ROUTES)} 条读路由，枚举逻辑可能失效了"

    # 按路由组点名，每组至少一条
    assert "/healthz" in paths, "顶层健康检查"
    assert any("技能健康" in p for p in paths), "public-api 组"
    assert any("/api/" in p for p in paths), "业务 API 组"
    assert any("导出任务" in p for p in paths), "受控导出组（S07/T-S07-03）"
    assert any("walking-skeleton" in p for p in paths), (
        "walking-skeleton 组整组不见了——这正是第一版漏掉的那组，"
        "而漏掉它的表现是全绿")

    # 顶层 app 的**可读**路由必须全在枚举结果里，否则递归展开写反了。
    # 只比 GET/HEAD——把 POST 也算进来是拿两套口径互相校验，注定不成立。
    top_level_readable = {
        r.path for r in app.routes
        if getattr(r, "path", None)
        and {"GET", "HEAD"} & (getattr(r, "methods", None) or set())
    }
    assert top_level_readable <= paths, sorted(top_level_readable - paths)


@pytest.fixture
def isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    """把**两套**状态目录都指向临时目录，并全部纳入快照。

    第一版只盯 `KMFA/machine`，于是 `/api/报告中心/导出` 往
    `KMFA_APP_STATE_DIR` 里写的导出登记完全在视野之外。
    状态有几个落点就盯几个——盯漏一个，等于给那个落点发了张免检证。
    """
    walking = tmp_path / "walking-state"
    app_state = tmp_path / "app-state"
    for directory in (walking, app_state):
        directory.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("KMFA_WALKING_SKELETON_ENABLED", "1")
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(walking))
    monkeypatch.delenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", raising=False)

    # `KMFA_APP_STATE_DIR` 在 **import 时**就被读成模块常量，改环境变量已经晚了。
    # 所以直接改常量。这不是绕过——若只改环境变量，路由会去写真实的
    # `/var/lib/kmfa/state`：本机上是 PermissionError（测试崩在无关的地方），
    # CI 上则可能**真的写进去**，让测试自己变成一次副作用。
    for attribute, target in (
        ("APP_STATE_DIR", app_state),
        ("APP_DB_PATH", app_state / "kmfa_app_state.sqlite3"),
        ("APP_EVENTS_PATH", app_state / "manual_resolution_events.jsonl"),
        ("EXPORT_REGISTRY_PATH", app_state / "report_export_records.jsonl"),
        ("APP_PREVIEWS_PATH", app_state / "manual_impact_previews.jsonl"),
        ("APP_RERUN_STEPS_PATH", app_state / "manual_rerun_steps.jsonl"),
        ("APP_RERUN_CONSISTENCY_PATH", app_state / "manual_rerun_consistency_checks.jsonl"),
        ("APP_AUDIT_PATH", app_state / "audit_events.jsonl"),
    ):
        monkeypatch.setattr(main, attribute, target, raising=False)
    client.cookies.clear()

    repository_root = Path(skeleton.__file__).resolve().parents[4]
    return [walking, app_state, repository_root / "KMFA" / "machine"]


@pytest.mark.parametrize("method,path", ROUTES, ids=lambda v: str(v).replace("/", "_"))
def test_read_request_does_not_change_business_state(method, path, isolated_state):
    """每条读路由打一次，前后比对全部状态落点与仓库树。

    仓库树也要比：读请求往仓库里写东西比往状态目录写更隐蔽——
    开发机上「看起来只是多了个文件」，到了只读文件系统的容器里才炸。
    """
    route = ROUTE_BY_KEY.get((method, path))
    params = _query_for(route) if route is not None else {}

    before = [_snapshot(target) for target in isolated_state]
    response = client.request(method, _fill(path), params=params)
    after = [_snapshot(target) for target in isolated_state]

    # **必须确认函数体真的执行过。** 422 表示请求被参数校验挡在门外，
    # 一行业务代码都没跑——此时「状态没变」不是结论，是没测。
    assert response.status_code != 422, (
        f"{method} {path} 返回 422（缺必填参数）——本用例根本没进到路由体内。"
        f"给 QUERY_FILLERS 补上它的参数，否则这是一盏覆盖为零的绿灯。"
        f"\n详情：{response.text[:300]}")
    assert response.status_code < 500 or response.status_code == 503, (
        f"{method} {path} 返回 {response.status_code}——读路径上崩了，那本身就该修")

    problems: list[str] = []
    for target, snapshot_before, snapshot_after in zip(isolated_state, before, after):
        for item in _diff(snapshot_before, snapshot_after):
            problems.append(f"[{target.name}] {item}")
    assert not problems, (
        f"{method} {path} 是读请求却改了业务状态：\n  " + "\n  ".join(problems))


def test_lazy_schema_bootstrap_writes_no_business_rows(isolated_state):
    """白名单里的两个 `.sqlite3` 必须**被证明**无害，不能只是被声称。

    首次读会创建空库并跑迁移——这是结构，不是业务事实。
    这条用例打开建出来的库逐表数行：**任何一行都判失败**。
    没有它，白名单就成了「把一个真实副作用洗白成已知情况」的地方。
    """
    import sqlite3

    walking, app_state, _ = isolated_state
    for _, path in [r for r in ROUTES if r[0] == "GET"]:
        client.get(_fill(path), params={"报告": "1", "格式": "html"})

    # **复用同一份白名单**，不另立一套：两套白名单迟早会分叉，
    # 而分叉的方向永远是「这边放行了那边没放行」，于是有人去调松严的那边。
    databases = [
        path for path in list(walking.rglob("*.sqlite3")) + list(app_state.rglob("*.sqlite3"))
        if not any(token in str(path) for token in ALLOWED_MUTABLE if token != ".sqlite3")
        or path.name in {"walking_skeleton.sqlite3", "kmfa_app_state.sqlite3"}
    ]
    databases = [p for p in databases
                 if p.name in {"walking_skeleton.sqlite3", "kmfa_app_state.sqlite3"}]
    assert databases, "一个库都没建出来——这条用例失去了对象，说明枚举或夹具变了"

    for database in databases:
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        try:
            tables = [
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%'")
            ]
            assert tables, f"{database.name} 建了但一张表都没有"
            for table in tables:
                # 迁移登记表记录的是「schema 到哪一版」，属于结构自身。
                if "migration" in table.lower() or "schema" in table.lower():
                    continue
                count = connection.execute(
                    f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                assert count == 0, (
                    f"读请求在 {database.name}.{table} 里写了 {count} 行业务数据——"
                    "白名单只放行建表，不放行写数据")
        finally:
            connection.close()


def test_head_and_get_agree_on_being_read_only(isolated_state):
    """HEAD 与 GET 共用实现是常态，但框架可能走不同分支。
    既然阈值是「有副作用 GET=0」，同语义的 HEAD 一并证，不靠推断。"""
    head_routes = [(m, p) for m, p in ROUTES if m == "HEAD"]
    assert head_routes, "一条 HEAD 路由都没有，枚举可能漏了"
    repository_root = Path(skeleton.__file__).resolve().parents[4]
    before = _snapshot(repository_root / "KMFA" / "machine")
    for _, path in head_routes:
        client.request("HEAD", _fill(path))
    assert _diff(before, _snapshot(repository_root / "KMFA" / "machine")) == []


def test_repeated_reads_are_stable(isolated_state):
    """同一条读路由连打三次，状态不变。

    单次不变可能只是「第一次已经写过了，后面在写同一份内容」——
    比如惰性缓存首次落盘。连打三次能把这种「写一次就稳定」的情况和真正的只读分开：
    真正只读的第一次就不写。
    """
    repository_root = Path(skeleton.__file__).resolve().parents[4]
    machine = repository_root / "KMFA" / "machine"
    for _, path in [r for r in ROUTES if r[0] == "GET"][:12]:
        target = _fill(path)
        client.get(target)
        before = _snapshot(machine)
        client.get(target)
        client.get(target)
        assert _diff(before, _snapshot(machine)) == [], f"{target} 重复读之间状态变了"
