"""harness taste 规则回归测试。"""

from pathlib import Path
from collections.abc import Sequence

from tools.harness.diagnostics import Diagnostic
from tools.harness.rule_taste import MAX_FILE_LINES
from tools.harness.rule_taste import check_file


def _write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines), encoding="utf-8")


def _has_message(diagnostics: Sequence[Diagnostic], message: str) -> bool:
    return any(diagnostic.message == message for diagnostic in diagnostics)


def test_taste_reports_file_above_350_lines(tmp_path: Path) -> None:
    """351 行文件必须触发 SA4002。"""
    file_path = tmp_path / "too_long.py"
    _write_lines(file_path, [f"value_{idx} = {idx}" for idx in range(MAX_FILE_LINES + 1)])

    diagnostics = check_file(file_path)

    assert _has_message(diagnostics, "File exceeds maximum line budget")


def test_taste_allows_file_at_350_lines(tmp_path: Path) -> None:
    """350 行及以下不应触发文件长度限制。"""
    file_path = tmp_path / "within_limit.py"
    _write_lines(file_path, [f"value_{idx} = {idx}" for idx in range(MAX_FILE_LINES)])

    diagnostics = check_file(file_path)

    assert not _has_message(diagnostics, "File exceeds maximum line budget")


def test_taste_no_long_function_diagnostic(tmp_path: Path) -> None:
    """函数超过 40 行不再单独触发 SA4002。"""
    file_path = tmp_path / "long_function.py"
    lines = ["def long_func():"]
    lines.extend(f"    value_{idx} = {idx}" for idx in range(60))
    lines.append("    return value_0")
    _write_lines(file_path, lines)

    diagnostics = check_file(file_path)

    assert not _has_message(diagnostics, "Function exceeds maximum line budget")
