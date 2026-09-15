"""运行态：pid 锁、墙钟上限、日志。

本机足迹只有两样，且都跑完即清：
  /tmp 下几十字节的 pid 锁（重启即失效）与 mktemp 临时工作目录。
锁不放 SMB —— SMB(CIFS) 上的文件锁语义不保证，放上去等于没锁。
"""
from __future__ import annotations
import os, sys, time, tempfile, shutil, contextlib
from pathlib import Path

LOCK = Path(tempfile.gettempdir()) / "kmfa_attendance_brief.pid"

class AlreadyRunning(RuntimeError):
    pass

@contextlib.contextmanager
def single_instance():
    """三态：没锁 / 锁着且进程还活着 / 陈旧锁（进程已死，回收）。
    三种都发固定标记，调度侧不用猜。"""
    if LOCK.exists():
        try:
            pid = int(LOCK.read_text().strip())
            os.kill(pid, 0)
            raise AlreadyRunning(f"另一个实例正在运行 (pid={pid})")
        except (ValueError, ProcessLookupError):
            emit("LOCK_STALE_RECLAIMED", "上一轮没清干净的锁，已回收")
            LOCK.unlink(missing_ok=True)
        except PermissionError:
            raise AlreadyRunning("另一个实例正在运行（锁属于别的用户）")
    LOCK.write_text(str(os.getpid()))
    emit("LOCK_ACQUIRED", f"pid={os.getpid()}")
    try:
        yield
    finally:
        LOCK.unlink(missing_ok=True)

@contextlib.contextmanager
def workdir():
    d = Path(tempfile.mkdtemp(prefix="kmfa_brief_"))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)

class Deadline:
    """墙钟上限。超时是终局：记 ABORTED_TIMEOUT，不发送、不补发。"""
    def __init__(self, seconds: int):
        self.t0, self.limit = time.time(), seconds
    @property
    def left(self) -> float:
        return self.limit - (time.time() - self.t0)
    def check(self, stage: str):
        if self.left <= 0:
            raise TimeoutError(f"ABORTED_TIMEOUT at {stage}")

def smb_write(text: str, dest: Path) -> None:
    """写 SMB：先写本机临时文件再 rsync 过去，写后校验非全 0。
    直接 cp 到 SMB 会静默写出全 0（字节数对、不报错、内容空白）。"""
    import subprocess
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".tmp", delete=False,
                                     encoding="utf-8") as f:
        f.write(text); tmp = Path(f.name)
    try:
        subprocess.run(["rsync", "-t", str(tmp), str(dest)], check=True,
                       capture_output=True, timeout=120)
        data = dest.read_bytes()
        if not data or set(data) == {0}:
            raise IOError(f"SMB 写出全 0 或空文件: {dest}")
    finally:
        tmp.unlink(missing_ok=True)

_RUNLOG: "Path | None" = None
MAXLOG = 2_000_000          # 超过就砍掉前半，SMB 上不能无限长

def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)

def emit(token: str, msg: str = "") -> None:
    """机器读的固定标记 + 人读的中文，一行里都有。

    判读一律认 token。中文只给人看 —— 文案随时会改，改了不该影响调度侧的判读。
    """
    line = f"{token}" + (f" | {msg}" if msg else "")
    print(f"[{time.strftime('%H:%M:%S')}] {line}", file=sys.stderr, flush=True)
    runlog(line)

def runlog_init(root) -> None:
    """运行日志落 SMB，跟其余产出同一个盘。出事能直接贴最后 30 行。"""
    global _RUNLOG
    try:
        d = root / "logs"; d.mkdir(parents=True, exist_ok=True)
        _RUNLOG = d / "kmfa_brief_run.log"
    except Exception:
        _RUNLOG = None

