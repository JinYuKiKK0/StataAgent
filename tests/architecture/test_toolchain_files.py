"""治理基线测试：仓库要求的静态检查与 CI 配置文件必须存在。"""

from pathlib import Path


def test_harness_tooling_files_exist() -> None:
    """验证本地与 CI 共用的工具链清单没有被误删。"""
    assert Path("pyrightconfig.json").exists()
    assert Path(".importlinter").exists()
    assert Path(".pre-commit-config.yaml").exists()
    assert Path(".github/workflows/harness.yml").exists()
