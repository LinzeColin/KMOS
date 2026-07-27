# -*- coding: utf-8 -*-
"""项目成本产线：两个原本写死为 MISSING 的证据项，实现后的行为。

背景：`current_regression._derive_private_requirements` 里，
`KINGDEE_READER_PROFILE` 与 `ACCOUNTING_BASIS_POLICY` 的 observed_status 被**写死成 MISSING**——
本该去查密封包的档案/政策清单，那段查询没有实现。写死的后果是双向的：
现场准备得再齐它也报缺失，产线永远过不去；而且没人看得出这是桩还是判定。

实现时最该防的，是把"实现"做成"放行"。所以这里逐条钉死五种情形，
其中四种必须**不放行**——只有完整且 ACTIVE 才 PRESENT。
"""
import sys
import textwrap
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1] / "skills" / "项目成本表"
sys.path.insert(0, str(SKILL / "src"))
pytest.importorskip("yaml")
from project_cost_table.current_regression import _sealed_artifact_status  # noqa: E402

PROFILE = "profiles/kingdee_reader_profile.private.yml"
POLICY = "policies/accounting_basis_policy.private.yml"


def _write(root: Path, rel: str, body: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(body), encoding="utf-8")


def test_absent_artifact_stays_missing(tmp_path):
    """实现之后也不能凭空转绿：文件不在，仍然 MISSING（与写死时的行为一致）。"""
    assert _sealed_artifact_status(tmp_path, PROFILE,
                                   forbid_placeholder_in="column_bindings") == "MISSING"
    assert _sealed_artifact_status(tmp_path, POLICY) == "MISSING"


def test_non_active_status_is_conflict(tmp_path):
    _write(tmp_path, PROFILE, """\
        status: DRAFT
        column_bindings: {debit: 借方}
        """)
    assert _sealed_artifact_status(tmp_path, PROFILE,
                                   forbid_placeholder_in="column_bindings") == "CONFLICT"


def test_leftover_placeholder_is_conflict(tmp_path):
    """模板占位没换掉就宣称 ACTIVE，是最容易蒙混过去的一种。"""
    _write(tmp_path, PROFILE, """\
        status: ACTIVE
        column_bindings: {debit: REPLACE_DEBIT_HEADER}
        """)
    assert _sealed_artifact_status(tmp_path, PROFILE,
                                   forbid_placeholder_in="column_bindings") == "CONFLICT"


def test_empty_bindings_is_conflict(tmp_path):
    _write(tmp_path, PROFILE, """\
        status: ACTIVE
        column_bindings: {}
        """)
    assert _sealed_artifact_status(tmp_path, PROFILE,
                                   forbid_placeholder_in="column_bindings") == "CONFLICT"


def test_complete_and_active_is_present(tmp_path):
    _write(tmp_path, PROFILE, """\
        status: ACTIVE
        column_bindings:
          account_code: 科目
          contract_source_key: 销售合同号
          debit: 借方
          credit: 贷方
        """)
    assert _sealed_artifact_status(tmp_path, PROFILE,
                                   forbid_placeholder_in="column_bindings") == "PRESENT"
    _write(tmp_path, POLICY, "status: ACTIVE\n")
    assert _sealed_artifact_status(tmp_path, POLICY) == "PRESENT"


def test_the_two_requirements_are_no_longer_hardcoded():
    """防回退：这两项一旦被改回写死，产线就又永远过不去且看不出来。"""
    source = (SKILL / "src" / "project_cost_table" / "current_regression.py").read_text(
        encoding="utf-8")
    for requirement in ("KINGDEE_READER_PROFILE", "ACCOUNTING_BASIS_POLICY"):
        block = source.split(f'"requirement_id": "{requirement}"', 1)[1][:220]
        assert '"observed_status": "MISSING"' not in block, (
            f"{requirement} 的 observed_status 又被写死成 MISSING —— "
            "那是 fail-closed 的桩，不是判定；请实现查询而不是写死。"
        )
