"""规则级测试：边界 lint 规则能识别跨边界返回裸对象的违规。"""

from tools.harness.rule_boundaries import check_file


def test_boundary_rule_flags_dict_return() -> None:
    """验证 SA2001 会拦截跨边界返回裸 `dict` 的实现。"""
    diagnostics = check_file("tests/fixtures/harness/boundary_leaks/returns_dict.py")

    assert diagnostics[0].code == "SA2001"


def test_boundary_rule_flags_any_annotation() -> None:
    """验证 SA2002 会拦截跨边界 `Any` 注解，避免类型边界松散化。"""
    diagnostics = check_file("tests/fixtures/harness/boundary_leaks/returns_any.py")

    assert diagnostics[0].code == "SA2002"
