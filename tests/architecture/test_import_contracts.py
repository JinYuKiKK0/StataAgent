import subprocess
import sys


def test_import_linter_contracts_pass() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from importlinter.cli import lint_imports; raise SystemExit(lint_imports())",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
