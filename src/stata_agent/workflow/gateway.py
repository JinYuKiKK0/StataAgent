from enum import Enum

from pydantic import BaseModel


class GatewayDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


class GatewayRecord(BaseModel):
    decision: GatewayDecision
    reason: str = ""


class GatewayResumeRequest(BaseModel):
    decision: GatewayDecision = GatewayDecision.REJECTED
    reason: str = ""


class GatewayState(BaseModel):
    record: GatewayRecord | None = None
