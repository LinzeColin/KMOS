# -*- coding: utf-8 -*-
"""The unsafe legacy project-margin generator must remain retired."""

from KMFA.tools.project_cost import build_project_margin


def test_legacy_project_margin_generator_fails_closed(capsys):
    assert build_project_margin.main() == 2
    assert "已下线" in capsys.readouterr().err
    assert not hasattr(build_project_margin, "build")
