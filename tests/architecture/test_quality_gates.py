"""统一 quality gate 入口回归测试。"""

import re
import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from tools import run_quality_gates as quality_gate_module
from tools.run_quality_gates import QUALITY_GATES
from tools.run_quality_gates import run_quality_gates


def _normalize_command(command: str) -> str:
    return " ".join(command.strip().split()).removeprefix("uv run ").strip()


def test_run_quality_gates_returns_zero_when_all_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """所有 gate 成功时统一入口返回 0。"""
    executed: list[tuple[str, ...]] = []

    def fake_run(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        executed.append(tuple(command))
        return subprocess.CompletedProcess(args=list(command), returncode=0, stdout="", stderr="")

    monkeypatch.setattr(quality_gate_module, "_run_command", fake_run)

    exit_code = run_quality_gates()

    assert exit_code == 0
    assert executed == [gate.argv for gate in QUALITY_GATES]


def test_run_quality_gates_continues_after_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """任一 gate 失败时仍继续执行剩余 gate，并最终返回非零。"""
    executed: list[tuple[str, ...]] = []
    return_codes = iter((0, 1, 0, 0, 0))

    def fake_run(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        executed.append(tuple(command))
        return subprocess.CompletedProcess(
            args=list(command),
            returncode=next(return_codes),
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(quality_gate_module, "_run_command", fake_run)

    exit_code = run_quality_gates()

    assert exit_code == 1
    assert executed == [gate.argv for gate in QUALITY_GATES]


def test_quality_gates_match_precommit_and_ci_configuration() -> None:
    """统一入口、pre-commit 与 CI 的 gate 列表必须保持一致。"""
    expected = [gate.canonical_command for gate in QUALITY_GATES]

    pre_commit_content = Path(".pre-commit-config.yaml").read_text(encoding="utf-8")
    pre_commit_entries = re.findall(
        r"^\s*entry:\s*(.+?)\s*$",
        pre_commit_content,
        flags=re.MULTILINE,
    )
    assert [_normalize_command(entry) for entry in pre_commit_entries] == expected

    workflow_content = Path(".github/workflows/harness.yml").read_text(
        encoding="utf-8"
    )
    workflow_runs = re.findall(
        r"^\s*run:\s*(.+?)\s*$",
        workflow_content,
        flags=re.MULTILINE,
    )
    expected_set = set(expected)
    workflow_gate_commands = {
        normalized
        for command in workflow_runs
        for normalized in [_normalize_command(command)]
        if normalized in expected_set
    }

    assert workflow_gate_commands == expected_set
