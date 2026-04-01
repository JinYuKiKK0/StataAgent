from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class GateSpec:
    name: str
    canonical_command: str
    argv: tuple[str, ...]


QUALITY_GATES: tuple[GateSpec, ...] = (
    GateSpec(
        name="ruff",
        canonical_command="python -m ruff check .",
        argv=(sys.executable, "-m", "ruff", "check", "."),
    ),
    GateSpec(
        name="pyright",
        canonical_command="python -m pyright",
        argv=(sys.executable, "-m", "pyright"),
    ),
    GateSpec(
        name="import-linter",
        canonical_command="python -m tools.run_import_linter",
        argv=(sys.executable, "-m", "tools.run_import_linter"),
    ),
    GateSpec(
        name="architecture-tests",
        canonical_command="pytest tests/architecture -q",
        argv=(sys.executable, "-m", "pytest", "tests/architecture", "-q"),
    ),
    GateSpec(
        name="harness",
        canonical_command="python -m tools.harness lint",
        argv=(sys.executable, "-m", "tools.harness", "lint"),
    ),
)


def run_quality_gates(gates: Sequence[GateSpec] = QUALITY_GATES) -> int:
    results: list[tuple[GateSpec, int]] = []

    for gate in gates:
        print(f"\n=== [{gate.name}] uv run {gate.canonical_command} ===")
        completed = _run_command(gate.argv)
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        results.append((gate, completed.returncode))

    print("\n=== quality gates summary ===")
    has_failure = False
    for gate, return_code in results:
        status = "PASS" if return_code == 0 else "FAIL"
        print(f"[{status}] {gate.name}: uv run {gate.canonical_command}")
        if return_code != 0:
            has_failure = True

    return 1 if has_failure else 0


def _run_command(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    return run_quality_gates()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
