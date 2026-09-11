#!/usr/bin/env python3
"""红圈业务源每日导出：调红圈自己的导出接口，不点页面，文件不经过 Downloads。

automation ``kmfa-hongquan-daily`` 只调用本文件，不带参数。

一轮流程：探共享盘 → 加锁 → 先把暂存区与 Downloads 里的遗留件投递掉 →
逐个对象创建导出任务并等它完成 → 从华为云 OBS 直接下载到本机暂存区 →
校验（zip 头、字节数、行数都与服务端一致）→ 交给 ``hongquan_archive`` 投递共享盘、写清单、删暂存。

登录：从 Chrome 里已登录的红圈页面读一次登录信息（AppleScript 执行一行页面 JS），之后请求由本进程直接发；
token 只在内存的请求头里，不打印、不写盘、只发往 *.hecom.cn。没有红圈标签时脚本自己开一个，取完就关。
附件接口顺带返回的临时 OBS 凭据当场丢弃，只留 bucket / objectKey / endpoint；OBS 上的导出文件公共可读，直接下载。

automation 调 ``--background``：几秒内返回，第一行报上一轮最终结果 ``PREVIOUS <标记>``，
最后一行报本轮启动结果 ``EXPORT_STARTED`` / ``EXPORT_RUNNING`` / ``SMB_UNAVAILABLE`` / ``LAUNCH_FAILED``；导出在后台跑完。
不带参数时前台跑完整一轮，stdout 最后一行是唯一的固定标记：
  EXPORT_OK n=<件数>                      全部对象导出并归档          退出码 0
  EXPORT_LOCKED                           上一轮还在跑，本轮让路      退出码 0
  EXPORT_PARTIAL ok=<件数> failed=<对象>  部分对象失败，成功的已归档  退出码 2
  ARCHIVE_FAILED                          投递共享盘失败              退出码 2
  EXPORT_CRASHED <异常类名>               意外中断（已记终态并告警）  退出码 2
  SMB_UNAVAILABLE                         共享盘不可用                退出码 1
  HECOM_NO_TAB                            Chrome 里打不开红圈页面     退出码 3
  HECOM_LOGIN_REQUIRED                    红圈登录失效                退出码 3
失败时私聊机主一次（同一天同一标记只发一次）。

测试必须设 ``HONGQUAN_BASE``：归档根、Downloads、暂存区都落到临时目录，告警变成空操作。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, List, NamedTuple, Optional, Sequence, Tuple
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hongquan_archive as H  # noqa: E402


OWNER_USER = "01256723246324629191"
RUNTIME_DIR = Path.home() / ".local" / "share" / "kmfa-hongquan"
HECOM_TAB_PREFIX = "https://cloud.hecom.cn"
NO_TAB = "__KMFA_NO_HECOM_TAB__"
APP_VERSION = "0.0.4"
STATE_DONE = 4
STATE_FAILED = 5
POLL_SECONDS = 3
TASK_TIMEOUT_SECONDS = 30 * 60
CALL_TIMEOUT_SECONDS = 90
OBJECT_READY_SECONDS = 120
DOWNLOAD_ATTEMPTS = 3
PAGE_READY_SECONDS = 90
LOGIN_HINTS = re.compile(r"登录|token|过期|失效", re.I)
SECRET_LIKE = re.compile(r"[A-Za-z0-9+/=_\-]{20,}")


def redact(text: str) -> str:
    """写进日志、last_run.json 的文字：像凭据的长串一律打码，只留 200 字。"""

    return SECRET_LIKE.sub("***", str(text))[:200]
STATE_FIELDS = ["state", "totalCount", "exportedCount", "resultSize", "resultDesc"]
ATTACHMENT_FIELDS = ["bucket", "objectKey", "endpoint"]


class ObjectSpec(NamedTuple):
    label: str                      # 红圈对象名 = 导出文件名前缀，归档脚本按它分目录
    meta_name: str
    meta_id: int
    field_names: Tuple[str, ...]    # 与页面导出对话框的默认勾选一致（2026-09-11 逐列比对过）
    sort_field: str = "createdOn"
    conditions: Tuple[Dict, ...] = ()


# 「付款审批（日常费用）」对象下有三个业务类型。页面列表按菜单配置只显示「日常费用」
# （业务类型 id 300396893756；写法照页面 getFilter：值是 id 字符串数组），历史全部「全历史导出」
# 也只含它（1200→1256→1268→1276 行）。不加这个条件会混进两类销售费用，09-11 实测多 185 行。
DAILY_EXPENSE_ONLY = {
    "op": "in",
    "left": {"type": "field", "value": "CustomObject876__c.bizType"},
    "right": {"type": "value", "value": ["300396893756"]},
}

# 投标管理菜单下的「主合同」打开的就是项目管理的同一个对象 conContract3X，只导一次。
OBJECTS: Tuple[ObjectSpec, ...] = (
    ObjectSpec("主合同", "conContract3X", 2148736877, (
        "name", "contractNo", "createdOn", "field69__c", "customer", "field120__c", "stakeholder",
        "taxContractAmount", "taxRate", "totalSettlementAmount", "SettlementNoReceivingAmount", "field119__c",
        "totalInvoiceAmount", "invoiceNoReceivingAmount", "totalReceivingAmount", "guaranteeMoney",
        "field113__c", "field114__c", "field115__c", "field121__c", "appendix", "approvalStatus",
        "approvalUsers", "field73__c", "field125__c", "field126__c", "field128__c", "field127__c",
        "field130__c", "field132__c", "field131__c")),
    ObjectSpec("项目开票", "invoiceReg3X", 2148795131, (
        "name", "conContract.conContract3X.contractNo", "field1__c", "invoiceDate", "customer", "conContract",
        "taxAmount", "taxRate", "field15__c", "stakeholder", "approvalStatus", "createdOn")),
    ObjectSpec("收款登记", "collectionReg3X", 2148797900, (
        "name", "createdOn", "customer", "conContract", "receivingAmount", "receivingDate", "paymentMethod",
        "receivingType", "afterTotalReceivingAmount", "field4__c", "field3__c", "project.project3X.projectNo",
        "code", "conContract.conContract3X.invoiceNoReceivingAmount", "conContract.conContract3X.field20__c",
        "conContract.conContract3X.field12__c", "conContract.conContract3X.taxContractAmount",
        "conContract.conContract3X.contractAmount", "conContract.conContract3X.totalReceivingAmount",
        "conContract.conContract3X.field14__c", "conContract.conContract3X.field15__c",
        "conContract.conContract3X.field21__c", "field8__c", "conContract.conContract3X.contractNo",
        "project.project3X.stakeholder", "conContract.conContract3X.stakeholder", "project",
        "project.project3X.name", "conContract.conContract3X.project")),
    ObjectSpec("项目资金支出", "expReimbursement3X", 2148811230, (
        "name", "createdBy", "applicationDate", "field21__c", "field1__c", "receivingAccount", "field2__c",
        "actualPaymentAmount", "TaxAmount", "paymentStatus", "approvalStatus", "approvalUsers",
        "expenseRemark", "field15__c", "field14__c", "field13__c", "appendix", "bizType", "owner")),
    ObjectSpec("招标信息", "CustomObject1021__c", 300906589812, (
        "name", "approvalStatus", "field17__c", "createdOn", "field5__c", "field46__c", "field2__c",
        "field15__c", "field50__c", "field12__c", "field8__c", "field30__c"), sort_field="updatedOn"),
    ObjectSpec("投标记录", "bidInformation3X", 2156189500, (
        "name", "field11__c", "field35__c", "approvalStatus", "field17__c", "biddingResults",
        "resultDescription", "field69__c.CustomObject1411__c.field13__c",
        "field69__c.CustomObject1411__c.field5__c", "biddingAmount", "bidSecurity", "field54__c", "field56__c",
        "field64__c", "field61__c", "field62__c", "field66__c", "field50__c")),
    ObjectSpec("付款审批（日常费用）", "CustomObject876__c", 300396893680, (
        "name", "createdBy", "paymentStatus", "applicationDate", "field12__c", "field11__c",
        "actualPaymentAmount", "approvalStatus", "receivingAccount", "paymentContent", "remark", "owner"),
        conditions=(DAILY_EXPENSE_ONLY,)),
)


class ObjectFailed(Exception):
    """单个对象没导出成功；其余对象照常进行。"""


class NoHecomTab(Exception):
    """Chrome 里没有可用的红圈页面。"""


class LoginRequired(Exception):
    """红圈页面未登录或登录已失效。"""


# ── 请求体 ──────────────────────────────────────────────────────────

def fields_mapping(names: Sequence[str]) -> List[Dict]:
    """与页面 formateFieldsMapping 同构：普通字段逐个列出，关联字段 a.对象.b 按 a 合并成 subFields。"""

    mapping: List[Dict] = [{"field": name, "assignmentRole": ""} for name in names if "." not in name]
    grouped: Dict[str, List[str]] = {}
    for name in names:
        if "." in name:
            parts = name.split(".")
            grouped.setdefault(parts[0], []).append(parts[2])
    mapping.extend({"field": key, "subFields": value} for key, value in grouped.items())
    return mapping


def build_payload(spec: ObjectSpec) -> Dict:
    conditions = [dict(condition, key=index + 1) for index, condition in enumerate(spec.conditions)]
    return {
        "metaId": spec.meta_id,
        "filterSetting": {
            "scope": 1,
            "filter": {
                "conditions": conditions,
                "expr": " and ".join(str(item["key"]) for item in conditions),
                "conj": "advance",
                "metaId": spec.meta_id,
                "metaName": spec.meta_name,
            },
            "sorts": [{"field": spec.sort_field, "orderType": 0}],
            "exportTreeView": False,
            "exportFrontendSeqNo": False,
        },
        "fieldsMapping": fields_mapping(spec.field_names),
        "fileType": "xlsx",
        "keyWordSearchFields": [name for name in spec.field_names if "." not in name],
        "keyWord": "",
    }


def obs_url(attachment: Dict) -> str:
    """附件只认华为云 OBS；bucket、objectKey 形态不对一律拒收，不去陌生地址下载。"""

    bucket = str(attachment.get("bucket") or "")
    key = str(attachment.get("objectKey") or "")
    host = urllib.parse.urlparse(str(attachment.get("endpoint") or "")).netloc
    if (not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,62}", bucket)
            or not re.fullmatch(r"obs\.[a-z0-9-]+\.myhuaweicloud\.com", host)
            or not key or key.startswith("/") or ".." in key.split("/")):
        raise ObjectFailed("attachment_unexpected")
    return "https://%s.%s/%s" % (bucket, host, urllib.parse.quote(key))


# ── 红圈登录信息与请求 ──────────────────────────────────────────────

DEFAULT_AUTH_URL = "https://cloud1.hecom.cn/universe/"

AUTH_JS = """(function(){var a={};try{a=JSON.parse(localStorage.getItem('auth')||'{}')}catch(e){}
return JSON.stringify({ready:document.readyState,base:localStorage.getItem('authURL')||'',accessToken:a.accessToken||'',entCode:a.entCode||'',uid:String(a.uid||''),empCode:String(a.empCode||'')});})()"""

# 逐个红圈标签读；优先返回已登录的那个，全部未登录时返回最后一个未登录的，没有标签返回 NO_TAB。
OSA_READ_AUTH = r"""on run argv
  set js to item 1 of argv
  set fallback to ""
  tell application "Google Chrome"
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t) starts with "%s" then
          set out to execute t javascript js
          if out is not missing value then
            if out contains "\"accessToken\":\"\"" then
              set fallback to out
            else
              return out
            end if
          end if
        end if
      end repeat
    end repeat
  end tell
  if fallback is not "" then return fallback
  return "%s"
