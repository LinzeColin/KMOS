#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""考勤简报看门狗：每个工作日上午回头看一眼「上一个工作日到底出没出报」。

没跑起来的东西不会告诉你它没跑。主线那两条 automation 被暂停、被删、没被触发，
或者共享盘掉了、钉钉登录过期了、机器整晚睡着 —— 这些情况主线自己一个字都报不出来，
因为它压根没被执行到。所以这条单独跑，不 import 主线任何模块，也不依赖共享盘上的代码。

发现问题私聊张霖泽，同一件事只报一次（状态落共享盘）。共享盘本身不可用时记不了状态，
那就每天报一次 —— 这种情况本来也该天天知道。

判的是「上一个工作日有没有留下一个结论性标记」，不是「有没有发」。
法定节假日会正常留下 SKIP_NON_WORKDAY，那是结论不是故障；
真正要抓的是运行日志里那一天整片空白 —— 那才叫「今天这份没了，而且没人知道」。
"""
# 系统自带的是 python3.9（看门狗故意不用主线那个 venv）。
# 3.9 在函数定义时就会求值注解，`str | None` 这种写法会直接 TypeError ——
# 而且是在 import 阶段炸，连一个标记都打不出来。加这一行把注解全部推迟成字符串。
from __future__ import annotations

import datetime
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

SKILL = Path(__file__).resolve().parents[1]
ENVF = SKILL / "private_runtime" / "kmfa_brief.env"
CRON = SKILL / "scripts" / "kmfa_brief_cron.sh"
APP_DB = Path.home() / ".codex" / "sqlite" / "codex-dev.db"
BEIJING = ZoneInfo("Asia/Shanghai")

# 简报只有这一条 automation（三个触发钟点都写在它的 rrule 里）。
# 本文件自己跑在 automation-2 上 —— 看门狗不看自己，只看它要守的那条。
AUTOMATIONS = ("automation",)
# 简报最晚的触发点是本机 21:15，看门狗排在第二天上午 ——
# 所以它跑的时候，「上一个工作日该发而没发」已经是定论，不是还没轮到。
MAX_SILENT_HOURS = 26
# 结论性标记：出现任何一个，就说明那一天脚本真的跑到底了、并且给出了判断。
CONCLUSIVE_OK = ("SEND_COMPLETED", "SKIP_ALREADY_SENT",
                 "SKIP_WEEKEND", "SKIP_NON_WORKDAY")
# 这些也是结论性的，但是坏消息。主线自己会告警一次，看门狗再兜一次 ——
# 主线告警走的也是 dws，dws 挂了的时候那条告警同样发不出去。
CONCLUSIVE_BAD = ("SEND_FAILED", "RUN_FAILED", "ABORTED_TIMEOUT",
                  "SMB_UNAVAILABLE", "DINGTALK_UNAVAILABLE", "CONFIG_MISSING",
                  "VENV_MISSING", "NO_TARGET", "SKIP_AFTER_WINDOW")


def env() -> dict:
    """只读部署位那份 env，不 source、不执行。读不到就返回空字典，
    调用方会把「读不到」本身当成一个问题报出去。"""
    out = {}
    try:
        for line in ENVF.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def dws_path(cfg: dict) -> Path:
    """进程环境优先，其次那份 env 文件。
    看门狗的 wrapper 不 source env 文件，所以验证时可以拿环境变量把 dws 打成桩，
    真发不出去任何东西。（主线那边不行：它的 wrapper 有 `set -a; . env`，
    会把导出的测试值再覆盖回真值 —— 踩过一次，一次探针变成了真发群。）"""
    raw = (os.environ.get("KMFA_BRIEF_DWS") or cfg.get("KMFA_BRIEF_DWS")
           or "~/.local/bin/dws")
    return Path(os.path.expanduser(raw))


def notify(text: str, cfg: dict) -> bool:
    exe, user = dws_path(cfg), cfg.get("KMFA_BRIEF_NOTIFY_USER", "").strip()
    if not exe.is_file() or not user:
        print("WATCHDOG_NOTIFY_LOG_ONLY dws_or_user_missing")
        return False
    r = subprocess.run([str(exe), "chat", "message", "send", "--user", user,
                        "--title", "⚠ 考勤简报看门狗", "--text", text[:600], "-y"],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print("WATCHDOG_NOTIFY_LOG_ONLY dws_failed")
        return False
    print("WATCHDOG_NOTIFY_SENT")
    return True


def automation_rows() -> dict:
    if not APP_DB.is_file():
        return {}
    con = sqlite3.connect(f"file:{APP_DB}?mode=ro", uri=True)
    try:
        out = {}
        for aid in AUTOMATIONS:
            row = con.execute("select status, rrule, last_run_at, prompt "
                              "from automations where id = ?", (aid,)).fetchone()
            out[aid] = row
        return out
    except sqlite3.Error:
        return {}
    finally:
        con.close()


def beijing_slots(rrule: str, minute: int = 15) -> list[str]:
    """把 rrule 里的本机钟点换算成北京时间，返回形如 ["17:15", "18:15"]。

    本机是 Australia/Sydney，有夏令时；北京没有。所以同一条 rrule 一年里
    指向两个不同的北京时刻 —— 2026-10-04 悉尼转夏令时那天，19:15 会从
    北京 17:15 变成 16:15，主槽从此天天卡在「还没到出报时刻」上空跑。
    naive 本地时间 .astimezone() 会按那一天的本地规则取偏移，夏令时自动算对。
    """
    m = re.search(r"BYHOUR=([0-9,]+)", rrule or "")
    if not m:
        return []
    today = datetime.date.today()
    out = []
    for h in m.group(1).split(","):
        try:
            local = datetime.datetime.combine(today, datetime.time(int(h), minute))
        except ValueError:
            continue
        out.append(f"{local.astimezone(BEIJING):%H:%M}")
    return out


def previous_workday(today: datetime.date) -> datetime.date:
    d = today - datetime.timedelta(days=1)
    while d.weekday() >= 5:
        d -= datetime.timedelta(days=1)
    return d


def day_markers(log: Path, day: str) -> list[str]:
    """运行日志里 day 这一天出现过的结论性标记。日志按行 "YYYY-MM-DD HH:MM:SS 标记 | 说明"
    追加，但它记的是**本机**日期，业务日写在 RUN_START 的说明里。
    这里两头都认：本机日期是 day，或者说明里带 业务日=day。"""
    try:
        text = log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    hits, armed = [], False
    for line in text.splitlines():
        if line.startswith(day) or f"业务日={day}" in line:
            armed = True
        elif re.match(r"^\d{4}-\d{2}-\d{2} ", line) and not line.startswith(day):
            armed = False
        if not armed:
            continue
        for tok in CONCLUSIVE_OK + CONCLUSIVE_BAD:
            if f" {tok} " in line or line.endswith(f" {tok}"):
                hits.append(tok)
    return hits


def dingtalk_broken(cfg: dict) -> str | None:
    """登录过期是这条线最典型的「几个月后忽然不发了」，而且过期之后
    连告警都发不出去 —— 得在它把某一天的简报弄丢之前先查出来。"""
    exe = dws_path(cfg)
    if not exe.is_file() or not os.access(str(exe), os.X_OK):
        return f"钉钉命令行工具不在了（{exe}）"
    try:
        r = subprocess.run([str(exe), "auth", "status", "-f", "json", "-y"],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return "钉钉登录状态查不了"
    if r.returncode != 0:
        return "钉钉登录状态检查返回失败"
    try:
        d = json.loads(r.stdout)
    except ValueError:
        return None
    if isinstance(d.get("error"), dict) or d.get("success") is False:
        return "钉钉登录已过期，简报发不出去了，需要重新登录"
    return None


def find_problem(cfg: dict) -> tuple[str, str] | None:
    """返回 (问题标识, 给人看的一句话)；一切正常返回 None。
    顺序是有意的：越是「连告警都发不出去」的，越要先查。"""
    if not CRON.is_file() or not os.access(str(CRON), os.X_OK):
        return "deploy_missing", f"部署位的入口脚本不在了或不可执行（{CRON}）"
    if not cfg:
        return "env_unreadable", f"读不到配置 {ENVF}，简报跑不起来"

    runtime_root = Path(cfg.get("KMFA_BRIEF_RUNTIME_ROOT", "")).expanduser()
    if not runtime_root.is_dir():
        return "smb_down", f"共享盘不可用（{runtime_root}），考勤简报今天跑不了"

    broken = dingtalk_broken(cfg)
    if broken:
        return "dingtalk_login", broken

    rows = automation_rows()
    if not rows:
        return "app_db_unreadable", "Codex 的 automation 数据库读不出来，查不了排程还在不在"

    valid_slots: list[str] = []
    newest_run = 0
    for aid, row in rows.items():
        if row is None:
            return f"automation_missing_{aid}", f"定时任务 {aid} 在应用里找不到了"
        status, rrule, last_run_at, prompt = row
        if status != "ACTIVE":
            return f"automation_{status}_{aid}", f"定时任务 {aid} 现在是 {status}，不会自己跑"
        if str(CRON) not in (prompt or ""):
            return (f"script_path_changed_{aid}",
                    f"定时任务 {aid} 调的已经不是部署位那个脚本了")
        valid_slots += [s for s in beijing_slots(rrule or "") if s >= "17:15"]
        newest_run = max(newest_run, last_run_at or 0)

    if not valid_slots:
        return ("no_valid_slot",
                "两条定时任务换算成北京时间全都早于 17:15，简报永远不会发出去 —— "
                "多半是悉尼转了夏令时，rrule 的钟点要整体往后挪一小时")
    if len(valid_slots) < 2:
        return ("single_slot",
                f"北京时间只剩 {valid_slots[0]} 这一个有效触发点了，"
                f"第一趟出岔子就没有第二趟兜底")

    if newest_run:
        silent = (datetime.datetime.now().timestamp() - newest_run / 1000) / 3600
        if silent > MAX_SILENT_HOURS:
            return "not_triggered", f"两条定时任务已经 {silent:.0f} 小时没被触发过"

    prev = previous_workday(datetime.datetime.now(BEIJING).date()).isoformat()
    marks = day_markers(runtime_root / "logs" / "kmfa_brief_run.log", prev)
    if not marks:
        # 不去查 pmset 的睡醒记录来分辨「机器睡了」还是「Codex 没开」：
        # `pmset -g log` 实测 81 秒、80MB，而这两种情况对老板来说动作是同一个。
        return (f"no_conclusion_{prev}",
                f"上一个工作日（{prev}）的运行日志里一条结论都没有 —— 那天简报没发出去，"
                f"也没有任何东西报警。这条线只能靠 Codex 触发：机器睡着、"
                f"或者 Codex 桌面端没开，它就不会跑")
    bad = [m for m in marks if m in CONCLUSIVE_BAD]
    if bad and not any(m == "SEND_COMPLETED" for m in marks):
        return (f"last_run_failed_{prev}",
                f"上一个工作日（{prev}）最后停在 {bad[-1]}，简报没发出去")
    return None


def state_file(cfg: dict) -> Path:
    return Path(cfg.get("KMFA_BRIEF_RUNTIME_ROOT", "/tmp")).expanduser() / ".考勤看门狗状态.json"


def load_state(cfg: dict) -> dict:
    try:
        return json.loads(state_file(cfg).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(cfg: dict, value: dict) -> None:
    """共享盘上 os.rename 覆盖已存在的目标会报 EIO，而且目标会先没掉。
    所以先写临时文件、读回校验、删目标、再改名；失败就把临时文件收拾干净。"""
    path = state_file(cfg)
    body = json.dumps(value, ensure_ascii=False, indent=1) + "\n"
    tmp = path.with_name(f".{path.name}.write")
    try:
        with tmp.open("wb") as fh:
            fh.write(body.encode("utf-8"))
            fh.flush()
            os.fsync(fh.fileno())
        if tmp.read_text(encoding="utf-8") != body:
            tmp.unlink()
            return
        for _ in range(4):
            try:
                if path.exists():
                    path.unlink()
            except OSError:
                pass
            try:
                os.rename(str(tmp), str(path))
                return
            except OSError:
                continue
        tmp.unlink()
    except OSError:
        pass


def main() -> int:
    cfg = env()
    problem = find_problem(cfg)
    today = datetime.datetime.now(BEIJING).date().isoformat()
    if problem is None:
        save_state(cfg, {})
        print(f"WATCHDOG_OK 检查 {previous_workday(datetime.date.fromisoformat(today)).isoformat()}：正常")
        return 0
    key, message = problem
    if load_state(cfg).get("problem") == key:
        print(f"WATCHDOG_KNOWN problem={key}")
        return 0
    notify(f"考勤简报看门狗：{message}。", cfg)
    save_state(cfg, {"problem": key,
                     "at": datetime.datetime.now(BEIJING).replace(microsecond=0).isoformat()})
    print(f"WATCHDOG_ALERT problem={key} detail={message}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
