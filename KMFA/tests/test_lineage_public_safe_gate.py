# -*- coding: utf-8 -*-
"""血缘图 public-safe 门禁。

KMOS 是公开仓。血缘图每个节点带 `domain` / `batch`，这两个值来自私有库的 raw 账本——
今天是分类名，但账本在 Owner 那边写，哪天 batch 里带上客户名或项目全称，就会顺着
这条管线流进公开仓，且不会有人发现。

所以门禁盯的是**产物的形状**，不是「现在有没有泄露」：键必须在白名单里、值里不许
出现金额形态、抽取来源必须声明。用白名单是因为黑名单挡不住「将来新增的字段」。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import check_lineage_public_safe as G  # noqa: E402

GOOD = '''# 由 KMFA/tools/lineage_graph.py 机械生成，勿手改
schema: "kmfa.lineage.v1"
extractions_source: "existing_lineage"
raw_assets: 53
raw_with_staging_edges: 13
nodes:
  - asset: "raw:cc3963bcdfa0"
    domain: "journal"
    batch: "2026-07-25"
    size_bytes: 1048576
edges:
  - from: "raw:cc3963bcdfa0"
    to: "_staging.expense_lines"
    sheet_hash: "ff224d7bc431"
    rows: 4364
    version: "expense-v1"
'''


def _write(tmp_path, text):
    path = tmp_path / "lineage.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_a_well_formed_graph_passes(tmp_path):
    assert G.check(_write(tmp_path, GOOD)) == []


def test_missing_extraction_source_is_flagged(tmp_path):
    """没有这行，读图的人分不出「刚跟抽取账本对过账」和「只是把旧边带过来」。"""
    problems = G.check(_write(tmp_path, GOOD.replace(
        'extractions_source: "existing_lineage"\n', "")))
    assert any("extractions_source" in p for p in problems)


def test_an_unregistered_key_is_rejected(tmp_path):
    """白名单的意义就在这里：将来有人加字段，默认不放行。"""
    problems = G.check(_write(tmp_path, GOOD + '客户全称: "武汉某某公司"\n'))
    assert any("未登记的键" in p for p in problems)


def test_money_shaped_values_are_rejected(tmp_path):
    """真金额一旦漏进来就是往公开仓写业务数据。"""
    for leaked in ('金额: "40,960,322.77"', 'x: "1234.56"'):
        problems = G.check(_write(tmp_path, GOOD + leaked + "\n"))
        assert any("金额形态" in p for p in problems), leaked


def test_row_counts_and_byte_sizes_are_not_mistaken_for_money(tmp_path):
    """行数和字节数是裸整数，误判它们会让门禁天天假红，然后被人关掉。"""
    problems = G.check(_write(tmp_path, GOOD))
    assert not any("金额形态" in p for p in problems)


def test_exit_code_is_nonzero_when_something_is_wrong(tmp_path, monkeypatch, capsys):
    bad = _write(tmp_path, GOOD + '客户全称: "武汉某某公司"\n')
    monkeypatch.setattr(sys, "argv", ["check", str(bad)])
    assert G.main() == 1
    assert "::error::" in capsys.readouterr().out
