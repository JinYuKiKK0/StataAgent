from tools.harness.rule_taste import check_file, check_path


def test_taste_rule_flags_console_print_outside_interface() -> None:
    diagnostics = check_file(
        "tests/fixtures/harness/taste_violations/prints_in_service.py"
    )

    assert diagnostics[0].code == "SA3002"


def test_taste_rule_flags_except_pass() -> None:
    diagnostics = check_file("tests/fixtures/harness/taste_violations/except_pass.py")

    assert diagnostics[0].code == "SA3004"


def test_taste_rule_flags_banned_filename() -> None:
    diagnostics = check_path("tests/fixtures/harness/taste_violations/utils.py")

    assert diagnostics[0].code == "SA4001"
