"""架构契约测试：顶层包导入边界必须通过 import-linter。"""

import subprocess
import sys


def test_import_linter_contracts_pass() -> None:
    """验证仓库声明的导入方向仍然成立，没有出现跨层级反向依赖。"""
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