end run""" % (HECOM_TAB_PREFIX, NO_TAB)

OSA_OPEN_TAB = """tell application "Google Chrome"
  if (count of windows) = 0 then make new window
  set t to make new tab at end of tabs of window 1 with properties {URL:"%s/"}
  return id of t
end tell""" % HECOM_TAB_PREFIX

OSA_CLOSE_TAB = """on run argv
  set wanted to (item 1 of argv) as integer
  tell application "Google Chrome"
    repeat with w in windows
      repeat with t in tabs of w
        if id of t is wanted then
          close t
          return "closed"
        end if
      end repeat
    end repeat
  end tell
  return "gone"
end run"""


def _osascript(script: str, *args: str) -> str:
    try:
        done = subprocess.run(["/usr/bin/osascript", "-e", script] + list(args),
                              capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise NoHecomTab("osascript_unavailable") from exc
    if done.returncode != 0:
        raise NoHecomTab("osascript_failed:" + redact((done.stderr.strip().splitlines() or [""])[-1][:120]))
    out = done.stdout.strip()
    return "" if out == "missing value" else out


def read_page_auth() -> str:
    return _osascript(OSA_READ_AUTH, AUTH_JS)


def open_hecom_tab() -> str:
    return _osascript(OSA_OPEN_TAB)


def close_tab(tab_id: str) -> None:
    if re.fullmatch(r"\d+", tab_id or ""):
        try:
            _osascript(OSA_CLOSE_TAB, tab_id)
        except NoHecomTab:
            pass


class _RefuseRedirect(urllib.request.HTTPRedirectHandler):
    """红圈接口与 OBS 下载都不该跳转：一跳就当失败。urllib 默认跟随跳转时会把 accessToken 等请求头原样带到新主机。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(_RefuseRedirect)


