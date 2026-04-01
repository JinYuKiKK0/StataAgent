from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

QUALITY_GATES_COMMAND: tuple[str, ...] = (
    "uv",
    "run",
    "python",
    "-m",
    "tools.run_quality_gates",
)
GIT_COMMIT_PATTERN = re.compile(r"(?:^|\s)git\s+commit(?:\s|$)")
WORKSPACE_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class GateRunResult:
    return_code: int
    stdout: str
    stderr: str


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    if not args:
        _emit_json(
            {
                "continue": False,
                "stopReason": "Missing hook mode argument.",
                "systemMessage": "Hook misconfigured: mode is required.",
            }
        )
        return 2

    mode = args[0].strip().lower()
    payload = _read_stdin_payload()

    if mode == "session-start":
        _emit_json(_session_start_output())
        return 0
    if mode == "pre-tool-use":
        _emit_json(_pre_tool_use_output(payload))
        return 0
    if mode == "stop":
        output, exit_code = _stop_output()
        _emit_json(output)
        return exit_code

    _emit_json(
        {
            "continue": False,
            "stopReason": f"Unsupported hook mode: {mode}",
            "systemMessage": "Hook misconfigured: unsupported mode.",
        }
    )
    return 2


def _read_stdin_payload() -> dict[str, object]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"rawStdin": raw}

    if isinstance(parsed, dict):
        return parsed

    return {"payload": parsed}


def _session_start_output() -> dict[str, object]:
    return {
        "continue": True,
        "systemMessage": (
            "StataAgent workflow reminder: session start should check `git log --oneline -10`, "
            "read `claude-progress.md`, read `feature_list.json`, and announce one feature "
            "to work on before coding."
        ),
    }


def _pre_tool_use_output(payload: dict[str, object]) -> dict[str, object]:
    command_text = _extract_command_text(payload)
    if not _is_git_commit_command(command_text):
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "Not a git commit command.",
            }
        }

    result = _run_quality_gates()
    if result.return_code == 0:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "Quality gates passed; git commit is allowed.",
            },
            "systemMessage": "Quality gates passed before git commit.",
        }

    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "Blocked git commit because `uv run python -m tools.run_quality_gates` failed."
            ),
        },
        "systemMessage": (
            "Quality gates failed before git commit. Fix failures first.\n\n"
            f"{_failure_excerpt(result)}"
        ),
    }


def _stop_output() -> tuple[dict[str, object], int]:
    result = _run_quality_gates()
    if result.return_code == 0:
        return (
            {
                "continue": True,
                "systemMessage": "Stop hook check passed: local quality gates are green.",
            },
            0,
        )

    return (
        {
            "continue": False,
            "stopReason": "Stop blocked: quality gates failed.",
            "systemMessage": (
                "Session end validation failed: `uv run python -m tools.run_quality_gates` "
                "did not pass.\n\n"
                f"{_failure_excerpt(result)}"
            ),
        },
        2,
    )


def _run_quality_gates() -> GateRunResult:
    completed = subprocess.run(
        QUALITY_GATES_COMMAND,
        cwd=WORKSPACE_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return GateRunResult(
        return_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _extract_command_text(payload: dict[str, object]) -> str:
    preferred_values = _find_values_for_keys(payload, {"command", "cmd"})
    sequence_values = _find_values_for_keys(payload, {"args", "argv", "arguments"})

    candidates: list[str] = []
    for value in [*preferred_values, *sequence_values]:
        normalized = _normalize_command_candidate(value)
        if normalized:
            candidates.append(normalized)

    for candidate in candidates:
        if _is_git_commit_command(candidate):
            return candidate

    return candidates[0] if candidates else ""


def _find_values_for_keys(
    node: object,
    target_keys: set[str],
) -> list[object]:
    values: list[object] = []

    if isinstance(node, dict):
        for key, value in node.items():
            if key.lower() in target_keys:
                values.append(value)
            values.extend(_find_values_for_keys(value, target_keys))
        return values

    if isinstance(node, list):
        for item in node:
            values.extend(_find_values_for_keys(item, target_keys))

    return values


def _normalize_command_candidate(value: object) -> str:
    if isinstance(value, str):
        return value.strip()

    if isinstance(value, list):
        parts: list[str] = [part.strip() for part in value if isinstance(part, str)]
        return " ".join(part for part in parts if part)

    return ""


def _is_git_commit_command(command_text: str) -> bool:
    return bool(command_text) and bool(GIT_COMMIT_PATTERN.search(command_text))


def _failure_excerpt(result: GateRunResult) -> str:
    combined = "\n".join(
        part for part in [result.stdout.strip(), result.stderr.strip()] if part
    )
    if not combined:
        return "No output captured."

    lines = combined.splitlines()
    tail = lines[-40:]
    return "\n".join(tail)


def _emit_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
