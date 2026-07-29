# -*- coding: utf-8 -*-
"""dws 数据授权请求器：自己去问 CLI，不靠我的记忆猜命令。

背景（2026-07-29）：`upstream-archive` 挂在 AUTH_PERMISSION_DENIED。缺的是
**数据授权**（读群消息内容那层，有 TTL 会过期），不是 access-token——那层
由 dws-keepalive 无交互刷新，55 次全绿。重新授权要 Owner 在宿主应用点确认。

**我已经凭记忆猜错过两次授权入口**（两次把 Owner 指去钉钉开放平台控制台）。
所以这个工具的核心契约不是「会不会调对命令」，而是：

    猜不到的时候，必须把 CLI 里**真实存在**的子命令原样交出来，
    而不是再编一个命令名。

下面的测试全部用**假 dws**跑真子进程——不 mock 掉 subprocess，
因为要验的恰恰是「真去问了 CLI」这件事。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "KMFA/tools/automation/dws_data_auth_request.py"


def _fake_dws(tmp_path: Path, script: str) -> dict:
    """造一个假 dws 放进 PATH，返回可传给 subprocess 的 env。"""
    binary = tmp_path / "dws"
    binary.write_text(script, encoding="utf-8")
    binary.chmod(0o755)
    env = dict(os.environ)
    env["PATH"] = f"{tmp_path}:{env['PATH']}"
    return env


def _run(env: dict, *args: str) -> tuple[int, dict]:
    proc = subprocess.run([sys.executable, str(TOOL), *args],
                          capture_output=True, text=True, check=False, env=env)
    try:
        return proc.returncode, json.loads(proc.stdout)
    except json.JSONDecodeError:  # pragma: no cover - 便于排错
        raise AssertionError(f"输出不是 JSON：\n{proc.stdout}\n{proc.stderr}") from None


CLI_WITH_AUTH = """#!/bin/sh
case "$*" in
  "--help")            echo "Usage: dws <cmd>"; echo "  chat    群与消息"; echo "  contact 通讯录" ;;
  "chat --help")       echo "Usage: dws chat <cmd>"; echo "  message   消息"; echo "  data-auth 数据授权"; echo "  search    搜索" ;;
  "chat data-auth --help") echo "Usage: dws chat data-auth [--ttl DURATION]"; echo "  --ttl  授权时长" ;;
  "chat data-auth"*)   echo '{"ok":true}' ;;
  *) echo "unknown: $*" >&2; exit 2 ;;
esac
"""

CLI_WITHOUT_AUTH = """#!/bin/sh
case "$*" in
  "--help")      echo "Usage: dws <cmd>"; echo "  chat    群与消息"; echo "  drive   网盘" ;;
  "chat --help") echo "Usage: dws chat <cmd>"; echo "  message 消息"; echo "  search  搜索" ;;
  *) echo "unknown: $*" >&2; exit 2 ;;
esac
"""


def test_it_finds_the_auth_subcommand_by_asking_the_cli(tmp_path):
    env = _fake_dws(tmp_path, CLI_WITH_AUTH)
    rc, report = _run(env, "--dry-run")
    assert rc == 0, report
    assert report["status"] == "PROBED_ONLY"
    assert "dws chat data-auth" in report["候选"], report


def test_dry_run_never_pops_a_dialog_at_the_owner(tmp_path):
    """探测模式绝不能真发起——否则压测碰它就会平白给 Owner 弹窗。"""
    marker = tmp_path / "fired"
    env = _fake_dws(tmp_path, CLI_WITH_AUTH.replace(
        '"chat data-auth"*)   echo \'{"ok":true}\' ;;',
        f'"chat data-auth"*)   touch {marker}; echo \'{{"ok":true}}\' ;;'))
    rc, report = _run(env, "--dry-run")
    assert rc == 0
    assert not marker.exists(), "探测模式把授权真发出去了"


def test_send_actually_invokes_the_command(tmp_path):
    marker = tmp_path / "fired"
    env = _fake_dws(tmp_path, CLI_WITH_AUTH.replace(
        '"chat data-auth"*)   echo \'{"ok":true}\' ;;',
        f'"chat data-auth"*)   touch {marker}; echo \'{{"ok":true}}\' ;;'))
    rc, report = _run(env, "--send")
    assert rc == 0, report
    assert marker.exists(), "带 --send 却没真调命令"
    assert report["status"] == "AUTH_REQUESTED"


def test_when_there_is_no_auth_subcommand_it_hands_back_the_real_list(tmp_path):
    """**本文件最重要的一条。**

    猜不到就得交出真实清单——那是能被下一步利用的事实。
    编一个命令名出来，就是第三次把 Owner 指错地方。
    """
    env = _fake_dws(tmp_path, CLI_WITHOUT_AUTH)
    rc, report = _run(env, "--send")
    assert rc == 4, report
    assert report["status"] == "NO_AUTH_SUBCOMMAND_FOUND"
    listed = {s for probe in report["探测"] for s in probe["子命令"]}
    assert {"message", "search"} <= listed, f"没把真实子命令交出来：{report['探测']}"


def test_it_does_not_mistake_token_auth_for_data_auth(tmp_path):
    """`auth-status` / `login` 是**认证**那层——它一直是好的，不是缺的这个。

    认错了会去「修」一个没坏的东西，然后报告说修好了。
    """
    cli = """#!/bin/sh
case "$*" in
  "--help")      echo "Usage: dws <cmd>"; echo "  chat 群与消息"; echo "  auth-status 认证状态"; echo "  login 登录" ;;
  "chat --help") echo "Usage: dws chat <cmd>"; echo "  message 消息" ;;
  *) exit 2 ;;
