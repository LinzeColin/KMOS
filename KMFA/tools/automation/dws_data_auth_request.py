#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""向 Owner 发起 dws **数据授权**请求——即：把授权弹窗推到他的钉钉/悟空上。

为什么要这个东西（2026-07-29）：
`upstream-archive` 挂在 `AUTH_PERMISSION_DENIED`（`chat/list_conversation_message_v2`）。
坏的**不是** access-token 那层——`dws-keepalive` 无交互刷新，55 次全绿；
坏的是**数据授权**（读群消息内容的那层授权），它有 TTL、会过期，
而重新授权要 Owner 在宿主应用里点一下确认。

为什么这个脚本要「自己去问 CLI」而不是写死命令：
**我已经凭记忆猜错过两次授权入口**（两次把 Owner 指去钉钉开放平台控制台，
都不是地方）。第三次不猜了。这里的做法是：

  1. 把 `dws --help` / `dws chat --help` 真跑一遍，拿到**真实存在**的子命令；
  2. 在里面找授权类子命令（auth / grant / authorize / consent / chmod / 授权）；
  3. 找到就读它自己的 `--help`，按它**自己声明**的参数调用；
  4. 找不到就把真实子命令清单原样报出来——那是一条能被下一步利用的事实，
     而不是又一次猜测。

「报出来」落在哪：stdout（run_skill.sh 会把整段存成本次运行的日志快照，
并随台账回传私有库）。help 文本不含密钥，但仍只走私有面，不上公开端点。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

#: 授权类子命令的候选词。宁可多认几个再用 --help 甄别，
#: 也不要漏掉一个而误报「CLI 里没有授权入口」。
AUTH_WORDS = ("data-auth", "dataauth", "authorize", "auth", "grant",
              "consent", "chmod", "permission", "授权")

#: 一眼就能排除的：这些是**认证**（我们已经有）而不是**数据授权**（缺的这个）。
NOT_DATA_AUTH = ("auth-status", "authstatus", "token", "login", "logout", "whoami")

#: 缩进行的第一个词 = 子命令候选。
#: **刻意写宽**：真实 help 的排版千奇百怪（一个空格、制表符、对齐列都有），
#: 而漏认一个子命令的代价是「报告说 CLI 里没有授权入口」——那正是这个工具
#: 要避免的那种错话。多认的候选后面会被 looks_like_data_auth 滤掉，代价只是噪音。
SUBCOMMAND_RE = re.compile(r"^[ \t]{2,}([a-z][a-z0-9-]{1,30})(?=[ \t]|$)", re.M)


def run(args: list[str], *, timeout: int = 60) -> tuple[int, str]:
    try:
        proc = subprocess.run(args, capture_output=True, text=True,
                              timeout=timeout, check=False)
    except FileNotFoundError:
        return 127, "dws 不在 PATH 上"
    except subprocess.TimeoutExpired:
        return 124, f"超时（{timeout}s）——若这是授权命令，很可能正等 Owner 在钉钉上确认"
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def subcommands(help_text: str) -> list[str]:
    """从 help 文本里抠出子命令名。宽松匹配，宁滥勿缺。"""
    return sorted({m for m in SUBCOMMAND_RE.findall(help_text)
                   if not m.startswith("-")})


def looks_like_data_auth(name: str) -> bool:
    low = name.lower()
    if any(bad in low for bad in NOT_DATA_AUTH):
        return False
    return any(word in low for word in AUTH_WORDS)


