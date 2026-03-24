from tools.harness.rule_boundaries import check_file


def test_boundary_rule_flags_dict_return() -> None:
    diagnostics = check_file("tests/fixtures/harness/boundary_leaks/returns_dict.py")

    assert diagnostics[0].code == "SA2001"


def test_boundary_rule_flags_any_annotation() -> None:
    diagnostics = check_file("tests/fixtures/harness/boundary_leaks/returns_any.py")

    assert diagnostics[0].code == "SA2002"
