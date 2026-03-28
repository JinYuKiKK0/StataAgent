"""规则级测试：taste invariants 会把常见坏味道转成可机检违规。"""

from tools.harness.rule_taste import check_file, check_path


def test_taste_rule_flags_console_print_outside_interface() -> None:
    """验证 SA3002 会阻止非接口层直接输出终端文本。"""
    diagnostics = check_file(
        "tests/fixtures/harness/taste_violations/prints_in_service.py"
    )

    assert diagnostics[0].code == "SA3002"


def test_taste_rule_flags_except_pass() -> None:
    """验证 SA3004 会阻止吞异常的静默失败模式。"""
    diagnostics = check_file("tests/fixtures/harness/taste_violations/except_pass.py")

    assert diagnostics[0].code == "SA3004"


def test_taste_rule_flags_banned_filename() -> None:
    """验证 SA4001 会阻止 `utils.py` 这类模糊职责文件名。"""
    diagnostics = check_path("tests/fixtures/harness/taste_violations/utils.py")

    assert diagnostics[0].code == "SA4001"
