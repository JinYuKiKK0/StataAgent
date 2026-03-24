from __future__ import annotations

import ast
from pathlib import Path

from tools.harness.diagnostics import Diagnostic


def check_file(path: str | Path) -> list[Diagnostic]:
    source_path = Path(path)
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    diagnostics: list[Diagnostic] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _is_bare_dict_annotation(node.returns):
                diagnostics.append(
                    Diagnostic(
                        code="SA2001",
                        path=f"{source_path}:{node.lineno}",
                        message="Boundary leak: function returns bare dict",
                        why="Cross-layer outputs must use explicit contract models to remain stable and auditable.",
                        fix="Return a named contract model such as ResearchSpec, ParseResult, or another explicit boundary type.",
                    )
                )

            if _function_uses_any(node):
                diagnostics.append(
                    Diagnostic(
                        code="SA2002",
                        path=f"{source_path}:{node.lineno}",
                        message="Boundary leak: function annotation uses Any",
                        why="Boundary contracts must remain explicit; Any hides shape drift and weakens downstream agent context.",
                        fix="Replace Any with a concrete model, scalar, collection element type, or union of explicit types.",
                    )
                )

    return diagnostics


def _function_uses_any(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    annotations: list[ast.expr | None] = [node.returns]
    annotations.extend(arg.annotation for arg in node.args.args)
    annotations.extend(arg.annotation for arg in node.args.kwonlyargs)
    if node.args.vararg is not None:
        annotations.append(node.args.vararg.annotation)
    if node.args.kwarg is not None:
        annotations.append(node.args.kwarg.annotation)

    return any(_annotation_contains_any(annotation) for annotation in annotations if annotation is not None)


def _annotation_contains_any(annotation: ast.expr) -> bool:
    if isinstance(annotation, ast.Name):
        return annotation.id == "Any"
    if isinstance(annotation, ast.Attribute):
        return annotation.attr == "Any"
    if isinstance(annotation, ast.Subscript):
        return _annotation_contains_any(annotation.value) or _annotation_contains_any(annotation.slice)
    if isinstance(annotation, ast.Tuple):
        return any(_annotation_contains_any(element) for element in annotation.elts)
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        return _annotation_contains_any(annotation.left) or _annotation_contains_any(annotation.right)
    return False


def _is_bare_dict_annotation(annotation: ast.expr | None) -> bool:
    if annotation is None:
        return False
    if isinstance(annotation, ast.Name):
        return annotation.id in {"dict", "Dict"}
    if isinstance(annotation, ast.Attribute):
        return annotation.attr == "Dict"
    if isinstance(annotation, ast.Subscript):
        return _is_bare_dict_annotation(annotation.value)
    return False
