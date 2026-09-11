"""不依赖任何业务数据的守卫测试（可以进公开仓）。

带真实截图数据的回归测试在私有运行位的 test_daily_funds_local.py，不进 Git。
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestNoUnboundNames(unittest.TestCase):
    """全包扫一遍「用了却从没绑定过的名字」。

    2026-09-10 的事故就是这一类：``smb_source.fetch`` 里写了
    ``hashlib.sha1(...)``，但模块顶上没有 ``import hashlib``。
    Python 的名字是**调用时**才解析的，所以：
      · import 这个模块不报错；
      · py_compile / compileall 全绿；
      · 58 个单测全过——因为没有一个测试真的调到 fetch()。
    结果它只在定时任务真跑到那一行时才炸，静默一天。

    检查刻意做成**过近似**：把文件里任何位置绑定过的名字全部当成已知
    （不分作用域），所以永远不会误报，代价是漏掉「只在别的函数里绑定过」
    的情形。宁可漏，不可假红——一条会误报的守卫，两周后就没人看了。
    """

    def _unbound(self, path):
        import ast
        import builtins

        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=path)
        bound = set(dir(builtins)) | {"__file__", "__name__", "__doc__"}

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for a in node.names:
                    bound.add((a.asname or a.name).split(".")[0])
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                bound.add(node.name)
            elif isinstance(node, ast.arg):
                bound.add(node.arg)
            elif isinstance(node, (ast.Global, ast.Nonlocal)):
                bound.update(node.names)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                bound.add(node.id)
            elif isinstance(node, ast.ExceptHandler) and node.name:
                bound.add(node.name)

        return sorted({
            (n.id, n.lineno)
            for n in ast.walk(tree)
            if isinstance(n, ast.Name)
            and isinstance(n.ctx, ast.Load)
            and n.id not in bound
        })

    def _package_files(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        out = []
        for sub in ("daily_funds_local", "scripts"):
            d = os.path.join(root, sub)
            if not os.path.isdir(d):
                continue
            for name in sorted(os.listdir(d)):
                if name.endswith(".py"):
                    out.append(os.path.join(d, name))
        return out

    def test_whole_package_has_no_unbound_names(self):
        files = self._package_files()
        self.assertGreater(len(files), 4, "没扫到文件说明路径错了，这测试就是假绿")
        bad = {}
        for path in files:
            found = self._unbound(path)
            if found:
                bad[os.path.basename(path)] = found
        self.assertEqual(bad, {}, "存在从未绑定的名字：%r" % (bad,))

    def test_guard_actually_catches_a_missing_import(self):
        """负控：把事故原样造一遍，守卫必须红。"""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                         encoding="utf-8") as fh:
            fh.write("def f(x):\n    return hashlib.sha1(x).hexdigest()\n")
            probe = fh.name
        try:
            self.assertEqual(self._unbound(probe), [("hashlib", 2)])
        finally:
            os.unlink(probe)


class TestSmbSourceFetch(unittest.TestCase):
    """真的调一次 fetch()——事故那条路，之前一个测试都没有。

    用临时目录当 SMB 根，走的是和线上完全一样的代码：
    双路查找 → rsync --inplace → 读回校验。
    """

    def _archive_with(self, root, filename, payload=b"\x89PNG\r\n\x1a\nnot-zero"):
        import pathlib

        from daily_funds_local import smb_source

        photo = os.path.join(root, "付款请示群", "photo")
        os.makedirs(photo, exist_ok=True)
        with open(os.path.join(photo, filename), "wb") as fh:
            fh.write(payload)
        arc = smb_source.SmbArchive.__new__(smb_source.SmbArchive)
        arc.photo_dir = pathlib.Path(photo)
        return arc

    def _cand(self, original, renamed=None):
        from daily_funds_local import smb_source

        return smb_source.Candidate(
            message_time="2026-09-10 14:02:00", layout="C",
            width=1218, height=1396, original_name=original,
            renamed=renamed, size_bytes=None,
        )

    def test_fetch_copies_and_names_by_full_hash(self):
        import hashlib as _h

        with tempfile.TemporaryDirectory() as root, \
             tempfile.TemporaryDirectory() as dest:
            name = "iwEfakeMediaNameForFetchTest0001.png"
            arc = self._archive_with(root, name)
            got = arc.fetch(self._cand(name), dest)

            self.assertIsNotNone(got, "fetch 返回 None——盘上明明有这个文件")
            tag = _h.sha1(name.encode("utf-8")).hexdigest()[:10]
            self.assertEqual(os.path.basename(got),
                             "2026-09-10_C_%s.png" % tag)
            self.assertTrue(os.path.getsize(got) > 0)

    def test_two_media_ids_sharing_a_prefix_do_not_collide(self):
        """新式 mediaId 前 16 位全一样，按前缀命名会让同一天两张图互相覆盖。"""
        with tempfile.TemporaryDirectory() as root, \
             tempfile.TemporaryDirectory() as dest:
            a = "iwEcAqNwbmcDAQTRAAAA.png"
            b = "iwEcAqNwbmcDAQTRBBBB.png"
            arc = self._archive_with(root, a, b"\x89PNG-a")
            self._archive_with(root, b, b"\x89PNG-b")
            pa = arc.fetch(self._cand(a), dest)
            pb = arc.fetch(self._cand(b), dest)
            self.assertNotEqual(pa, pb)

    def test_missing_file_returns_none_instead_of_raising(self):
        with tempfile.TemporaryDirectory() as root, \
             tempfile.TemporaryDirectory() as dest:
            arc = self._archive_with(root, "存在的.png")
            self.assertIsNone(arc.fetch(self._cand("不在盘上的.png"), dest))


if __name__ == "__main__":
    unittest.main(verbosity=2)
