#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把技能运行台账回传 GitHub 私有库——让"技能到底跑没跑"这件事可被自验。

为什么需要它（实测踩到的）：
  台账只写在容器卷 `/var/log/kmfa/ledger.jsonl`，而 Coolify 这个应用的
  `logs` 返回空、`exec` 返回 404，`/api/排程健康` 又在 Access 后面。
  结果是**没有任何不登录就能拿到的证据**能证明技能真跑了。
  更早还踩过更糟的一种：cron 有输出、退出码 0、时间戳新鲜，但它跑的是校验器，
  一个文件都没归档回来——**探日志新鲜度会给出假绿，只有探产出物才作数**。

所以每次技能运行后把台账行 append 到私有库，验证就变成一条 `gh api`，
不需要登录、不需要进容器、不依赖 Coolify 的可观测性。

凭据：`KMFA_BACKUP_GH_TOKEN`（已为备份链路配好，对 Private-Database 有 contents:write）。
没有 token 时静默跳过——台账回传失败不该把技能本身判失败。

【Owner 铁律】只进唯一私有库 Private-Database，永不新建 repo。
"""
from __future__ import annotations
import argparse, base64, json, os, sys, urllib.error, urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.github.com"
REPO = os.environ.get("KMFA_LEDGER_REPO", "LinzeColin/Private-Database")
AREA = "Private-KMDatabase/skill-ledger"


def _token() -> str | None:
    for k in ("KMFA_BACKUP_GH_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        v = os.environ.get(k)
        if v:
            return v.strip()
    return None


def _api(method: str, path: str, token: str, body=None):
    req = urllib.request.Request(
        f"{API}{path}", data=json.dumps(body).encode() if body is not None else None, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "kmfa-skill-ledger")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def month_path(now: datetime | None = None) -> str:
    """按月分片：单文件无限增长会让每次 append 都要下载整月内容。"""
    bj = (now or datetime.now(timezone.utc)).astimezone(timezone(timedelta(hours=8)))
    return f"{AREA}/{bj:%Y-%m}.jsonl"


def append_line(line: str, token: str, repo: str = REPO, path: str | None = None) -> str:
    """把一行 append 到私有库的当月台账，返回结果说明。"""
    path = path or month_path()
    cur = _api("GET", f"/repos/{repo}/contents/{path}", token)
    old = base64.b64decode(cur["content"]).decode("utf-8", "replace") if cur else ""
    if old and not old.endswith("\n"):
        old += "\n"
    body = {
        "message": f"ledger: {json.loads(line).get('skill', '?')} @ {json.loads(line).get('ts', '')}",
        "content": base64.b64encode((old + line.rstrip("\n") + "\n").encode()).decode(),
    }
    if cur:
        body["sha"] = cur["sha"]
    _api("PUT", f"/repos/{repo}/contents/{path}", token, body)
    return f"✓ 已回传 {repo}/{path}"


def main() -> int:
    ap = argparse.ArgumentParser(description="技能台账回传私有库")
    ap.add_argument("--line", help="一行 JSON 台账；缺省从 stdin 读")
    a = ap.parse_args()
    line = a.line if a.line is not None else sys.stdin.read()
    line = line.strip()
    if not line:
        print("空台账行，跳过")
        return 0
    try:
        json.loads(line)
    except json.JSONDecodeError as e:
        print(f"台账行不是合法 JSON，跳过：{e}", file=sys.stderr)
        return 0
    token = _token()
    if not token:
        print("无 KMFA_BACKUP_GH_TOKEN，跳过回传（不影响技能本身）")
        return 0
    try:
        print(append_line(line, token))
    except Exception as e:                       # noqa: BLE001 —— 回传失败绝不拖垮技能
        print(f"回传失败（不影响技能本身）：{type(e).__name__}: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
