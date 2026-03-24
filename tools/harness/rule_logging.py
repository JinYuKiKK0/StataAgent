from __future__ import annotations

import ast
from pathlib import Path

from tools.harness.diagnostics import Diagnostic


_ALLOWED_BASIC_CONFIG_PATH = Path("src/stata_agent/providers/logging.py")


def check_file(path: str | Path) -> list[Diagnostic]:
    source_path = Path(path)
    if source_path.as_posix() == _ALLOWED_BASIC_CONFIG_PATH.as_posix():
        return []

    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    diagnostics: list[Diagnostic] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "logging" and node.func.attr == "basicConfig":
                diagnostics.append(
                    Diagnostic(
                        code="SA3005",
                        path=f"{source_path}:{node.lineno}",
                        message="Logging setup uses logging.basicConfig outside providers/logging.py",
                        why="Logging bootstrap must stay centralized so agent code does not scatter global logging behavior.",
                        fix="Move logging bootstrap to src/stata_agent/providers/logging.py or use a structured logger entrypoint.",
                    )
                )

    return diagnostics
