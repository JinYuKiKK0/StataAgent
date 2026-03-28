"""治理入口测试：harness CLI 能把规则违规稳定报告给调用方。"""

from pytest import CaptureFixture

from tools.harness.__main__ import main


def test_harness_cli_reports_boundary_violation(capsys: CaptureFixture[str]) -> None:
    """验证 CLI 模式下的 lint 会输出边界违规编号，供 CI 和本地开发复用。"""
    exit_code = main(["lint", "tests/fixtures/harness/boundary_leaks/returns_dict.py"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "SA2001" in captured.out
