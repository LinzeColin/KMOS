# -*- coding: utf-8 -*-
"""读私有库里的一个文件，就只该取那一个文件。

2026-07-28 线上：self-audit 连续失败在
`subprocess.TimeoutExpired: Command '['git', 'checkout', '--quiet']' timed out after 120 seconds`。

上一版把超时从 120s 提到 300s——那只是让它「慢着失败」。真因是口径：为了读一份
`Private-KMDatabase/manifest.jsonl`，`read_text` 去 sparse-checkout 它的**父目录**
`Private-KMDatabase/`，而那里面装着 KMFA_MetaData、objects、app-state-backup……
几百 MB 全落盘。

修法是别去检出根本不需要的东西：
  · 读 → blobless clone + `git show HEAD:<path>`，按需只拉一个 blob，不建工作树；
  · 写 → 要工作树才能 add/commit/push，但用 `--no-cone` 精确到文件
    （cone 模式只认目录，一给就是整个目录）。

这组测试盯的就是这个口径别再飘回父目录。
"""
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import private_db_access as PDB  # noqa: E402

MANIFEST = "Private-KMDatabase/manifest.jsonl"


class _Recorder:
    """记下每次 git 调用，让测试能断言「检出范围」而不是断言实现细节。"""

    def __init__(self, show_output=""):
        self.calls: list[list[str]] = []
        self.show_output = show_output

    def __call__(self, args, cwd=None, timeout=120):
        self.calls.append(list(args))
        return self.show_output if args and args[0] == "show" else ""

    def joined(self):
        return [" ".join(c) for c in self.calls]


@pytest.fixture
def deploy_key_only(monkeypatch):
    """强制走部署密钥那条路——token 在时是 REST，不碰 git。"""
    monkeypatch.setattr(PDB, "token", lambda: None)
    monkeypatch.setattr(PDB, "has_deploy_key", lambda: True)


def test_reading_a_file_never_checks_out_its_parent_directory(deploy_key_only, monkeypatch):
    """这是那 120s 超时的真因——父目录是几百 MB。"""
    recorder = _Recorder(show_output='{"sha256":"abc"}\n')
    monkeypatch.setattr(PDB, "_git", recorder)
    assert PDB.read_text(MANIFEST).strip() == '{"sha256":"abc"}'
    joined = recorder.joined()
    assert not any("sparse-checkout" in c for c in joined), \
        f"读单个文件不该做 sparse-checkout：{joined}"
    assert not any(c.startswith("checkout") for c in joined), \
        f"读单个文件不该建工作树：{joined}"


def test_reading_uses_show_to_fetch_exactly_one_blob(deploy_key_only, monkeypatch):
    recorder = _Recorder(show_output="内容\n")
    monkeypatch.setattr(PDB, "_git", recorder)
    PDB.read_text(MANIFEST)
    assert any(c == f"show HEAD:{MANIFEST}" for c in recorder.joined())


def test_the_clone_stays_blobless(deploy_key_only, monkeypatch):
    """整仓 clone 会损伤机器——私有库预计 500GB+。"""
    recorder = _Recorder(show_output="x")
    monkeypatch.setattr(PDB, "_git", recorder)
    PDB.read_text(MANIFEST)
    clone = next(c for c in recorder.joined() if c.startswith("clone"))
    assert "--filter=blob:none" in clone and "--no-checkout" in clone


def test_a_missing_file_is_not_reported_as_an_outage(deploy_key_only, monkeypatch):
    """`git show` 对「路径不存在」也返回非零。文件不在是业务事实，
    跟网络/超时够不着是两回事，混了会让缺文件看起来像故障。"""
    def fake(args, cwd=None, timeout=120):
        if args and args[0] == "show":
            raise PDB.Unavailable(
                "git show 失败：fatal: path 'x' does not exist in 'HEAD'")
        return ""
    monkeypatch.setattr(PDB, "_git", fake)
    with pytest.raises(PDB.Unavailable, match="私有库里没有"):
        PDB.read_text(MANIFEST)


def test_a_real_outage_keeps_its_own_message(deploy_key_only, monkeypatch):
    def fake(args, cwd=None, timeout=120):
        if args and args[0] == "show":
            raise PDB.Unavailable("git show 超时（300s）——私有库大，网络或磁盘慢")
        return ""
    monkeypatch.setattr(PDB, "_git", fake)
    with pytest.raises(PDB.Unavailable, match="超时"):
        PDB.read_text(MANIFEST)


def test_writing_narrows_sparse_checkout_to_the_exact_file(monkeypatch):
    """写要工作树，但只要那一个文件——cone 模式只认目录，必须 --no-cone。"""
    recorder = _Recorder()
    monkeypatch.setattr(PDB, "_git", recorder)
    PDB._sparse_clone_file("Private-KMDatabase/KMFA/skill-ledger/2026-07.jsonl", "/tmp/x")
    joined = recorder.joined()
    assert any("sparse-checkout init --no-cone" in c for c in joined), joined
    assert any(c == "sparse-checkout set Private-KMDatabase/KMFA/skill-ledger/2026-07.jsonl"
               for c in joined), joined


def test_the_parent_directory_helper_is_gone():
    """旧的父目录口径必须删掉，留着就是等下一个人踩同一个坑。"""
    assert not hasattr(PDB, "_sparse_clone"), \
        "_sparse_clone（按父目录检出）还在，它正是 120s 超时的来源"
    source = (TOOLS / "private_db_access.py").read_text(encoding="utf-8")
    assert "Path(path).parent" not in source, \
        "还有地方按父目录取范围——读写都该精确到文件"
