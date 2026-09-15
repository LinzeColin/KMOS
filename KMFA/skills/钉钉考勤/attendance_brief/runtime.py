"""运行态：pid 锁、墙钟上限、日志。

本机足迹只有两样，且都跑完即清：
  /tmp 下几十字节的 pid 锁（重启即失效）与 mktemp 临时工作目录。
锁不放 SMB —— SMB(CIFS) 上的文件锁语义不保证，放上去等于没锁。
"""
from __future__ import annotations
import os, sys, time, tempfile, shutil, contextlib
from pathlib import Path

_LOCKDIR = Path(tempfile.gettempdir())
LOCK = _LOCKDIR / "kmfa_attendance_brief.pid"   # 日报的锁，名字保持不变

class AlreadyRunning(RuntimeError):
    pass

@contextlib.contextmanager
def single_instance(name: str = ""):
    """三态：没锁 / 锁着且进程还活着 / 陈旧锁（进程已死，回收）。
    三种都发固定标记，调度侧不用猜。

    日报和周报各拿各的锁 —— 共用一把的话，周报卡住会把当天的日报一起挡掉，
    而这两件事之间没有任何依赖。
    """
    lock = _LOCKDIR / (f"kmfa_attendance_{name}.pid" if name else LOCK.name)
    if lock.exists():
        try:
            pid = int(lock.read_text().strip())
            os.kill(pid, 0)
            raise AlreadyRunning(f"另一个实例正在运行 (pid={pid})")
        except (ValueError, ProcessLookupError):
            emit("LOCK_STALE_RECLAIMED", "上一轮没清干净的锁，已回收")
            lock.unlink(missing_ok=True)
        except PermissionError:
            raise AlreadyRunning("另一个实例正在运行（锁属于别的用户）")
    lock.write_text(str(os.getpid()))
    emit("LOCK_ACQUIRED", f"pid={os.getpid()} lock={lock.name}")
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)

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

# 过程标记：只说明跑到哪一步了，不参与判读。其余一律算结论性标记。
# 前缀要写窄。第一版写了 "LOCK_"，把结论性的 LOCK_HELD（上一轮还在跑，本轮
# 什么都不做，属正常）也当成了过程标记 —— 于是 _LAST 一直是 None，收尾判成
# ESCALATE，调度侧每次撞锁都会误报故障。故障演练抓到的。
PROGRESS_PREFIX = ("RUN_START", "WEEKLY_START", "LOCK_ACQUIRED", "LOCK_STALE_RECLAIMED",
                   "ALARM_", "KMFILE_", "KMMEDIA_", "ARCHIVE_")
# 真的把东西发进群了才算 ACT。
ACT_TOKENS = ("SEND_COMPLETED", "WEEKLY_SENT")
_LAST = None                       # 最后一个结论性标记

def emit(token: str, msg: str = "") -> None:
    """机器读的固定标记 + 人读的中文，一行里都有。

    判读一律认 token。中文只给人看 —— 文案随时会改，改了不该影响调度侧的判读。
    顺手记住最后一个结论性标记，收尾时由 emit_action() 折成一行 ACTION。
    """
    global _LAST
    if not token.startswith(PROGRESS_PREFIX):
        _LAST = token
    line = f"{token}" + (f" | {msg}" if msg else "")
    print(f"[{time.strftime('%H:%M:%S')}] {line}", file=sys.stderr, flush=True)
    runlog(line)

def action() -> str:
    """把这一轮折成三个词之一。

    调度侧跑的是 SCNet 那个小模型，让它对着一张十几行的标记表做判读，
    等于把业务判断交给一个判不了的东西。所以判读在这里做完，
    automation 的 prompt 只剩一句「把最后那行 ACTION 抄到第一行」。
    """
    if _LAST is None:
        return "ESCALATE"                     # 一个结论性标记都没有 = 不知道发生了什么
    if _LAST in ACT_TOKENS:
        return "ACT"
    if _LAST.startswith(("SKIP_", "NOT_SENT_", "WATCHDOG_OK", "WATCHDOG_KNOWN")):
        return "NONE"
    if _LAST == "LOCK_HELD":                  # 上一轮还在跑，不是故障
        return "NONE"
    return "ESCALATE"

def emit_action() -> str:
    """整轮最后一行，固定形状 `ACTION: X`。包装脚本和调度侧都只认这一行。"""
    a = action()
    print(f"ACTION: {a}", file=sys.stderr, flush=True)
    runlog(f"ACTION: {a}")
    return a

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

