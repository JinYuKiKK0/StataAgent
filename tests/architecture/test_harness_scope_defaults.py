"""harness 默认扫描范围与输出豁免回归测试。"""

from collections.abc import Iterable
from pathlib import Path

import pytest

from tools.harness import __main__ as harness_main
from tools.harness.diagnostics import Diagnostic
from tools.harness.rule_taste import check_file
from tools.harness.rules_manifest import DEFAULT_EXCLUDE_GLOBS
from tools.harness.rules_manifest import DEFAULT_LINT_PATHS
from tools.harness.rules_manifest import iter_python_files


def _write_py(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_harness_cli_defaults_to_src_tests_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`tools.harness lint` 无参时必须默认扫描 src/tests/tools。"""
    captured_paths: list[str] = []

    def fake_run_rules(paths: Iterable[str]) -> list[Diagnostic]:
        captured_paths.extend(paths)
        return []

    monkeypatch.setattr(harness_main, "run_rules", fake_run_rules)

    exit_code = harness_main.main(["lint"])

    assert exit_code == 0
    assert captured_paths == list(DEFAULT_LINT_PATHS)


def test_harness_default_scope_excludes_fixtures_and_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """默认扫描应包含 src/tests/tools 并排除 tests/fixtures/harness 与 __pycache__。"""
    _write_py(tmp_path / "src" / "included.py", "value = 1")
    _write_py(tmp_path / "tests" / "included.py", "value = 2")
    _write_py(tmp_path / "tools" / "included.py", "value = 3")
    _write_py(tmp_path / "tests" / "fixtures" / "harness" / "ignored.py", "value = 4")
    _write_py(tmp_path / "src" / "pkg" / "__pycache__" / "ignored.py", "value = 5")

    monkeypatch.chdir(tmp_path)
    files = iter_python_files(DEFAULT_LINT_PATHS, DEFAULT_EXCLUDE_GLOBS)
    relative_paths = {path.as_posix() for path in files}

    assert "src/included.py" in relative_paths
    assert "tests/included.py" in relative_paths
    assert "tools/included.py" in relative_paths
    assert "tests/fixtures/harness/ignored.py" not in relative_paths
    assert "src/pkg/__pycache__/ignored.py" not in relative_paths


def test_taste_output_exemptions_keep_tools_entrypoints_usable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """开发工具入口允许文本输出，普通 tools 模块仍禁止 print。"""
    run_entry = tmp_path / "tools" / "run_quality_gates.py"
    cli_entry = tmp_path / "tools" / "harness" / "__main__.py"
    regular_tool = tmp_path / "tools" / "module.py"

    _write_py(run_entry, "print('ok')")
    _write_py(cli_entry, "print('ok')")
    _write_py(regular_tool, "print('not allowed')")

    monkeypatch.chdir(tmp_path)

    run_diagnostics = check_file(run_entry)
    cli_diagnostics = check_file(cli_entry)
    regular_diagnostics = check_file(regular_tool)

    assert all(diagnostic.code != "SA3001" for diagnostic in run_diagnostics)
    assert all(diagnostic.code != "SA3001" for diagnostic in cli_diagnostics)
    assert any(diagnostic.code == "SA3001" for diagnostic in regular_diagnostics)