def post_json(url: str, headers: Dict[str, str], body: Dict) -> Tuple[int, object]:
    request = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                                     headers=headers, method="POST")
    try:
        with _OPENER.open(request, timeout=CALL_TIMEOUT_SECONDS) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read()
    try:
        return status, json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return status, None


class HecomSession:
    """从 Chrome 里已登录的红圈页面借一次登录信息，之后请求全部由本进程直接发。

    09-11 第二轮实测：把请求放进页面、再轮询回读结果，只要用户自己也开着红圈（两个标签）
    或页面刷新一次，就会读错标签、读不到结果，一轮里三个对象超时。所以页面只用来取登录信息，
    整轮导出期间不再碰标签；脚本自己开的标签取完就关，停在未登录时留给人登录。
    """

    def __init__(self, reader: Callable[[], str] = read_page_auth, opener: Callable[[], str] = open_hecom_tab,
                 closer: Callable[[str], None] = close_tab,
                 sender: Optional[Callable[[str, Dict[str, str], Dict], Tuple[int, object]]] = None,
                 sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic):
        self.reader, self.opener, self.closer = reader, opener, closer
        self.sender = sender or post_json
        self.sleep, self.clock = sleep, clock
        self._auth: Dict[str, str] = {}
        self._base = ""

    def _page_auth(self) -> Optional[Dict]:
        raw = self.reader()
        if raw == NO_TAB:
            return None
        try:
            data = json.loads(raw)
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}

    def ensure_ready(self) -> None:
        data = self._page_auth()
        opened = ""
        if data is None:
            opened = self.opener() or ""
            deadline = self.clock() + PAGE_READY_SECONDS
            while not (data and (data.get("accessToken") or data.get("ready") == "complete")):
                if self.clock() > deadline:
                    self.closer(opened)
                    raise NoHecomTab("page_not_loaded")
                self.sleep(3)
                data = self._page_auth()
        if not data.get("accessToken"):
            raise LoginRequired()
        base = str(data.get("base") or DEFAULT_AUTH_URL).rstrip("/") + "/paas"
        parsed = urllib.parse.urlparse(base)
        if parsed.scheme != "https" or not parsed.netloc.endswith(".hecom.cn"):
            raise NoHecomTab("unexpected_base")
        self._base = base
        self._auth = {key: str(data.get(key) or "") for key in ("accessToken", "entCode", "uid", "empCode")}
        if opened:
            self.closer(opened)

    def _headers(self, path: str, obj: str) -> Dict[str, str]:
        headers = {"Content-Type": "application/json", "version": APP_VERSION, "clientTag": "web"}
        headers.update(self._auth)
        segments = path.split("/")
        if len(segments) > 2 and segments[1] == "app":
            headers.update({"app": segments[2], "act": "export", "obj": obj})
        return headers

    def call(self, path: str, body: Dict, obj: str, pick: Optional[List[str]]):
        if not self._auth:
            self.ensure_ready()
        for attempt in (1, 2):
            status, payload = self.sender(self._base + path, self._headers(path, obj), body)
            payload = payload if isinstance(payload, dict) else {}
            desc = str(payload.get("desc") or "")
            if status == 200 and str(payload.get("result")) == "0":
                data = payload.get("data")
                if pick is None:
                    return None if isinstance(data, (dict, list)) else data
                return {key: data[key] for key in pick if isinstance(data, dict) and key in data}
            if status in (401, 403) or LOGIN_HINTS.search(desc):
                if attempt == 1:
                    self.ensure_ready()        # 页面可能已经换过 token，重取一次
                    continue
                raise LoginRequired()
            raise ObjectFailed("%s:http%s:%s" % (path.rsplit("/", 1)[-1], status, redact(desc)))
        raise LoginRequired()


