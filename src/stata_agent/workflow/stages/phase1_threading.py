from collections.abc import Mapping

from langchain_core.runnables.config import RunnableConfig


def resolve_thread_id(config: RunnableConfig | None, fallback: str) -> str:
    if config is None:
        return fallback
    configurable = config.get("configurable")
    if isinstance(configurable, Mapping):
        thread_id = configurable.get("thread_id")
        if isinstance(thread_id, str) and thread_id.strip():
            return thread_id
    return fallback