def runlog(line: str) -> None:
    if _RUNLOG is None:
        return
    try:
        if _RUNLOG.exists() and _RUNLOG.stat().st_size > MAXLOG:
            keep = _RUNLOG.read_text(encoding="utf-8", errors="replace")[MAXLOG // 2:]
            _RUNLOG.write_text(keep, encoding="utf-8")
        with _RUNLOG.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {line}\n")
    except Exception:
        pass                                  # 日志写不进去不能拖垮正事

def smb_ready(*roots) -> str:
    """SMB 掉了要在第一步就认出来，而不是等 python 在中途以随机方式炸。
    人员表图片、花名册缓存、台账、归档、运行日志全在共享盘上。
    返回空串表示可用，否则返回原因。"""
    for r in roots:
        try:
            r.mkdir(parents=True, exist_ok=True)
            probe = r / ".kmfa_write_probe"
            probe.write_text("ok", encoding="utf-8")
            if probe.read_text(encoding="utf-8") != "ok":
                return f"{r} 写进去读不回来（SMB 静默写空）"
            probe.unlink(missing_ok=True)
        except Exception as e:
            return f"{r} 不可用: {type(e).__name__} {e}"
    return ""

# 老板 2026-09-15 定的：报文里不许出现这三个词。
# 说时长就是在书面记录公司自己的用工强度，压力给到公司而不是员工 ——
# 考勤简报要的是「谁该补卡、谁该调休」，不是「谁干了多久」。
# 闸放在**投递之前**，不是放在写文案的人的自觉上：以后谁改文案都漏不掉。
BANNED = ("加班", "工时", "小时")

def banned_words(text: str) -> list:
    return [w for w in BANNED if w in text]

def alarm(dws: str, user_id: str, token: str, body: str) -> bool:
    """出事私聊张霖泽。ACTION: ESCALATE 只写在 Codex 桌面 app 的任务消息里，
    手机上看不见 —— 挂三天也没人知道。所以告警必须自己走钉钉私聊。"""
    if not (dws and user_id):
        return False
    import subprocess
    try:
        r = subprocess.run([dws, "chat", "message", "send", "--user", user_id,
                            "--title", f"⚠ 考勤简报故障 · {token}",
                            "--text", body], capture_output=True, timeout=60)
        ok = r.returncode == 0
        runlog(f"ALARM_SENT | {token}" if ok else f"ALARM_FAILED | {token}")
        return ok
    except Exception as e:
        runlog(f"ALARM_FAILED | {token} | {type(e).__name__}")
        return False

def _marker(root, day: str):
    return root / "已发送" / f"{day}.txt"

# 已发送标记分两档，不是一个布尔。
#   完整 —— 拿到人员表、判完了考勤。这是终局，当天不会再发第二条。
#   降级 —— 17:15 时人员表还没到，只能发一条催办。这是临时的。
# 为什么要分：实测 44 个工作日里有 12 天人员表晚于 17:15 才发出来（最晚 17:52）。
# 旧写法把降级那条也当终局锁死，于是四天里有一天群里只有催办、永远等不到考勤结果。
# 现在降级之后，同一工作日后面的触发点（本机 20:15 / 21:15）会再看一眼，
# 人员表到了就补一条完整版并把标记升级成完整。一天最多两条。
FINAL, DEGRADED = "完整", "降级"

def _marker(root, day: str):
    return root / "已发送" / f"{day}.txt"

def sent_kind(root, day: str):
    """返回 None / "降级" / "完整"。

    老标记（2026-09-15 之前写的）里没有这个字段，一律当「完整」——
    那些天本来就都发出去了，把它们当成降级会在升级上线当天重发一轮历史。
    """
    m = _marker(root, day)
    try:
        if not m.exists():
            return None
        return DEGRADED if DEGRADED in m.read_text(encoding="utf-8", errors="replace") else FINAL
    except OSError:
        # 读不出来就当已发过。宁可漏发一天，也不能因为共享盘抖一下就重发进群。
        return FINAL

def already_sent(root, day: str) -> bool:
    return sent_kind(root, day) is not None

def mark_sent(root, day: str, note: str, kind: str = FINAL) -> None:
    smb_write(f"{note.rstrip()} · {kind}\n", _marker(root, day))