esac
"""
    env = _fake_dws(tmp_path, cli)
    rc, report = _run(env, "--send")
    assert rc == 4, f"把 auth-status/login 当成数据授权了：{report}"


def test_a_blocking_command_is_read_as_the_dialog_being_up(tmp_path):
    """命令卡住通常是**好消息**：弹窗已推出、正等 Owner 点。不能判成失败。"""
    cli = CLI_WITH_AUTH.replace(
        '"chat data-auth"*)   echo \'{"ok":true}\' ;;',
        '"chat data-auth"*)   sleep 300 ;;')
    env = _fake_dws(tmp_path, cli)
    proc = subprocess.run(
        [sys.executable, "-c",
         f"import runpy,sys; sys.argv=['t','--send']; "
         f"sys.path.insert(0,{str(TOOL.parent)!r}); "
         f"import dws_data_auth_request as m; "
         f"m.run.__globals__['run']; "
         f"print(m.run(['dws','chat','data-auth'], timeout=1)[0])"],
        capture_output=True, text=True, check=False, env=env)
    assert proc.stdout.strip() == "124", f"超时没被识别：{proc.stdout} {proc.stderr}"


def test_the_skill_is_wired_into_the_runner():
    """技能要真接进 run_skill.sh——否则触发了也跑不起来。"""
    runner = (REPO / "KMFA/deploy/skills-runtime/run_skill.sh").read_text(encoding="utf-8")
    assert "dws-data-auth)" in runner, "技能没接进 run_skill.sh"
    assert "dws_data_auth_request.py" in runner


def test_the_trigger_is_never_unconditional():
    """触发必须**有闸**——无条件弹窗 = 每次部署都骚扰 Owner 一次。

    这条改过两次，两次都是设计真的变了：
      v1 闸是环境变量 KMFA_DWS_DATA_AUTH_REQUEST —— 线上实证不生效
         （变量没到容器，KMFA_BOOT_SWEEP 那次的重演），整条删除。
      v2 闸放在 entrypoint 里先判再决定跑不跑 —— 判成「不跑」时整件事只在
         读不到的 cron.log 留一行，线上跟故障分不开，又浪费一次部署。
    现在闸在**技能内部**：entrypoint 无条件调用，每次决定都进台账。
    闸的语义细节归 test_dws_auth_asks_itself.py 管。
    """
    runner = (REPO / "KMFA/deploy/skills-runtime/run_skill.sh").read_text(encoding="utf-8")
    assert "--only-if-blocked" in runner, "技能被无条件调用且没有闸——那就是每次部署都弹窗"

    tool = (REPO / "KMFA/tools/automation/dws_data_auth_request.py").read_text(encoding="utf-8")
    gate = tool.index("args.only_if_blocked")
    fire = tool.index("rc, output = run(invocation")
    assert gate < fire, "闸在真发起之后才判——等于没闸"


def test_it_tries_every_candidate_not_just_the_first(tmp_path):
    """一个候选失败，不代表这条路走不通。

    2026-07-29 线上第一次拿到真答案时暴露的：上一版只试**字母序第一个**候选
    （`dws chat chmod`），它要一个位置参数（`accepts 1 arg(s), received 0`），
    于是整件事以 AUTH_REQUEST_FAILED 收场——而候选里还有个 `data-auth`
    **从没被试过**。差一步就拿到弹窗，却停在了第一个。
    """
    cli = """#!/bin/sh
case "$*" in
  "--help")                echo "Usage: dws <cmd>"; echo "  chat 群与消息" ;;
  "chat --help")           echo "Usage: dws chat <cmd>"; echo "  chmod 授权"; echo "  data-auth 数据授权"; echo "  message 消息" ;;
  "chat chmod --help")     echo "Usage: dws chat chmod <scope>" ;;
  "chat chmod")            echo '{"error":{"message":"accepts 1 arg(s), received 0"}}' >&2; exit 5 ;;
  "chat data-auth --help") echo "Usage: dws chat data-auth" ;;
  "chat data-auth")        echo '{"ok":true}' ;;
  *) exit 2 ;;
esac
"""
    env = _fake_dws(tmp_path, cli)
    rc, report = _run(env, "--send")
    tried = [t["命令"] for t in report["尝试"]]
    assert "dws chat chmod" in tried, f"第一个候选没试：{tried}"
    assert "dws chat data-auth" in tried, (
        f"第一个失败就停了——第二个候选本来能成功：{tried}")
    assert rc == 0 and report["status"] == "AUTH_REQUESTED", report


def test_every_candidate_help_is_kept_even_when_all_fail(tmp_path):
    """全失败时，留下的必须是一份**完整的命令说明书**，不是半句。

    这是我今天在这件事上唯一真正前进的一步：拿到 CLI 自己的原话。
    只留第一个候选的帮助，等于把另一半答案丢掉。
    """
    cli = """#!/bin/sh
case "$*" in
  "--help")                echo "Usage: dws <cmd>"; echo "  chat 群与消息" ;;
  "chat --help")           echo "Usage: dws chat <cmd>"; echo "  chmod 授权"; echo "  data-auth 数据授权" ;;
  "chat chmod --help")     echo "CHMOD_HELP_MARKER" ;;
  "chat data-auth --help") echo "DATAAUTH_HELP_MARKER" ;;
  *) exit 5 ;;
esac
"""
    env = _fake_dws(tmp_path, cli)
    rc, report = _run(env, "--send")
    helps = json.dumps(report["候选帮助"], ensure_ascii=False)
    assert "CHMOD_HELP_MARKER" in helps and "DATAAUTH_HELP_MARKER" in helps, \
        f"漏了某个候选的帮助：{helps[:300]}"
    assert rc == 5, report
