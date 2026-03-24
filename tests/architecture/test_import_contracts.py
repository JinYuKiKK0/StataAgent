import subprocess
import sys


def test_import_linter_contracts_pass() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.run_import_linter",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