# ── 单个对象 ────────────────────────────────────────────────────────

def download_public(url: str, dest: Path) -> int:
    written = 0
    with _OPENER.open(url, timeout=300) as response, dest.open("wb") as handle:
        while True:
            block = response.read(1 << 20)
            if not block:
                break
            handle.write(block)
            written += len(block)
    return written


def remote_size(url: str) -> int:
    """OBS 上这份文件当前的字节数；还没出现或查不到返回 -1。"""

    try:
        with _OPENER.open(urllib.request.Request(url, method="HEAD"), timeout=60) as response:
            return int(response.headers.get("Content-Length") or -1)
    except (OSError, ValueError):
        return -1


def count_data_rows(path: Path) -> int:
    """流式数第一张表的行数（减表头），大文件也不整表进内存。"""

    with zipfile.ZipFile(path) as book:
        sheets = sorted(name for name in book.namelist()
                        if name.startswith("xl/worksheets/") and name.endswith(".xml"))
        if not sheets:
            raise ObjectFailed("no_sheet")
        rows = 0
        with book.open(sheets[0]) as handle:
            for _, element in ElementTree.iterparse(handle, events=("end",)):
                if element.tag.endswith("}row"):
                    rows += 1
                element.clear()
    return max(0, rows - 1)


def export_object(page: HecomSession, spec: ObjectSpec, staging: Path,
                  download: Optional[Callable[[str, Path], int]] = None,
                  probe: Optional[Callable[[str], int]] = None,
                  sleep: Callable[[float], None] = time.sleep,
                  clock: Callable[[], float] = time.monotonic) -> Tuple[Path, int]:
    download = download or download_public
    probe = probe or remote_size
    task = page.call("/app/std/export", build_payload(spec), spec.meta_name, None)
    if not re.fullmatch(r"\d+", str(task or "")):
        raise ObjectFailed("export_no_task")
    task_id = int(task)

    deadline = clock() + TASK_TIMEOUT_SECONDS
    while True:
        state = page.call("/app/std/getExportTaskState", {"taskId": task_id}, spec.meta_name, STATE_FIELDS) or {}
        if state.get("state") == STATE_DONE:
            break
        if state.get("state") == STATE_FAILED:
            raise ObjectFailed("export_failed:%s" % redact(state.get("resultDesc") or ""))
        if clock() > deadline:
            raise ObjectFailed("export_timeout")
        sleep(POLL_SECONDS)

    total = int(state.get("totalCount") or -1)
    if int(state.get("exportedCount") or -2) != total:
        raise ObjectFailed("exported_count_short")
    attachment = page.call("/app/std/getExportTaskResultAttachment", {"taskId": task_id},
                           spec.meta_name, ATTACHMENT_FIELDS) or {}
    url = obs_url(attachment)
    name = os.path.basename(str(attachment["objectKey"]))
    if not (name.startswith(spec.label + "_导出文件_") and name.endswith(".xlsx")):
        raise ObjectFailed("unexpected_file_name")

    expected = int(state.get("resultSize") or -1)
    part = staging / (name + ".part")
    try:
        # 服务端先报「完成」、OBS 上的文件后写完：09-11 主合同就在这个间隙里被下成了残件。
        # 所以先等 OBS 上的字节数与服务端一致再下；下完仍不一致就重下，最多三次。
        for _ in range(DOWNLOAD_ATTEMPTS):
            ready_deadline = clock() + OBJECT_READY_SECONDS
            while probe(url) != expected and clock() < ready_deadline:
                sleep(POLL_SECONDS)
            try:
                received = download(url, part)
            except OSError:
                received = -1
            if received == expected:
                break
        else:
            raise ObjectFailed("size_mismatch")
        with part.open("rb") as handle:
            if handle.read(4) != b"PK\x03\x04":
                raise ObjectFailed("not_xlsx")
        rows = count_data_rows(part)
        if rows != total:
            raise ObjectFailed("row_count_mismatch:%d/%d" % (rows, total))
        final = staging / name
        os.replace(str(part), str(final))
        return final, rows
    finally:
        if part.exists():
            part.unlink()


