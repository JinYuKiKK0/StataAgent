from __future__ import annotations

import ast
from fnmatch import fnmatch
from pathlib import Path

from tools.harness.diagnostics import Diagnostic

BANNED_FILENAMES = {"utils.py", "helpers.py", "common.py", "misc.py", "temp.py"}
INTERFACE_SEGMENT = "src/stata_agent/interfaces/"
OUTPUT_EXEMPT_PATTERNS = ("tools/**/__main__.py", "tools/run_*.py")
MAX_FILE_LINES = 350


def check_path(path: str | Path) -> list[Diagnostic]:
    source_path = Path(path)
    if source_path.name not in BANNED_FILENAMES:
        return []

    return [
        Diagnostic(
            code="SA4001",
            path=str(source_path),
            message="Banned catch-all filename",
            why="Catch-all filenames encourage dumping unrelated logic into vague modules that agents keep reusing.",
            fix="Rename the file to reflect one explicit responsibility such as settings.py, parser.py, or rule_taste.py.",
        )
    ]


def check_file(path: str | Path) -> list[Diagnostic]:
    source_path = Path(path)
    source = source_path.read_text(encoding="utf-8")
    lines = source.splitlines()
    tree = ast.parse(source, filename=str(source_path))
    diagnostics = check_path(source_path)
    in_interfaces = INTERFACE_SEGMENT in source_path.as_posix()
    output_exempt = _is_output_exempt(source_path)

    if len(lines) > MAX_FILE_LINES:
        diagnostics.append(
            Diagnostic(
                code="SA4002",
                path=str(source_path),
                message="File exceeds maximum line budget",
                why="Large files hide responsibility boundaries and degrade future agent edits.",
                fix=f"Split the file into focused modules so it stays at or below {MAX_FILE_LINES} lines.",
            )
        )

    for node in ast.walk(tree):
        if not in_interfaces and not output_exempt and isinstance(node, ast.Call):
            diagnostics.extend(_check_call_for_taste(node, source_path))

        if isinstance(node, ast.ExceptHandler):
            diagnostics.extend(_check_except_handler(node, source_path))

    return diagnostics


def _is_output_exempt(path: Path) -> bool:
    candidates = _path_match_candidates(path)
    return any(
        fnmatch(candidate, pattern)
        for candidate in candidates
        for pattern in OUTPUT_EXEMPT_PATTERNS
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


def _check_call_for_taste(node: ast.Call, source_path: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    if isinstance(node.func, ast.Name) and node.func.id == "print":
        diagnostics.append(
            Diagnostic(
                code="SA3001",
                path=f"{source_path}:{node.lineno}",
                message="print() used outside interface layer",
                why="User-visible output must stay in the interface layer so runtime and service code remain composable.",
                fix="Move the output to src/stata_agent/interfaces or replace it with structured logging.",
            )
        )

    if isinstance(node.func, ast.Attribute):
        if node.func.attr == "print":
            diagnostics.append(
                Diagnostic(
                    code="SA3002",
                    path=f"{source_path}:{node.lineno}",
                    message="Console.print() used outside interface layer",
                    why="Rich console output is an interface concern and should not leak into providers or business logic.",
                    fix="Raise a typed error or emit structured logs; let the interface decide how to render it.",
                )
            )

        if isinstance(node.func.value, ast.Name) and node.func.value.id == "sys" and node.func.attr == "exit":
            diagnostics.append(
                Diagnostic(
                    code="SA3003",
                    path=f"{source_path}:{node.lineno}",
                    message="sys.exit() used outside interface layer",
                    why="Lower layers must surface typed failures instead of terminating the process directly.",
                    fix="Raise a typed exception and let the interface layer translate it into an exit code.",
                )
            )

    return diagnostics


def _check_except_handler(node: ast.ExceptHandler, source_path: Path) -> list[Diagnostic]:
    for statement in node.body:
        if isinstance(statement, ast.Pass):
            return [
                Diagnostic(
                    code="SA3004",
                    path=f"{source_path}:{statement.lineno}",
                    message="except block silently passes",
                    why="Silent exception swallowing hides real failures and creates non-auditable control flow.",
                    fix="Handle the exception explicitly, log it, or re-raise a typed error.",
                )
            ]

    return []
