from tools.harness.__main__ import main


def test_harness_cli_reports_boundary_violation(capsys) -> None:
    exit_code = main(["lint", "tests/fixtures/harness/boundary_leaks/returns_dict.py"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "SA2001" in captured.out
