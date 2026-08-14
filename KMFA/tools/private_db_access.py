#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读写唯一私有库 Private-Database——**用容器里真有的那把凭据**。

为什么不只走 token（2026-07-27 线上实测定位）：
  技能台账回传从未成功过，私有库里连 skill-ledger 目录都不存在，而回传按设计
  静默失败（不该拖垮技能），于是断了几十次无人察觉。加上回传留痕后一次就定位到：
  容器内 `KMFA_BACKUP_GH_TOKEN` 是空的。
  查 Coolify 发现**同名变量存了两份**——正是以前踩过的坑，空的那份赢了。

  修法不是去改那个 token（密钥不该经 agent 之手，也不该为此反复重建）。
  同一个容器里有一把**已经证明能用**的部署密钥：project-cost-refresh 每天
  用它 clone 私有库、rc=0，上游归档也用它。既然它在、它能用，就用它。

所以这里的策略是：token 在就走 REST（快、无需 clone）；token 不在就走部署密钥
（sparse clone，只取要的那个文件）。两条都没有才报读不到——**不假装成功**。

【Owner 铁律】只进唯一私有库 Private-Database，永不新建 repo。
"""
from __future__ import annotations
import base64
import json
import os
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

REPO = os.environ.get("KMFA_LEDGER_REPO", "LinzeColin/Private-Database")
DEPLOY_KEY = os.environ.get("KMFA_BACKUP_DEPLOY_KEY", "/opt/kmfa/secrets/kmfa_backup_deploy_key")
API = "https://api.github.com"


#: 稀疏 checkout 的超时预算。私有库很大，blob 在 checkout 这一步才真正下载，
#: 默认 120s 线上不够用（2026-07-28 实测 self-audit 就卡死在这里）。
#: 环境变量可调，方便在慢机器上加预算而不必改代码重部署。
CHECKOUT_TIMEOUT_SECONDS = int(os.environ.get("KMFA_PRIVATE_DB_CHECKOUT_TIMEOUT", "300"))


class Unavailable(RuntimeError):
    """够不着私有库——是「读不到」，不是「没有内容」。两者绝不能混。"""


def token() -> str | None:
    for key in ("KMFA_BACKUP_GH_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        value = os.environ.get(key)
        if value and value.strip():
            return value.strip()
    return None


def has_deploy_key() -> bool:
    return Path(DEPLOY_KEY).is_file()


def _ssh_env() -> dict:
    env = dict(os.environ)
    env["GIT_SSH_COMMAND"] = (
        f"ssh -i {DEPLOY_KEY} -o IdentitiesOnly=yes "
        "-o StrictHostKeyChecking=accept-new -o BatchMode=yes")
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def _git(args: list[str], cwd: str | None = None, timeout: int = 120) -> str:
    try:
        done = subprocess.run(["git", *args], cwd=cwd, env=_ssh_env(), timeout=timeout,
                              capture_output=True, text=True)
    except subprocess.TimeoutExpired as exc:
        # 超时也是「够不着」，必须归成 Unavailable。
        #
        # 2026-07-28 线上：`git checkout --quiet` 在 120s 上超时，而 TimeoutExpired
        # 不是 Unavailable，于是一路穿过 lineage_graph 的 `except ManifestUnavailable`
        # 变成裸 traceback——self-audit 报 rc=1 但失败码是 UNKNOWN，看的人只能猜。
        # 调用方对「读不到」是有正经处理的（如实说读不到，不当成没有资产）；
        # 让超时绕开那条路，等于把一个已知状态退化成未知故障。
        raise Unavailable(f"git {args[0]} 超时（{timeout}s）——私有库大，网络或磁盘慢") from exc
    if done.returncode != 0:
        # stderr 可能带 ssh 细节，但不含密钥本体；截断防止把整段塞进台账。
        raise Unavailable(f"git {args[0]} 失败：{(done.stderr or '').strip()[:200]}")
    return done.stdout


def _rest(method: str, path: str, tok: str, body=None):
    request = urllib.request.Request(
        f"{API}{path}", data=json.dumps(body).encode() if body is not None else None,
        method=method)
    request.add_header("Authorization", f"Bearer {tok}")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("User-Agent", "kmfa-private-db")
    if body is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise Unavailable(f"私有库返回 HTTP {exc.code}") from exc


def _sparse_clone_file(path: str, into: str) -> None:
    """只把**一个文件**检出到工作树。

    要写回私有库就必须有工作树（要 add/commit/push），但不需要它旁边的邻居。
    用 `--no-cone` 才能精确到文件；cone 模式只认目录，一给就是整个目录。
    """
    _blobless_clone(into)
    _git(["sparse-checkout", "init", "--no-cone"], cwd=into)
    _git(["sparse-checkout", "set", path], cwd=into)
    _git(["checkout", "--quiet"], cwd=into, timeout=CHECKOUT_TIMEOUT_SECONDS)


def _blobless_clone(into: str) -> None:
    """只取 commit/tree，不取任何 blob，也不建工作树。

    配合 `git show HEAD:<path>` 使用：blob 在那一刻按需拉一个，仅此一个。
    """
    _git(["clone", "--quiet", "--filter=blob:none", "--no-checkout",
          f"git@github.com:{REPO}.git", into], timeout=180)


def read_text(path: str) -> str:
    """读私有库里的一个文件。够不着抛 Unavailable，绝不返回空串冒充「文件是空的」。

    走部署密钥时**不建工作树**——`git show HEAD:<path>` 在 blobless clone 上按需
    只拉那一个 blob。

    原实现是 `_sparse_clone([该文件的父目录])`：为了读一份 `manifest.jsonl`，
    把整个 `Private-KMDatabase/` 检出到磁盘——里面装着 `KMFA/KMFA_MetaData`、objects、
    `KMFA/app-state-backup` 等等，几百 MB。2026-07-28 线上就卡在这一步：
    `git checkout --quiet` 120s 超时，self-audit 因此连续失败。
    把超时调大只是让它「慢着失败」；真正该改的是**别去检出根本不需要的东西**。
    """
    tok = token()
    if tok:
        got = _rest("GET", f"/repos/{REPO}/contents/{path}", tok)
        if got is None:
            raise Unavailable(f"私有库里没有 {path}")
        return base64.b64decode(got["content"]).decode("utf-8", "replace")

    if not has_deploy_key():
        raise Unavailable("容器内既没有可用 token，也没有部署密钥")

    with tempfile.TemporaryDirectory(prefix="kmfa-pdb-") as work:
        _blobless_clone(work)
        try:
            return _git(["show", f"HEAD:{path}"], cwd=work, timeout=CHECKOUT_TIMEOUT_SECONDS)
        except Unavailable as exc:
            # git show 对「路径不存在」也返回非零。这两种要分开：文件不在是业务事实，
            # 网络/超时是够不着——混在一起会让「私有库里没有这个文件」看起来像故障。
            if "exists on disk" in str(exc) or "does not exist" in str(exc):
                raise Unavailable(f"私有库里没有 {path}") from exc
            raise


def append_line(path: str, line: str, message: str) -> str:
    """往私有库里的一个文本文件追加一行；文件不存在则创建。"""
    tok = token()
    if tok:
        got = _rest("GET", f"/repos/{REPO}/contents/{path}", tok)
        old = base64.b64decode(got["content"]).decode("utf-8", "replace") if got else ""
        if old and not old.endswith("\n"):
            old += "\n"
        body = {"message": message,
                "content": base64.b64encode((old + line.rstrip("\n") + "\n").encode()).decode()}
        if got:
            body["sha"] = got["sha"]
        _rest("PUT", f"/repos/{REPO}/contents/{path}", tok, body)
        return f"✓ 已回传（REST）{REPO}/{path}"

    if not has_deploy_key():
        raise Unavailable("容器内既没有可用 token，也没有部署密钥")

    with tempfile.TemporaryDirectory(prefix="kmfa-pdb-") as work:
        # 精确到**文件**，不是它的父目录。父目录口径下，只要哪天日志挪进一个大目录，
        # 就会像 read_text 那样把几百 MB 检出到磁盘然后超时（2026-07-28 实测）。
        _sparse_clone_file(path, work)
        target = Path(work) / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(line.rstrip("\n") + "\n")
        _git(["add", path], cwd=work)
        # 无变化不产生空提交——每天几十次运行，空提交会把历史淹掉。
        if not subprocess.run(["git", "diff", "--cached", "--quiet"],
                              cwd=work, env=_ssh_env()).returncode:
            return "无变化，未提交"
        _git(["-c", "user.email=kmfa-skills@localhost", "-c", "user.name=KMFA Skills",
              "commit", "-q", "-m", message], cwd=work)
        _git(["push", "-q", "origin", "HEAD"], cwd=work, timeout=180)
        return f"✓ 已回传（部署密钥）{REPO}/{path}"
