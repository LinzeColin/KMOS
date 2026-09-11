"""从 SMB 归档里找出「资金账户明细表」余额表的原始图片。

三条实测约束，改动前先读：

1. **只用 rsync 读 SMB。** SMB 上 ``cp`` 会静默写出全 0——字节数正确、无报错、
   内容空白。写后必须校验非全 0。
2. **manifest 里的路径在盘上可能不存在。** 上游 KMMedia-Archive 做过幂等改名，
   要经 ``原名新名映射.csv`` 转换；而映射表比 manifest 滞后约半个月，
   所以新名、原名两条路都得走。
3. **选择器是尺寸，不是文本也不是业务名。** 带 ``M.D资金明细`` 文字的那张是
   付款流水表；业务名同一张图会被打成 6 种不同名字。
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from .mediaid import dims_of

SMB_ROOT_DEFAULT = "/Volumes/share/03_资料库/MetaData/IDS_MetaData/KMVideo"
GROUP = "付款请示群"

# 余额表的三代版式，精确匹配尺寸（不要改成范围启发式，会混进别的表）
LAYOUTS = {
    (719, 1391): "A",    # 2026-01-09 → 04-24  列名「收款小计/付款小计/本日余额」，含库存现金
    (1218, 1256): "B",   # 2026-04-27 → 06-29  列名「今日收款/今日支出/今日余额」
    (1218, 1396): "C",   # 2026-06-30 → 至今   同 B，多「湖北曦悦」
}


class SmbUnavailable(RuntimeError):
    pass


@dataclass
class Candidate:
    message_time: str      # 消息时间，只用来缩小搜索窗口；权威日期以图内为准
    layout: str            # A / B / C
    width: int
    height: int
    original_name: str
    renamed: Optional[str]
    size_bytes: Optional[int]

    @property
    def message_date(self) -> str:
        return self.message_time[:10]


class SmbArchive:
    def __init__(self, root: Optional[str] = None) -> None:
        self.root = Path(root or os.environ.get("KM_SMB_ROOT") or SMB_ROOT_DEFAULT)
        if not self.root.is_dir():
            raise SmbUnavailable("SMB 根不可用: %s" % self.root)
        self.photo_dir = self.root / GROUP / "photo"
        self._rename: Optional[Dict[str, str]] = None

    # ---------- 账本 ----------

    def _local_copy(self, remote: Path, suffix: str) -> Path:
        """rsync 到本地临时文件并校验非全 0。"""
        tmp = Path(tempfile.mkdtemp(prefix="kmfa-smb-")) / ("f" + suffix)
        rc = subprocess.run(
            ["rsync", "-a", "--inplace", str(remote), str(tmp)],
            capture_output=True, text=True,
        )
        if rc.returncode != 0 or not tmp.exists():
            raise SmbUnavailable("rsync 失败 %s: %s" % (remote.name, rc.stderr.strip()[:160]))
        data = tmp.read_bytes()
        if not data or not data.strip(b"\x00"):
            raise SmbUnavailable("SMB 读回全 0（cp 静默失败的典型症状）: %s" % remote.name)
        return tmp

    @property
    def rename_map(self) -> Dict[str, str]:
        """原文件名 -> 新文件名。映射表滞后是常态，查不到就用原名。"""
        if self._rename is None:
            self._rename = {}
            src = self.root / "原名新名映射.csv"
            if src.exists():
                local = self._local_copy(src, ".csv")
                with local.open(encoding="utf-8-sig", newline="") as fh:
                    for row in csv.DictReader(fh):
                        if row.get("项目") == GROUP and row.get("原文件名"):
                            self._rename[row["原文件名"]] = row.get("新文件名") or ""
        return self._rename

    def candidates(self) -> Iterator[Candidate]:
        """遍历 manifest，吐出所有命中三代尺寸的余额表候选。"""
        manifest = self.root / GROUP / ".manifest.jsonl"
        local = self._local_copy(manifest, ".jsonl")
        rename = self.rename_map
        with local.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if rec.get("record_type") != "media":
                    continue
                dims = dims_of(rec)
                if dims not in LAYOUTS:
                    continue
                original = (rec.get("smb_relative_path") or "").split("/")[-1]
                if not original:
                    continue
                yield Candidate(
                    message_time=rec.get("message_time") or "",
                    layout=LAYOUTS[dims],
                    width=dims[0],
                    height=dims[1],
                    original_name=original,
                    renamed=rename.get(original) or None,
                    size_bytes=rec.get("size_bytes"),
                )

    # ---------- 取图 ----------

    def fetch(self, cand: Candidate, dest_dir: str) -> Optional[str]:
        """双路查找并取回图片。两条都失败返回 None（记 file_missing，不中断）。"""
        names: List[str] = []
        if cand.renamed:
            names.append(cand.renamed)
        names.append(cand.original_name)

        for name in names:
            remote = self.photo_dir / name
            if not remote.exists():
                continue
            # 新式 mediaId 的前 16 位全是 "iwEcAqNwbmcDAQTR"，拿它当文件名
            # 会让同一天的两张图互相覆盖。用全名哈希。
            tag = hashlib.sha1(cand.original_name.encode("utf-8")).hexdigest()[:10]
            dest = Path(dest_dir) / ("%s_%s_%s.png" % (
                cand.message_date, cand.layout, tag))
            dest.parent.mkdir(parents=True, exist_ok=True)
            rc = subprocess.run(
                ["rsync", "-a", "--inplace", str(remote), str(dest)],
                capture_output=True, text=True,
            )
            if rc.returncode == 0 and dest.exists():
                data = dest.read_bytes()
                if data and data.strip(b"\x00"):
                    return str(dest)
        return None

    def fetch_media(self, media_id: str, dest_dir: str) -> Optional[str]:
        """按钉钉 mediaId（不带 @）取图。归档文件名是 ``<mediaId>_<高>_<宽>.png``，
        被幂等改名过的经映射表找回。mediaId 自身含 ``_`` 和 ``-``，只能整段前缀匹配，
        不能按 ``_`` 切。还没归档到就返回 None——下一轮再来，不算失败。"""
        prefix = media_id + "_"
        names: List[str] = []
        try:
            names = [n for n in os.listdir(self.photo_dir)
                     if n.startswith(prefix) and not n.startswith("._")]
        except OSError:
            names = []
        if not names:
            names = [new for orig, new in self.rename_map.items()
                     if orig.startswith(prefix) and new]
        for name in sorted(names, key=len):
            remote = self.photo_dir / name
            if not remote.exists():
                continue
            tag = hashlib.sha1(media_id.encode("utf-8")).hexdigest()[:10]
            dest = Path(dest_dir) / ("bills_%s.png" % tag)
            dest.parent.mkdir(parents=True, exist_ok=True)
            rc = subprocess.run(["rsync", "-a", "--inplace", str(remote), str(dest)],
                                capture_output=True, text=True)
            if rc.returncode == 0 and dest.exists():
                data = dest.read_bytes()
                if data and data.strip(b"\x00"):
                    return str(dest)
        return None
