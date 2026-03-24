from pathlib import Path


def test_harness_tooling_files_exist() -> None:
    assert Path("pyrightconfig.json").exists()
    assert Path(".importlinter").exists()
    assert Path(".pre-commit-config.yaml").exists()
    assert Path(".github/workflows/harness.yml").exists()
