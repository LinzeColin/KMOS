"""出报前的前置归档：KMFile（文件）+ KMMedia（图片/视频）。

**只归档考勤自己那一个群。** KMFile / KMMedia 作为独立的每日任务是全公司全群全类型的，
那是它们自己的职责；考勤简报只是调用方，管好自己的生产管理群就行 ——
为了出一份考勤报去跑一轮全公司归档，既慢（实测单轮 20 分钟以上）也不是它该扛的。

命令行固定带 `--only-group <群名> --since-manifest`：
  · `--since-manifest` 是日增量入口。不带它会从 2025-01-01 全量回填，回填不许进调度。
  · `--refresh-groups` / `--include-new-groups` 不带 —— 有 `--only-group` 时 pipeline
    直接忽略它们（源码 `if args.refresh_groups and not args.only_group`）。
  · `--window-days` 只有 kmfile 有，kmvideo 没有，所以两边都不传。
  · 底层的 archive_internal_files.py / archive_internal_media.py 不用，它们的
    `--allow-title` 是 required，参数形态完全不同。

三个踩过或差点踩的坑，写在这里免得以后改回去：

1. **子进程输出不许走 subprocess.PIPE。** 只在最后 read()，输出一超过管道缓冲
   （约 64KB）子进程就会阻塞在写上，永远等不到我们去读 —— 归档十几分钟的日志量
   轻松超过。改成直连临时文件，事后读尾巴；被超时打断也还能拿到尾巴。
2. **超时用 SIGTERM，不是 SIGKILL。** pipeline 收到 TERM 会写完当前 manifest 窗口再退；
   直接 -9 会把 manifest 写坏。给 20 秒宽限，赖着不走才升级到 KILL。
3. **被别人的锁挡住时也要认出来。** 实测两个 pipeline 被活锁挡住时退出码是 1
   （不是 0），但这条不能只靠退出码 —— 日志里那句「另一个 pipeline 实例仍在运行」
   才是确证，单独识别成 KMFILE_LOCKED / KMMEDIA_LOCKED，别混进 FAILED。
   陈旧锁（持有者已死）上游 acquire_workdir_lock 自己会用 kill -0 收掉，实测确认，这里不重复做。

workdir 用 pipeline 的默认值，跟每日全量任务共用同一份 manifest 与登记表，
`--since-manifest` 的增量水位才是连续的。代价是撞上正在跑的全量任务会被锁挡，
那种情况发 LOCKED 标记继续出报，不阻断。

归档失败绝不阻断简报 —— 简报才是交付物。
"""
from __future__ import annotations
import os, subprocess, tempfile, time
from pathlib import Path

from . import runtime

LOCKED_MARK = "另一个 pipeline 实例仍在运行"
TERM_GRACE = 20                     # SIGTERM 后给它写完 manifest 的宽限（秒）

# 只跑 scan 阶段，不跑 all。
# scan 就是「把这个群的新原件抓下来归档进 SMB」—— 考勤要的就是这个。
# all 后面那串 probe / thumbs / dedup / label / rename / registry / upload
# 是 KMFile、KMVideo 两个产品自己的编目流程，跟出一份考勤报没关系，
# 而且慢得离谱：2026-09-07 实测 kmmedia 的 scan 只要 4 分 36 秒，
# 接着 thumbs 一个阶段跑了 22 分钟还没完（109 个媒体逐张 rsync 到 SMB 再 stat 回来）。
# 编目该由它们各自 03:15 / 03:30 的每日任务去做，那里有的是时间。
#
# 注意这不是缩小归档范围：群、类型、对象一个没少，少的只是下游编目步骤。
STAGE = "scan"

JOBS = (
    ("KMFILE", "~/.codex/skills/KMFile-Archive/scripts/kmfile_pipeline.py"),
    ("KMMEDIA", "~/.codex/skills/KMMedia-Archive/scripts/kmvideo_pipeline.py"),
)

