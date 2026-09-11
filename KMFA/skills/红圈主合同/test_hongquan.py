#!/usr/bin/env python3
"""红圈业务源导出与归档的离线测试。

不碰 Chrome、不碰共享盘、不碰 ~/Downloads、不发钉钉：导入前先把 HONGQUAN_BASE 指到临时目录，
归档根、Downloads、暂存区全部落在里面；红圈接口与下载用脚本化的假页面代替。

运行：/usr/bin/python3 test_hongquan.py
"""

import io
import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

TMP = Path(tempfile.mkdtemp(prefix="hongquan-test-"))
os.environ["HONGQUAN_BASE"] = str(TMP)
for name in ("HONGQUAN_STAGING", "HONGQUAN_ARCHIVE_ROOT", "HONGQUAN_DOWNLOADS"):
    os.environ.pop(name, None)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hongquan_archive as H  # noqa: E402
import hongquan_export as E  # noqa: E402


def forbid_network(*_args, **_kwargs):
    raise AssertionError("测试不许真的访问网络")


E.download_public = E.remote_size = forbid_network

PASSED = 0
FAILED = []


def check(name, condition, detail=""):
    global PASSED
    if condition:
        PASSED += 1
        print("  PASS  " + name)
    else:
        FAILED.append(name)
        print("  FAIL  %s %s" % (name, detail))


def section(title):
    print("\n== %s ==" % title)


def make_xlsx(header, rows):
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    strings, index = [], {}

    def sid(value):
        if value not in index:
            index[value] = len(strings)
            strings.append(value)
        return index[value]

    def col(i):
        letters, i = "", i + 1
        while i:
            i, rem = divmod(i - 1, 26)
            letters = chr(65 + rem) + letters
        return letters

    body = []
    for r, row in enumerate([header] + rows, start=1):
        cells = "".join('<c r="%s%d" t="s"><v>%d</v></c>' % (col(c), r, sid(v)) for c, v in enumerate(row))
        body.append('<row r="%d">%s</row>' % (r, cells))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as book:
        book.writestr("xl/worksheets/sheet1.xml",
                      '<?xml version="1.0"?><worksheet xmlns="%s"><sheetData>%s</sheetData></worksheet>'
                      % (ns, "".join(body)))
        book.writestr("xl/sharedStrings.xml", '<?xml version="1.0"?><sst xmlns="%s">%s</sst>'
                      % (ns, "".join("<si><t>%s</t></si>" % escape(s) for s in strings)))
    return buf.getvalue()


def sample(spec, n=3):
    if spec.label == "付款审批（日常费用）":
        return make_xlsx(["付款编号", "申请日期"], [["P%d" % i, "202%d-01-01" % (4 + i % 2)] for i in range(n)])
    if spec.label == "收款登记":
        return make_xlsx(["收款编号", "收款日期"], [["S%d" % i, "202%d-02-02" % (4 + i % 2)] for i in range(n)])
    return make_xlsx(["编号", "名称"], [["N%d" % i, "x"] for i in range(n)])


def spec_of(label):
    return next(s for s in E.OBJECTS if s.label == label)


def reset():
    for child in TMP.iterdir():
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    (TMP / "Downloads").mkdir()


def month_dir():
    return TMP / H.shanghai_now().strftime("%Y%m") / "红圈"