def emit(report: dict) -> None:
    print(json.dumps(report, ensure_ascii=False, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="只探测 CLI 表面、不真发起授权（不给 Owner 弹窗）")
    ap.add_argument("--send", action="store_true", help="真发起授权请求")
    ap.add_argument("--ttl", default=None,
                    help="授权时长；不给就用命令自己的默认值，不擅自替 Owner 选")
    ap.add_argument("--only-if-blocked", action="store_true",
                    help="仅当上游归档确实卡住、且已过静默期时才发起")
    ap.add_argument("--ledger", default="/var/log/kmfa/ledger.jsonl")
    ap.add_argument("--state", default="/var/log/kmfa/dws-data-auth/.last_request")
    args = ap.parse_args()

    report: dict = {"status": "UNKNOWN", "探测": [], "尝试": []}

    # 闸放在**技能内部**，不放在 entrypoint 里。
    #
    # 上一版放在外面：判据说「不跑」，整件事就只在 cron.log 留一行，而 cron.log
    # 谁都读不到（Coolify logs 返空、exec 404、/api 在 Access 后面）。
    # 线上表现成「什么都没发生」，跟故障完全分不开。**为此浪费了一次部署。**
    # 放进来之后，每一次决定都经 run_skill.sh 进台账，能用一条 gh api 验到。
    if args.only_if_blocked:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from should_request_dws_auth import decide  # noqa: PLC0415

        ok, why = decide(ledger=Path(args.ledger), state=Path(args.state),
                         now=datetime.now())
        report["闸"] = why
        if not ok:
            # **rc=0**：这是「按设计没请求」，不是故障。判成非零会让心跳天天假红，
            # 而天天亮的红灯最后一定被当噪音关掉——真出事那次跟着被忽略。
            report["status"] = "NOT_REQUESTED_BY_DESIGN"
            emit(report)
            return 0

    if not shutil.which("dws"):
        report["status"] = "DWS_NOT_INSTALLED"
        report["说明"] = "容器里没有 dws——这不是授权问题，是运行时缺件"
        emit(report)
        return 3

    # ① 先问 CLI 自己有哪些子命令。这一步的产出本身就是可交付的事实：
    #    它能一次性了结「授权入口到底在哪」这个我已经答错两次的问题。
    surfaces = []
    for probe in (["dws", "--help"], ["dws", "chat", "--help"]):
        rc, text = run(probe, timeout=30)
        subs = subcommands(text)
        surfaces.append({"命令": " ".join(probe), "rc": rc, "子命令": subs})
        report["探测"].append(surfaces[-1])

    candidates: list[list[str]] = []
    for surface in surfaces:
        base = surface["命令"].replace(" --help", "").split()
        for name in surface["子命令"]:
            if looks_like_data_auth(name):
                candidates.append([*base, name])

    if not candidates:
        # 关键分支：**不编**。把真实子命令原样交出去。
        report["status"] = "NO_AUTH_SUBCOMMAND_FOUND"
        report["说明"] = (
            "dws CLI 里找不到授权类子命令。上面「探测」里是它真实存在的全部子命令——"
            "下一步该照着它走，而不是再猜一个命令名。")
        emit(report)
        return 4

    report["候选"] = [" ".join(c) for c in candidates]

    # ② 读候选命令自己的 --help，照它声明的参数来，不硬塞我记忆里的 flag。
    chosen = candidates[0]
    rc, help_text = run([*chosen, "--help"], timeout=30)
    report["候选帮助"] = {"命令": " ".join(chosen), "rc": rc, "原文": help_text[:4000]}

    if args.dry_run or not args.send:
        report["status"] = "PROBED_ONLY"
        report["说明"] = "只探测未发起——要真给 Owner 弹窗请带 --send"
        emit(report)
        return 0

    # ③ 真发起。TTL 只在命令自己声明了该参数、且调用方明确给了值时才带上——
    #    授权时长是 Owner 的事，不替他选。
    invocation = list(chosen)
    if args.ttl and "--ttl" in help_text:
        invocation += ["--ttl", args.ttl]

    rc, output = run(invocation, timeout=180)
    report["尝试"].append({"命令": " ".join(invocation), "rc": rc,
                          "输出": output[:4000]})

    if rc in (0, 124):
        # 写下时间戳：静默期靠它生效。**只在真发起之后写**——
        # 没发起却盖时间戳，会把下一次真该请求的时机推掉。
        if args.only_if_blocked:
            state = Path(args.state)
            state.parent.mkdir(parents=True, exist_ok=True)
            state.write_text(datetime.now().isoformat(timespec="seconds"), encoding="utf-8")
    if rc == 0:
        report["status"] = "AUTH_REQUESTED"
        report["说明"] = "授权请求已发出——Owner 的钉钉/悟空上应出现确认弹窗"
        emit(report)
        return 0
    if rc == 124:
        # 超时**很可能是好消息**：命令正阻塞等 Owner 点确认。
        report["status"] = "AUTH_REQUESTED_AWAITING_CONFIRM"
        report["说明"] = "命令阻塞超时——通常意味着弹窗已推出、正在等 Owner 确认"
        emit(report)
        return 0
    report["status"] = "AUTH_REQUEST_FAILED"
    report["说明"] = "授权命令存在但调用失败；上面「输出」是它自己的原话，照它改"
    emit(report)
    return 5


if __name__ == "__main__":
    sys.exit(main())
