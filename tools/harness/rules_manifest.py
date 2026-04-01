from collections.abc import Iterable
from fnmatch import fnmatch
from pathlib import Path

from tools.harness.diagnostics import Diagnostic
from tools.harness.rule_boundaries import check_file as check_boundaries
from tools.harness.rule_logging import check_file as check_logging
from tools.harness.rule_taste import check_file as check_taste

DEFAULT_LINT_PATHS: tuple[str, ...] = ("src", "tests", "tools")
DEFAULT_EXCLUDE_GLOBS: tuple[str, ...] = (
    "**/__pycache__/**",
    ".venv/**",
    "tests/fixtures/harness/**",
)


def iter_python_files(
    paths: Iterable[str],
    exclude_globs: Iterable[str] = DEFAULT_EXCLUDE_GLOBS,
) -> list[Path]:
    python_files: set[Path] = set()
    exclusions = tuple(exclude_globs)

    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir():
            for candidate in path.rglob("*.py"):
                if candidate.is_file() and not _is_excluded(candidate, exclusions):
                    python_files.add(candidate)
        elif (
            path.suffix == ".py"
            and path.is_file()
            and not _is_excluded(path, exclusions)
        ):
            python_files.add(path)

    return sorted(python_files)


def _is_excluded(path: Path, exclude_globs: tuple[str, ...]) -> bool:
    candidates = _path_match_candidates(path)
    return any(
        fnmatch(candidate, pattern)
        for candidate in candidates
        for pattern in exclude_globs
    )


def _path_match_candidates(path: Path) -> tuple[str, ...]:
    candidates: list[str] = [path.as_posix()]

    try:
        relative = path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        relative = None

    if relative is not None:
        candidates.append(relative)

    return tuple(dict.fromkeys(candidates))


def run_rules(
    paths: Iterable[str],
    *,
    exclude_globs: Iterable[str] = DEFAULT_EXCLUDE_GLOBS,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    for file_path in iter_python_files(paths, exclude_globs=exclude_globs):
        diagnostics.extend(check_boundaries(file_path))
        diagnostics.extend(check_logging(file_path))
        diagnostics.extend(check_taste(file_path))

    return diagnostics
