# -*- coding: utf-8 -*-
"""血缘图必须在没有 DuckDB 的机器上也能重建。

为什么（2026-07-28 查 self-audit 连红 40 次查出来的）：

`load_extractions()` 原来只认 `KMFA/.codex_private_runtime/duckdb/kmfa_staging.duckdb`。
那是 gitignored 的私有运行时——本机没有、CI 没有、连容器里都被 self-audit 自己的
tar `--exclude=./KMFA/.codex_private_runtime` 排掉。也就是说 `build`
**在任何一台能跑 self-audit 的机器上都跑不起来**。

后果不是报错，是更糟的一种：图冻死在旧版本，Owner 每往私有库放一批新数据，
`stale` 就报一次 STALE，rc=1。连红 40 次之后，这个检查在驾驶舱上等于一盏坏灯——
它永远红，所以它红的时候没人看。

降级路径的关键约束是**不能把已有的边抹掉**：返回空列表会让重建后的图变成
「零抽取」，`lineage_complete_v1` 翻假，而这在产物里看起来像是数据出了问题，
比直接报错难查得多。
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import lineage_graph as L  # noqa: E402


def test_duckdb_is_not_reachable_where_self_audit_runs():
    """这条钉住问题本身：DuckDB 在私有运行时目录下，而那目录被 self-audit 排除。

    哪天它真的被纳入交付了，这条会失败——那时降级路径就该重新审一遍。
    """
    assert ".codex_private_runtime" in str(L.DB_PATH)
    runner = Path(__file__).resolve().parents[1] / "deploy" / "skills-runtime" / "run_skill.sh"
    assert "--exclude=./KMFA/.codex_private_runtime" in runner.read_text(encoding="utf-8")


def test_edges_survive_when_duckdb_is_gone():
    """DuckDB 够不着时，已记录的边必须原样回来——一条都不能少。"""
    recovered = L._edges_from_existing_lineage()
    assert recovered, "现有 lineage.yaml 里读不出边，降级路径等于没有"
    text = L.LINEAGE_PATH.read_text(encoding="utf-8")
    assert len(recovered) == text.count("  - from:"), "回读的边数跟 yaml 里的对不上"
    for edge in recovered:
        assert edge["file_hash_prefix"] and edge["table"]
        assert "sheet_hash" in edge and "rows" in edge and "version" in edge


def test_load_extractions_reports_which_ledger_it_used():
    """降级不能悄悄发生：来源必须跟着数一起出来。"""
    rows, source = L.load_extractions()
    assert source in ("duckdb", "existing_lineage")
    assert rows, "两条路径都空，等于把血缘抹掉了"


def test_refuses_to_rebuild_as_zero_extraction(tmp_path, monkeypatch):
    """DuckDB 没有 + yaml 也读不出边 → 必须报错，绝不能产出一张空图。

    产出空图的表现是 `lineage_complete_v1` 突然翻假、13 个已覆盖资产变 0——
    看起来像数据出了问题，实际是工具把账抹了。这种失败必须响。
    """
    empty = tmp_path / "lineage.yaml"
    empty.write_text("schema: \"kmfa.lineage.v1\"\nnodes: []\n", encoding="utf-8")
    monkeypatch.setattr(L, "LINEAGE_PATH", empty)
    monkeypatch.setattr(L, "DB_PATH", tmp_path / "nope.duckdb")
    with pytest.raises(L.ExtractionsUnavailable):
        L.load_extractions()


def test_graph_records_the_extraction_source():
    """产物里要能看出这次重建有没有跟 DuckDB 对过账。"""
    text = L.LINEAGE_PATH.read_text(encoding="utf-8")
    # 现有产物是旧版工具生成的，没有这个字段；新版必须写出来。
    assert "extractions_source" in Path(
        L.__file__).read_text(encoding="utf-8"), "build_graph 没有把来源写进产物"


def test_prefix_collision_is_detected_not_silently_mismatched(monkeypatch):
    """按 12 位前缀匹配的代价：撞车会把 A 的边挂到 B 上。必须报错，不能静默。"""
    same = "abcdef012345" + "0" * 52
    monkeypatch.setattr(L, "load_raw", lambda: [
        {"sha256": same, "domain": "d", "batch": "b", "size_bytes": 1},
        {"sha256": same, "domain": "d2", "batch": "b2", "size_bytes": 2},
    ])
    monkeypatch.setattr(L, "load_extractions", lambda: ([], "existing_lineage"))
    with pytest.raises(RuntimeError, match="撞车"):
        L.build_graph()
