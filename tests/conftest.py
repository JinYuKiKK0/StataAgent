import os
from collections.abc import Generator
from typing import Protocol, cast

import pytest

from stata_agent.providers.settings import get_settings


class _MarkerAwareNode(Protocol):
    def get_closest_marker(self, name: str) -> object: ...


class _NodeCarrier(Protocol):
    node: object


@pytest.fixture(autouse=True)
def configure_test_settings(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[None, None, None]:
    request_with_node = cast(_NodeCarrier, request)
    node = cast(_MarkerAwareNode, request_with_node.node)
    live_api_test = node.get_closest_marker("live_api") is not None
    if not live_api_test:
        monkeypatch.setenv("WORKSPACE_DIR", ".stata-agent")
        monkeypatch.setenv("DASHSCOPE_API_KEY", "test-dashscope-key")
        monkeypatch.setenv("TONGYI_MODEL", "qwen-plus")

    if os.getenv("RUN_LIVE_API_TESTS", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }:
        get_settings.cache_clear()
        yield
        get_settings.cache_clear()
        return

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