# ── 整轮 ────────────────────────────────────────────────────────────

ALERT_TEXT = {
    "SMB_UNAVAILABLE": "共享盘连不上，今天的红圈数据没有存进去。",
    "ARCHIVE_FAILED": "红圈数据导出了，但存共享盘失败；文件在本机暂存区，下一轮会自动补存。",
    "HECOM_NO_TAB": "Chrome 里打不开红圈页面（Chrome 没开，或页面加载不出来）。",
    "HECOM_LOGIN_REQUIRED": "红圈登录失效了，请在 Chrome 里重新登录一次 cloud.hecom.cn。",
    "EXPORT_PARTIAL": "有红圈对象没导出成功，其余已存进共享盘。",
    "EXPORT_CRASHED": "红圈导出脚本意外中断，本轮没做完；已下载的会在下一轮自动补存。",
    "LAUNCH_FAILED": "红圈导出没能在后台启动。",
}


def describe(exc: BaseException) -> str:
    """失败原因：自己抛的 ObjectFailed 与系统 I/O 错误保留原因（已打码），其余意外只留异常类名。"""

    if isinstance(exc, (ObjectFailed, OSError)):
        return "%s%s" % ("" if isinstance(exc, ObjectFailed) else type(exc).__name__ + ":", redact(str(exc)))
    return type(exc).__name__


