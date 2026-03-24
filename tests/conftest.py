from collections.abc import Generator

import pytest

from stata_agent.providers.settings import get_settings


@pytest.fixture(autouse=True)
def configure_test_settings(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("WORKSPACE_DIR", ".stata-agent")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-dashscope-key")
    monkeypatch.setenv("TONGYI_MODEL", "qwen-plus")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