class FakePage:
    """脚本化的红圈接口：按对象返回任务、状态、附件；记录每次调用。"""

    def __init__(self, rows=3, claim=None, fail=(), state5=(), login_after=None, no_tab=False,
                 probe_lag=0, short_downloads=0):
        self.rows, self.claim = rows, claim
        self.probe_lag, self.short_downloads, self.probes, self.downloads = probe_lag, short_downloads, 0, 0
        self.fail, self.state5 = set(fail), set(state5)
        self.login_after, self.no_tab = login_after, no_tab
        self.calls, self.blobs, self.exports = [], {}, 0

    def ensure_ready(self):
        if self.no_tab:
            raise E.NoHecomTab("no_tab")

    def call(self, path, body, obj, pick):
        self.calls.append((path, obj, pick))
        spec = next(s for s in E.OBJECTS if s.meta_name == obj)
        if path.endswith("/export"):
            self.exports += 1
            if self.login_after is not None and self.exports > self.login_after:
                raise E.LoginRequired()
            if spec.label in self.fail:
                raise E.ObjectFailed("export:rejected")
            task = 900000 + self.exports
            self.blobs[task] = sample(spec, self.rows)
            return task
        if path.endswith("/getExportTaskState"):
            if spec.label in self.state5:
                return {"state": 5, "resultDesc": "筛选条件配置有误"}
            count = self.rows if self.claim is None else self.claim
            return {"state": 4, "totalCount": count, "exportedCount": count,
                    "resultSize": len(self.blobs[body["taskId"]])}
        if path.endswith("/getExportTaskResultAttachment"):
            return {"bucket": "hwhq-cloud-file", "endpoint": "https://obs.cn-north-4.myhuaweicloud.com",
                    "objectKey": "KM_888/%s/%s_导出文件_%d.xlsx" % (obj, spec.label, body["taskId"])}
        raise AssertionError(path)

    def blob(self, url):
        return self.blobs[int(url.rsplit("_", 1)[1].split(".")[0])]

    def probe(self, url):
        self.probes += 1
        return -1 if self.probes <= self.probe_lag else len(self.blob(url))

    def download(self, url, dest):
        self.downloads += 1
        data = self.blob(url)
        if self.downloads <= self.short_downloads:
            data = data[: len(data) // 2]
        dest.write_bytes(data)
        return len(data)


def no_sleep(_seconds):
    return None


# ── 一 ──────────────────────────────────────────────────────────────
section("一、归档：写坏的残件不再卡住整批（09-11 的 0 字节空壳）")
reset()
now = H.shanghai_now()
ym, day = now.strftime("%Y%m"), now.strftime("%Y%m%d")
data = sample(spec_of("招标信息"), 5)
src = TMP / "Downloads" / "招标信息_导出文件_1.xlsx"
src.write_bytes(data)
target_dir = month_dir() / "招标信息"
target_dir.mkdir(parents=True)
name = H.output_filename(src, "招标信息", ym, day, False)
(target_dir / name).write_bytes(b"")
real_rsync, writes = H.run_rsync, []


def flaky(source, target):
    writes.append(target)
    if len(writes) == 1:
        Path(target).write_bytes(b"")
        return
    real_rsync(source, target)


H.run_rsync = flaky
rc = H.run(False)
H.run_rsync = real_rsync
check("同名位置上的 0 字节空壳被当成没写成、原地重写", (target_dir / name).read_bytes() == data)
check("不另起带 md5 后缀的新名", sorted(p.name for p in target_dir.iterdir()) == [name])
check("第一次写坏会自动再写一次，最终成功", rc == 0 and len(writes) >= 2)
check("投递成功后源件删除", not src.exists())

src2 = TMP / "Downloads" / "投标记录_导出文件_2.xlsx"
src2.write_bytes(sample(spec_of("投标记录")))
H.run_rsync = lambda source, target: Path(target).write_bytes(b"")
rc = H.run(False)
H.run_rsync = real_rsync
bid_dir = month_dir() / "投标记录"
check("一直写坏：退出码 2", rc == 2)
check("一直写坏：共享盘不留残件", not bid_dir.exists() or not any(bid_dir.iterdir()))
check("一直写坏：源件保留等下一轮", src2.exists())
rc = H.run(False)
check("写通道恢复后下一轮补投成功", rc == 0 and not src2.exists() and any(bid_dir.iterdir()))

# ── 二 ──────────────────────────────────────────────────────────────
section("二、导出请求与页面一致")
payload = E.build_payload(spec_of("付款审批（日常费用）"))
conditions = payload["filterSetting"]["filter"]["conditions"]
check("付款审批只导业务类型「日常费用」", len(conditions) == 1
      and "bizType" in json.dumps(conditions) and "300396893756" in json.dumps(conditions))
check("条件编号与表达式对得上", payload["filterSetting"]["filter"]["expr"] == "1" and conditions[0]["key"] == 1)
check("其余六个对象不加任何筛选（全量）",
      all(E.build_payload(s)["filterSetting"]["filter"]["conditions"] == []
          for s in E.OBJECTS if s.label != "付款审批（日常费用）"))
mapping = E.fields_mapping(["name", "conContract", "conContract.conContract3X.contractNo",
                            "conContract.conContract3X.project"])
check("关联字段按页面规则合并成 subFields", mapping == [
    {"field": "name", "assignmentRole": ""}, {"field": "conContract", "assignmentRole": ""},
    {"field": "conContract", "subFields": ["contractNo", "project"]}])
check("七个对象、名字不重复（投标管理的主合同与项目管理是同一对象，只导一次）",
      len(E.OBJECTS) == 7 and len({s.label for s in E.OBJECTS}) == 7
      and len({s.meta_name for s in E.OBJECTS}) == 7)
check("每个对象的导出文件名都能被归档脚本认到自己的目录",
      all(H.classify_source(Path("%s_导出文件_1.xlsx" % s.label)) == s.label for s in E.OBJECTS))
good = E.obs_url({"bucket": "hwhq-cloud-file", "endpoint": "https://obs.cn-north-4.myhuaweicloud.com",
                  "objectKey": "KM_888/invoiceReg3X/项目开票_导出文件_1.xlsx"})
check("附件地址拼成华为云 OBS 公共地址",
      good.startswith("https://hwhq-cloud-file.obs.cn-north-4.myhuaweicloud.com/KM_888/invoiceReg3X/"))
for bad in ({"bucket": "hwhq-cloud-file", "endpoint": "https://evil.example.com", "objectKey": "a.xlsx"},
            {"bucket": "hwhq-cloud-file", "endpoint": "https://obs.cn-north-4.myhuaweicloud.com.evil.com",
             "objectKey": "a.xlsx"},
            {"bucket": "hwhq-cloud-file", "endpoint": "https://obs.cn-north-4.myhuaweicloud.com",
             "objectKey": "KM_888/../a.xlsx"}):
    try:
        E.obs_url(bad)
        rejected = False
    except E.ObjectFailed:
        rejected = True
    check("拒收可疑附件地址 %s %s" % (bad["endpoint"][8:48], bad["objectKey"]), rejected)

# ── 三 ──────────────────────────────────────────────────────────────
section("三、单个对象：下载后先校验，不合格不进暂存区")
reset()
staging = TMP / "staging"
staging.mkdir()
page = FakePage(rows=4)
path, rows = E.export_object(page, spec_of("项目开票"), staging, download=page.download, probe=page.probe, sleep=no_sleep)
check("成功：暂存区出现与红圈同名的文件", path.name.startswith("项目开票_导出文件_") and path.exists())
check("成功：行数与服务端一致", rows == 4)
check("暂存区没有 .part 残件", not list(staging.glob("*.part")))
check("每次调用都带白名单，附件接口不带回临时凭据",
      all(pick in (None, E.STATE_FIELDS, E.ATTACHMENT_FIELDS) for _, _, pick in page.calls)
      and not ({"accessKeyId", "securityToken", "accessKeySecret"} & set(E.ATTACHMENT_FIELDS)))


def expect_rejected(fake, download, why):
    for leftover in staging.iterdir():
        leftover.unlink()
    try:
        E.export_object(fake, spec_of("项目开票"), staging, download=download, probe=fake.probe, sleep=no_sleep)
        raised = False
    except E.ObjectFailed:
        raised = True
    check(why, raised and not any(staging.iterdir()))


fake = FakePage(state5=["项目开票"])
expect_rejected(fake, fake.download, "服务端任务失败：报对象失败")
fake = FakePage()
expect_rejected(fake, lambda url, dest: (dest.write_bytes(b"PK\x03\x04short"), 9)[1], "字节数与服务端不符：拒收、不留残件")
fake = FakePage(rows=4, claim=5)
expect_rejected(fake, fake.download, "行数与服务端不符：拒收")
fake = FakePage(short_downloads=99)
expect_rejected(fake, fake.download, "一直下不全：三次后报失败、不留残件")
check("一直下不全：恰好重下三次", fake.downloads == E.DOWNLOAD_ATTEMPTS)

for leftover in staging.iterdir():
    leftover.unlink()
fake = FakePage(rows=4, probe_lag=2)
_, rows = E.export_object(fake, spec_of("项目开票"), staging, download=fake.download, probe=fake.probe, sleep=no_sleep)
check("OBS 上文件还没写完：先等字节数对上再下载（09-11 主合同的残件）", rows == 4 and fake.probes == 3 and fake.downloads == 1)
fake = FakePage(rows=4, short_downloads=1)
_, rows = E.export_object(fake, spec_of("项目开票"), staging, download=fake.download, probe=fake.probe, sleep=no_sleep)
check("下到残件会重下，第二次对上就成功", rows == 4 and fake.downloads == 2)

# ── 四 ──────────────────────────────────────────────────────────────
section("四、整轮：一条命令做完，文件从不经过 Downloads")
reset()
page, alerts = FakePage(), []
rc = E.run(page=page, alert=alerts.append, download=page.download, probe=page.probe, sleep=no_sleep)
archived = {p.parent.name for p in month_dir().rglob("*.xlsx")}
check("全部成功：退出码 0，不告警", rc == 0 and alerts == [])
check("七个对象各自进了共享盘目录", archived == {s.label for s in E.OBJECTS})
check("暂存区清空", not any((TMP / "staging").iterdir()))
check("Downloads 从未被写入", not any((TMP / "Downloads").iterdir()))
check("付款审批、收款登记按全历史口径命名",
      all(any("全历史导出" in p.name for p in (month_dir() / label).iterdir())
          for label in ("付款审批（日常费用）", "收款登记")))

reset()
(TMP / "Downloads" / "收款登记_导出文件_5.xlsx").write_bytes(sample(spec_of("收款登记")))
page, alerts = FakePage(), []
rc = E.run(page=page, alert=alerts.append, download=page.download, probe=page.probe, sleep=no_sleep)
check("Downloads 里人工导出的遗留件也被收进共享盘", rc == 0 and not any((TMP / "Downloads").iterdir()))

reset()
page, alerts = FakePage(login_after=3), []
rc = E.run(page=page, alert=alerts.append, download=page.download, probe=page.probe, sleep=no_sleep)
check("中途登录失效：退出码 3，告警写明要重新登录", rc == 3 and alerts == ["HECOM_LOGIN_REQUIRED"])
check("中途登录失效：已导出的 3 份照样存进共享盘", len(list(month_dir().rglob("*.xlsx"))) == 3)

reset()
page, alerts = FakePage(no_tab=True), []
rc = E.run(page=page, alert=alerts.append, download=page.download, probe=page.probe, sleep=no_sleep)
check("打不开红圈页面：HECOM_NO_TAB，退出码 3", rc == 3 and alerts == ["HECOM_NO_TAB"])

reset()
page, alerts = FakePage(fail=["付款审批（日常费用）"]), []
rc = E.run(page=page, alert=alerts.append, download=page.download, probe=page.probe, sleep=no_sleep)
check("部分失败：退出码 2，标记写明哪个对象",
      rc == 2 and alerts == ["EXPORT_PARTIAL ok=6 failed=付款审批（日常费用）"])

reset()
_, root = H.resolve_paths()
lock = H.lock_path_for(root)
H.acquire_lock(lock)
page, alerts = FakePage(), []
rc = E.run(page=page, alert=alerts.append, download=page.download, probe=page.probe, sleep=no_sleep)
H.release_lock(lock)
check("上一轮还在跑：让路、退出码 0、不告警、不导出", rc == 0 and alerts == [] and page.calls == [])

reset()
called, original = [], E.alert_owner
E.alert_owner = called.append
rc = E.run(page=FakePage(no_tab=True), download=lambda url, dest: 0, probe=lambda url: 0, sleep=no_sleep)
E.alert_owner = original
check("设了 HONGQUAN_BASE 时默认告警是空操作，测试发不出钉钉", rc == 3 and called == [])

# ── 五 ──────────────────────────────────────────────────────────────
section("五、登录信息：页面只借一次，请求不再碰标签")
TOKEN = "SECRET-TOKEN-0911"


def auth_json(token=TOKEN, base="https://cloud1.hecom.cn/universe/"):
    return json.dumps({"ready": "complete", "base": base, "accessToken": token,
                       "entCode": "KM_888", "uid": "1", "empCode": "2"})


class Reader:
    def __init__(self, *answers):
        self.answers, self.calls = list(answers), 0

    def __call__(self):
        self.calls += 1
        return self.answers[min(self.calls, len(self.answers)) - 1]


sent = []


def ok_sender(url, headers, body):
    sent.append((url, dict(headers), body))
    if url.endswith("/getExportTaskResultAttachment"):
        return 200, {"result": "0", "data": {"bucket": "b", "objectKey": "k", "endpoint": "e",
                                             "accessKeyId": "AK", "securityToken": "ST", "accessKeySecret": "SK"}}
    return 200, {"result": "0", "data": 12345}


def session_with(reader, sender, opener=lambda: "", closer=lambda tab: None):
    return E.HecomSession(reader=reader, opener=opener, closer=closer, sender=sender, sleep=no_sleep)


reader = Reader(auth_json())
session = session_with(reader, ok_sender)
session.ensure_ready()
for _ in range(5):
    session.call("/app/std/export", {}, "conContract3X", None)
check("取完登录信息后连发 5 个请求，都不再碰标签（两个红圈标签也不会串）", reader.calls == 1)
check("请求头带 app/act/obj（缺 app 头红圈一律 500）",
      sent[-1][1].get("app") == "std" and sent[-1][1].get("act") == "export" and sent[-1][1].get("obj") == "conContract3X")
check("请求只发往 cloud1.hecom.cn", all(url.startswith("https://cloud1.hecom.cn/universe/paas/") for url, _, _ in sent))
got = session.call("/app/std/getExportTaskResultAttachment", {"taskId": 1}, "conContract3X", E.ATTACHMENT_FIELDS)
check("附件接口的临时凭据当场丢弃，只留 bucket/objectKey/endpoint", set(got) == {"bucket", "objectKey", "endpoint"})

try:
    session_with(Reader(auth_json(base="https://evil.example.com/universe/")), ok_sender).ensure_ready()
    refused = False
except E.NoHecomTab:
    refused = True
check("页面给的地址不是 *.hecom.cn：拒绝，不发任何请求", refused)

opened, closed = [], []
session = session_with(Reader(E.NO_TAB, auth_json()), ok_sender,
                       opener=lambda: opened.append("77") or "77", closer=closed.append)
session.ensure_ready()
check("没有红圈标签：自己开一个，取完登录信息就关掉", opened == ["77"] and closed == ["77"])

opened, closed = [], []
session = session_with(Reader(E.NO_TAB, auth_json(token="")), ok_sender,
                       opener=lambda: opened.append("78") or "78", closer=closed.append)
try:
    session.ensure_ready()
    login = False
except E.LoginRequired:
    login = True
check("自己开的标签停在未登录：报需要登录，标签留着给人登录", login and closed == [])

tokens = []


def expired_then_ok(url, headers, body):
    tokens.append(headers["accessToken"])
    if len(tokens) == 1:
        return 200, {"result": "51018", "desc": "登录已失效，请重新登录"}
    return 200, {"result": "0", "data": 7}


session = session_with(Reader(auth_json(token="OLD"), auth_json(token="NEW")), expired_then_ok)
session.ensure_ready()
check("页面换过 token：重取一次登录信息后继续",
      session.call("/app/std/export", {}, "conContract3X", None) == 7 and tokens == ["OLD", "NEW"])

session = session_with(Reader(auth_json()), lambda url, headers, body: (500, {"result": "0", "data": {"status": 500}}))
session.ensure_ready()
try:
    session.call("/app/std/export", {}, "conContract3X", None)
    failed500 = False
except E.ObjectFailed:
    failed500 = True
check("HTTP 500 但 result 为 0：照样算失败（缺头时红圈就是这样回的）", failed500)

import contextlib  # noqa: E402

reset()
buffer, alerts = io.StringIO(), []
session = session_with(Reader(auth_json()), lambda url, headers, body: (200, {"result": "51018", "desc": "登录已失效"}))
with contextlib.redirect_stdout(buffer):
    rc = E.run(page=session, alert=alerts.append, download=lambda url, dest: 0, probe=lambda url: 0, sleep=no_sleep)
check("登录一直失效：HECOM_LOGIN_REQUIRED，退出码 3", rc == 3 and alerts == ["HECOM_LOGIN_REQUIRED"])
check("token 不出现在任何输出与告警里", TOKEN not in buffer.getvalue() and all(TOKEN not in a for a in alerts))
check("暂存区不在 Downloads 里", "Downloads" not in str(E.RUNTIME_DIR / "staging"))

section("六、automation 入口：几秒返回，导出挂后台，下一次先报上一轮结果")
reset()
spawned = []


class FakeChild:
    pid = 4242


def fake_spawn(command, **kwargs):
    spawned.append((command, kwargs))
    return FakeChild()


buffer = io.StringIO()
with contextlib.redirect_stdout(buffer):
    rc = E.launch_background(spawn=fake_spawn)
out = buffer.getvalue().strip().splitlines()
check("首次启动：上一轮记为 NONE，本轮已挂后台", rc == 0 and out[0] == "PREVIOUS NONE"
      and out[-1].startswith("EXPORT_STARTED pid=4242"))
command, kwargs = spawned[0]
check("后台进程脱离 automation 会话、整轮不闲置睡眠",
      kwargs.get("start_new_session") is True and command[:2] == ["/usr/bin/caffeinate", "-i"]
      and command[-1].endswith("hongquan_export.py") and "--background" not in command)
check("后台日志落在运行目录的 logs/ 下", str(TMP / "logs") in out[-1])

page = FakePage(fail=["付款审批（日常费用）"])
with contextlib.redirect_stdout(io.StringIO()):
    E.run(page=page, alert=lambda marker: None, download=page.download, probe=page.probe, sleep=no_sleep)
spawned.clear()
buffer = io.StringIO()
with contextlib.redirect_stdout(buffer):
    E.launch_background(spawn=fake_spawn)
out = buffer.getvalue().strip().splitlines()
check("下一次启动第一行报上一轮真实结果（部分失败写明对象）",
      out[0].startswith("PREVIOUS EXPORT_PARTIAL ok=6 failed=付款审批（日常费用）"))
check("上一轮的 DETAIL 一并带出", any(line.startswith("PREVIOUS_DETAIL 付款审批（日常费用） failed=") for line in out))

_, root = H.resolve_paths()
lock = H.lock_path_for(root)
H.acquire_lock(lock)
spawned.clear()
buffer = io.StringIO()
with contextlib.redirect_stdout(buffer):
    rc = E.launch_background(spawn=fake_spawn)
before = (TMP / "last_run.json").read_text(encoding="utf-8")
with contextlib.redirect_stdout(io.StringIO()):
    E.run(page=FakePage(), alert=lambda marker: None, download=lambda url, dest: 0, probe=lambda url: 0, sleep=no_sleep)
H.release_lock(lock)
check("上一轮还在后台跑：报 EXPORT_LOCKED，不起第二个",
      rc == 0 and buffer.getvalue().strip().splitlines()[-1] == "EXPORT_LOCKED" and spawned == [])
check("让路的那一轮不覆盖上一轮结果", (TMP / "last_run.json").read_text(encoding="utf-8") == before)
check("不认识的参数直接拒绝，不跑导出", E.main(["--now"]) == 64)

shutil.rmtree(TMP, ignore_errors=True)
print("\n" + "=" * 54)
if FAILED:
    print("失败 %d 条：" % len(FAILED))
    for item in FAILED:
        print("  - " + item)
    print("断言数: %d" % (PASSED + len(FAILED)))
    sys.exit(1)
print("全部通过")
print("断言数: %d" % PASSED)