# 老板定的：报文里不许出现这些词。2026-09-15 先定了前三个（说时长等于书面记录
# 公司自己的用工强度，压力给到公司而不是员工），2026-09-16 扩到全表 ——
# 要求是「哪怕员工拿着这些记录去举报，也是对公司有利的」。
# 所以报文只下排班指令，不做任何事实认定、不碰任何法律词。
# 闸放在**投递之前**，不是放在写文案的人的自觉上：以后谁改文案都漏不掉。
BANNED = ("加班", "工时", "小时", "劳动法", "仲裁", "违法", "超时", "疲劳",
          "连续工作", "未休", "旷工", "加班费", "法定", "赔偿", "举报")

def banned_words(text: str) -> list:
    return [w for w in BANNED if w in text]

# 干跑期间不发告警。干跑是人坐在终端前主动跑的验证，故障就在屏幕上，
# 再私聊一条只是打扰 —— 2026-09-16 共享盘掉线时，一次干跑就这么发出去一条。
# 排程跑失败才需要私聊，因为那时候没有人在看。
_QUIET = False

def quiet_alarms(on: bool = True) -> None:
    global _QUIET
    _QUIET = on

def alarm(dws: str, user_id: str, token: str, body: str) -> bool:
    """出事私聊张霖泽。ACTION: ESCALATE 只写在 Codex 桌面 app 的任务消息里，
    手机上看不见 —— 挂三天也没人知道。所以告警必须自己走钉钉私聊。"""
    if _QUIET:
        runlog(f"ALARM_SUPPRESSED | {token}（干跑，不打扰）")
        return False
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

# 已发送标记分两档，不是一个布尔。
#   完整 —— 拿到人员表、判完了考勤。这是终局，当天不会再发第二条。
#   降级 —— 17:15 时人员表还没到，只能发一条催办。这是临时的。
# 为什么要分：实测 44 个工作日里有 12 天人员表晚于 17:15 才发出来（最晚 17:52）。
# 旧写法把降级那条也当终局锁死，于是四天里有一天群里只有催办、永远等不到考勤结果。
# 现在降级之后，同一工作日后面的触发点（本机 20:15 / 21:15）会再看一眼，
# 人员表到了就补一条完整版并把标记升级成完整。一天最多两条。
FINAL, DEGRADED = "完整", "降级"

def peer_check(aid: str) -> str:
    """互查另一条 automation 还活着没有。返回空串表示正常，否则返回原因。

    **自己这条停了，自己报不了。** 看门狗跑在 automation-2 上，它守的是 automation；
    可 automation-2 整个停掉的时候，看门狗和周报是一起停的 —— 那一侧没有任何人会说话。
    所以反过来也要有一只眼睛：日报（automation）成功出报之后顺手看一眼 automation-2。
    两条互为看门狗，任何一条停了，另一条都会私聊报出来。

    只读 Codex 的应用库，查不了就返回空串 —— 看不到不等于出事，不制造噪音。
    """
    import sqlite3, datetime as _dt
    db = Path.home() / ".codex" / "sqlite" / "codex-dev.db"
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5)
        row = con.execute("select status, last_run_at from automations where id = ?",
                          (aid,)).fetchone()
        con.close()
    except Exception:
        return ""
    if row is None:
        return f"定时任务 {aid} 在 Codex 里找不到了 —— 周报和看门狗都不会再跑"
    status, last = row
    if status != "ACTIVE":
        return f"定时任务 {aid} 现在是 {status}，不会自己跑 —— 周报和看门狗都停了"
    if last:
        # 判据是「上一个工作日之前」，不是「多少小时」。这条线每工作日跑一次，
        # 周五跑完到周一隔着 72 小时 —— 按小时判每个周一都会误报，
        # 误报几次之后这条告警就没人看了，等于没有。
        last_d = _dt.datetime.fromtimestamp(last / 1000).date()
        d = _dt.date.today() - _dt.timedelta(days=1)
        while d.weekday() >= 5:                  # 往回跳过周末
            d -= _dt.timedelta(days=1)
        if last_d < d:
            return (f"定时任务 {aid} 上次触发还是 {last_d}，上一个工作日（{d}）"
                    f"整天都没跑 —— 周报和看门狗多半停了")
    return ""

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
