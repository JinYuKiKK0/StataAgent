from collections.abc import Iterable
from pathlib import Path

from tools.harness.diagnostics import Diagnostic
from tools.harness.rule_boundaries import check_file as check_boundaries
from tools.harness.rule_logging import check_file as check_logging
from tools.harness.rule_taste import check_file as check_taste


def iter_python_files(paths: Iterable[str]) -> list[Path]:
    python_files: list[Path] = []

    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir():
            python_files.extend(sorted(candidate for candidate in path.rglob("*.py") if candidate.is_file()))
        elif path.suffix == ".py" and path.is_file():
            python_files.append(path)

    return python_files


def run_rules(paths: Iterable[str]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    for file_path in iter_python_files(paths):
        diagnostics.extend(check_boundaries(file_path))
        diagnostics.extend(check_logging(file_path))
        diagnostics.extend(check_taste(file_path))

    return diagnostics
