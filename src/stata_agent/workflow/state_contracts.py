from __future__ import annotations

from typing import TypeAlias, TypedDict

from stata_agent.workflow.gateway import GatewayState
from stata_agent.workflow.observability import WorkflowNodeAudit
from stata_agent.workflow.state import Phase1Artifacts
from stata_agent.workflow.state import WorkflowAuditState
from stata_agent.workflow.types import RunStage

NodeAuditMap: TypeAlias = dict[str, WorkflowNodeAudit]


class Phase1StateUpdate(TypedDict, total=False):
    phase1_artifacts: Phase1Artifacts
    workflow_audit: WorkflowAuditState
    gateway_state: GatewayState
    stage: RunStage