def _finish(name: str, proc, log: Path, started: float) -> None:
    took = int(time.time() - started)
    text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    tail = text.strip().splitlines()[-1:]
    last = tail[0][:200] if tail else ""
    if LOCKED_MARK in text:
        runtime.emit(f"{name}_LOCKED", f"{took} 秒 · 被另一轮归档的锁挡住，本轮跳过 · {last}")
    elif proc.returncode == 0:
        runtime.emit(f"{name}_OK", f"{took} 秒 · {last}")
    else:
        runtime.emit(f"{name}_FAILED", f"退出码 {proc.returncode} · {took} 秒 · {last}")

def run(group_title: str, budget: int, python: str = "python3") -> None:
    """并发跑两个归档，只跑 group_title 这一个群，合计不超过 budget 秒。
    只发标记，不抛异常，不阻断调用方。"""
    try:
        _run(group_title, budget, python)
    except Exception as e:
        # 「不抛异常」是本模块对调用方的承诺，这里把它兑现成代码而不是注释。
        # run() 在入口那个 try 之外被调用，一旦漏出异常，整个进程会带着
        # traceback 退出：简报没发、没有结论标记、手机上也没有告警。
        # 归档只是出报前的热身，永远不值得用它换掉简报本身。
        runtime.emit("ARCHIVE_ABORTED",
                     f"{type(e).__name__}: {e} · 跳过归档，继续出报")

def _run(group_title: str, budget: int, python: str) -> None:
    live, logs = [], []
    for name, rel in JOBS:
        script = Path(rel).expanduser()
        if not script.exists():
            runtime.emit(f"{name}_FAILED", f"找不到 {script}")
            continue
        # --no-private 只跳过 upload 阶段里「往私有资料库推」那一步
        # （源码 stage_upload: `if args.no_private: res["private"] = "skip"`），
        # 下载、归档、去重、登记全都照跑 —— 它不缩小归档范围，只少了一个推送目的地。
        # 加它的原因：pipeline 找的是 $KMOS_ROOT/machine/tools/private_db_client.py，
        # 而这台机器上根本没有那个文件（真件在 MetaDatabase/EEI 和 AgentDatabase 下），
        # 于是每轮都在 upload 阶段 RuntimeError 退出 —— 2026-09-07 实测 146 秒后必挂。
        # 推私有库是归档线自己每日任务的职责，不是考勤简报该扛的。
        cmd = [python, str(script), STAGE, "--only-group", group_title,
               "--since-manifest", "--no-private"]
        fd, path = tempfile.mkstemp(prefix=f"kmfa_{name.lower()}_", suffix=".log")
        log = Path(path); logs.append(log)
        runtime.emit(f"{name}_START", " ".join(cmd))
        # 直连文件，不走 PIPE：输出量大时 PIPE 会把子进程堵死。
        proc = subprocess.Popen(cmd, stdout=fd, stderr=subprocess.STDOUT)
        os.close(fd)                            # 子进程已 dup，父进程这份要还掉
        live.append((name, proc, log, time.time()))

    try:
        t0 = time.time()
        while live:
            if time.time() - t0 >= budget:
                for name, p, log, started in live:
                    p.terminate()                       # SIGTERM，让它写完 manifest
                    try:
                        p.wait(timeout=TERM_GRACE)
                    except subprocess.TimeoutExpired:
                        p.kill()                        # 赖着不走才升级
                        try:
                            p.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            # SIGKILL 都收不走，多半卡在 SMB 的不可中断 IO（D 态）。
                            # 这里再抛出去就会连累简报，所以只记一笔，不等了。
                            runtime.emit(f"{name}_TIMEOUT",
                                         "SIGKILL 后仍未退出，不再等，继续出报")
                            continue
                    runtime.emit(f"{name}_TIMEOUT",
                                 f"合计 {budget} 秒预算用尽，已 SIGTERM 收尾，继续出报")
                return
            for item in list(live):
                name, p, log, started = item
                if p.poll() is None:
                    continue
                live.remove(item)
                _finish(name, p, log, started)
            if live:
                time.sleep(2)
    finally:
        for log in logs:
            log.unlink(missing_ok=True)
