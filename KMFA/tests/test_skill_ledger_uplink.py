# -*- coding: utf-8 -*-
"""技能台账回传的回归测试。

这条链路的价值全在"失败时不要拖垮技能"和"确实把行追加上去了"这两点上，
所以测的就是这两点，外加一条：没配 token 时必须安静跳过而不是报错刷屏。
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import skill_ledger_uplink as U  # noqa: E402

LINE = json.dumps({"ts": "2026-07-27T12:00:00+08:00", "skill": "upstream-archive",
                   "rc": 0, "log": "/var/log/kmfa/upstream-archive/x.log",
                   "delivery_enabled": "0"}, ensure_ascii=False)


def test_month_path_uses_beijing_time():
    """跨日/跨月分片按北京时间，否则 UTC 早八小时会把月末归错月。"""
    utc_new_month_eve = datetime(2026, 7, 31, 20, 0, tzinfo=timezone.utc)  # 北京已是 8/1
    assert U.month_path(utc_new_month_eve).endswith("2026-08.jsonl")


def test_append_creates_file_when_absent(monkeypatch):
    calls = []

    def fake_api(method, path, token, body=None):
        calls.append((method, path, body))
        if method == "GET":
            return None                      # 当月还没有台账文件
        return {}

    monkeypatch.setattr(U, "_api", fake_api)
    U.append_line(LINE, "tok", repo="X/Y", path="a/b.jsonl")
    put = [c for c in calls if c[0] == "PUT"][0]
    assert "sha" not in put[2], "文件不存在时不该带 sha"
    import base64
    assert base64.b64decode(put[2]["content"]).decode() == LINE + "\n"


def test_append_preserves_existing_and_adds_trailing_newline(monkeypatch):
    import base64
    old = '{"ts":"1","skill":"a","rc":0}'      # 故意不带结尾换行
    stored = {}

    def fake_api(method, path, token, body=None):
        if method == "GET":
            return {"content": base64.b64encode(old.encode()).decode(), "sha": "s1"}
        stored.update(body)
        return {}

    monkeypatch.setattr(U, "_api", fake_api)
    U.append_line(LINE, "tok", repo="X/Y", path="a/b.jsonl")
    got = base64.b64decode(stored["content"]).decode()
    assert got == old + "\n" + LINE + "\n", "既有内容必须原样保留且补上换行"
    assert stored["sha"] == "s1"


def test_missing_token_exits_quietly(monkeypatch, capsys):
    monkeypatch.setattr(U, "_token", lambda: None)
    monkeypatch.setattr(sys, "argv", ["x", "--line", LINE])
    assert U.main() == 0
    assert "跳过回传" in capsys.readouterr().out


def test_upload_failure_never_fails_the_skill(monkeypatch, capsys):
    monkeypatch.setattr(U, "_token", lambda: "tok")

    def boom(*a, **k):
        raise RuntimeError("GitHub 挂了")

    monkeypatch.setattr(U, "append_line", boom)
    monkeypatch.setattr(sys, "argv", ["x", "--line", LINE])
    assert U.main() == 0, "回传失败必须返回 0——否则会把技能本身判成失败"
    assert "回传失败" in capsys.readouterr().err


def test_malformed_line_is_skipped_not_uploaded(monkeypatch):
    monkeypatch.setattr(U, "_token", lambda: "tok")
    monkeypatch.setattr(U, "append_line", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("不该上传非法行")))
    monkeypatch.setattr(sys, "argv", ["x", "--line", "这不是 JSON"])
    assert U.main() == 0


def test_target_is_the_single_private_repo():
    """Owner 铁律：只进 Private-Database，永不新建 repo。"""
    assert U.REPO == "LinzeColin/Private-Database"
    assert U.AREA.startswith("Private-KMDatabase/")