def lock_holder_text(lock_path: Path) -> str:
    try:
        pid, started = lock_path.read_text(encoding="ascii").split()[:2]
        when = datetime.fromtimestamp(int(started), timezone(timedelta(hours=8))).strftime("%H:%M")
    except (OSError, ValueError):
        return ""
    return " pid=%s started=%s" % (pid, when)


def bj_today() -> str:
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d")


def alert_owner(marker: str) -> None:
    """私聊机主；同一天同一标记只发一次，免得一天三轮刷屏。"""

    head = marker.split(" ", 1)[0]
    stamp = RUNTIME_DIR / "alerted" / ("%s_%s" % (bj_today(), head))
    if stamp.exists():
        return
    text = "【红圈每日导出】%s\n标记：%s" % (ALERT_TEXT.get(head, "本轮没完成。"), marker)
    try:
        done = subprocess.run(["dws", "chat", "message", "send", "--user", OWNER_USER, "--text", text],
                              capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return
    if done.returncode == 0:
        stamp.parent.mkdir(parents=True, exist_ok=True)
        stamp.touch()


def runtime_dir() -> Path:
    base = os.environ.get("HONGQUAN_BASE")
    return Path(base).expanduser() if base else RUNTIME_DIR


def staging_dir() -> Path:
    override = os.environ.get("HONGQUAN_STAGING")
    return Path(override).expanduser() if override else runtime_dir() / "staging"


def record_last_run(marker: str, details: Sequence[str]) -> None:
    """记下本轮最终结果，下一次 automation 启动时第一行报出来。"""

    path = runtime_dir() / "last_run.json"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(json.dumps({
            "marker": marker,
            "finished_bj": datetime.now(timezone(timedelta(hours=8))).strftime("%m-%d %H:%M"),
            "details": list(details)[-20:],
        }, ensure_ascii=False), encoding="utf-8")
        os.replace(str(temporary), str(path))
    except OSError:
        pass


def read_last_run() -> Dict:
    try:
        data = json.loads((runtime_dir() / "last_run.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def finish(marker: str, code: int, alert: Callable[[str], None], details: Sequence[str] = ()) -> int:
    record_last_run(marker, details)
    if code != 0:
        alert(marker)
    print(marker)
    return code


def run(page: Optional[HecomSession] = None, alert: Optional[Callable[[str], None]] = None,
        objects: Sequence[ObjectSpec] = OBJECTS,
        download: Optional[Callable[[str, Path], int]] = None,
        probe: Optional[Callable[[str], int]] = None,
        sleep: Callable[[float], None] = time.sleep) -> int:
    downloads, archive_root = H.resolve_paths()
    if alert is None:
        alert = (lambda marker: None) if os.environ.get("HONGQUAN_BASE") else alert_owner
    try:
        H.ensure_archive_root(archive_root)
    except H.SmbUnavailable:
        return finish("SMB_UNAVAILABLE", 1, alert)

    lock_path = H.lock_path_for(archive_root)
    if not H.acquire_lock(lock_path):
        print("EXPORT_LOCKED")
        return 0
    try:
        return _run_locked(page, alert, objects, download, probe, sleep, downloads, archive_root, staging_dir())
    except Exception as exc:  # 兜底：没预料到的异常也要落终态、告警，不能只在日志里留一段 traceback
        return finish("EXPORT_CRASHED %s" % type(exc).__name__, 2, alert)
    finally:
        H.release_lock(lock_path)


def _run_locked(page, alert, objects, download, probe, sleep, downloads: Path, archive_root: Path, staging: Path) -> int:
    details: List[str] = []

    def say(line: str) -> None:
        details.append(line)
        print(line)

    try:
        staging.mkdir(parents=True, exist_ok=True)
        for leftover in staging.glob("*.part"):
            leftover.unlink()
        manual, quarantined = H.split_valid(H.candidate_sources(downloads), runtime_dir() / "quarantine")
        for name in quarantined:
            say("DETAIL Downloads 里的 %s 不是完整的红圈导出，已移到隔离区、没有入库" % name)
        pending = H.candidate_sources(staging) + manual
        if pending:
            say("DETAIL 先投递遗留件 %d 份" % len(pending))
            H.archive_sources(pending, archive_root)
    except (H.ArchiveFailure, OSError, ValueError):
        return finish("ARCHIVE_FAILED", 2, alert, details)

    page = page or HecomSession()
    failed: List[str] = []
    blocker = ""
    try:
        page.ensure_ready()
        for spec in objects:
            started = time.monotonic()
            try:
                _, rows = export_object(page, spec, staging, download=download, probe=probe, sleep=sleep)
                say("DETAIL %s rows=%d secs=%.0f" % (spec.label, rows, time.monotonic() - started))
            except (NoHecomTab, LoginRequired):
                raise
            except Exception as exc:  # 单个对象的任何意外只算这个对象失败，其余照常
                failed.append(spec.label)
                say("DETAIL %s failed=%s" % (spec.label, describe(exc)))
    except NoHecomTab as exc:
        blocker = "HECOM_NO_TAB"
        say("DETAIL %s" % (str(exc)[:200] or "no_tab"))
    except LoginRequired:
        blocker = "HECOM_LOGIN_REQUIRED"

    try:
        staged = H.candidate_sources(staging)
        archived = H.archive_sources(staged, archive_root) if staged else 0
    except (H.ArchiveFailure, OSError, ValueError):
        return finish("ARCHIVE_FAILED", 2, alert, details)
    if blocker:
        return finish(blocker, 3, alert, details)
    if failed:
        return finish("EXPORT_PARTIAL ok=%d failed=%s" % (archived, ",".join(failed)), 2, alert, details)
    return finish("EXPORT_OK n=%d" % archived, 0, alert, details)


def launch_background(spawn: Optional[Callable[..., object]] = None) -> int:
    """automation 用的入口：几秒内返回，导出挂到后台跑完。

    Codex 的命令工具 10 秒就返回，之后每 10–30 秒要模型轮询一次；七分钟的导出会烧掉十几轮完整上下文
    （SCNet 不缓存）。所以前台只做四件事：报上一轮结果、探共享盘、看锁、把导出挂到后台。
    后台进程脱离 automation 会话，并由 caffeinate 顶住，整轮期间 Mac 不进入闲置睡眠。
    """

    previous = read_last_run()
    print("PREVIOUS %s%s" % (previous.get("marker") or "NONE",
                             (" finished=%s" % previous["finished_bj"]) if previous.get("finished_bj") else ""))
    for line in previous.get("details") or []:
        print("PREVIOUS_%s" % line)

    _, archive_root = H.resolve_paths()
    alert = (lambda marker: None) if os.environ.get("HONGQUAN_BASE") else alert_owner
    try:
        H.ensure_archive_root(archive_root)
    except H.SmbUnavailable:
        return finish("SMB_UNAVAILABLE", 1, alert)
    lock_path = H.lock_path_for(archive_root)
    if H.holder_is_alive(lock_path):
        print("EXPORT_RUNNING%s" % lock_holder_text(lock_path))
        return 0

    command = [sys.executable, str(Path(__file__).resolve())]
    if Path("/usr/bin/caffeinate").exists():
        command = ["/usr/bin/caffeinate", "-i"] + command
    try:
        logs = runtime_dir() / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        for old in sorted(logs.glob("*.log"))[:-30]:
            old.unlink()
        log = logs / (datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d_%H%M%S") + ".log")
        with log.open("ab") as handle:
            child = (spawn or subprocess.Popen)(command, stdin=subprocess.DEVNULL, stdout=handle,
                                               stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
    except OSError as exc:
        return finish("LAUNCH_FAILED %s" % type(exc).__name__, 2, alert)
    print("EXPORT_STARTED pid=%s log=%s" % (getattr(child, "pid", "?"), log))
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    # 输出进管道或日志文件时默认整块缓冲，几分钟里一行都看不到会被当成卡死；逐行刷出。
    sys.stdout.reconfigure(line_buffering=True)
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["--background"]:
        return launch_background()
    if args:
        print("用法：hongquan_export.py [--background]")
        return 64
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
