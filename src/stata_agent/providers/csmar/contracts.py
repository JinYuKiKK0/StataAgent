from pydantic import BaseModel, Field


class McpToolPayload(BaseModel):
    content: dict[str, object] = Field(default_factory=dict)
