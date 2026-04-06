from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from stata_agent.workflow.gateway import GatewayDecision
from stata_agent.workflow.gateway import GatewayResumeRequest
from stata_agent.workflow.state import ResearchState


def render_contract_for_approval(console: Console, state: ResearchState) -> None:
    """呈递最低可行数据契约供用户审核。"""
    contract = state.phase1_artifacts.data_contract_bundle
    if contract is None:
        return

    if contract.entity_scope_inferred:
        console.print("\n[bold yellow]⚠ Gateway 审批：请审核最低可行数据契约[/bold yellow]")
        console.print(
            "[bold magenta]ℹ 样本范围为 Agent 推断，请特别确认是否正确[/bold magenta]\n"
        )
    else:
        console.print("\n[bold yellow]⚠ Gateway 审批：请审核最低可行数据契约[/bold yellow]\n")

    table = Table(title="最低可行数据契约")
    table.add_column("字段", style="cyan")
    table.add_column("值", style="white")

    table.add_row("分析粒度", contract.analysis_grain)
    entity_scope_label = contract.entity_scope
    if contract.entity_scope_inferred:
        entity_scope_label = f"{contract.entity_scope} (Agent 推断)"
    table.add_row("样本范围", entity_scope_label)
    table.add_row("时间范围", f"{contract.time_start_year}-{contract.time_end_year}")
    table.add_row("Hard Contract 变量", "、".join(contract.hard_contract_variables) or "无")
    table.add_row("Soft Contract 变量", "、".join(contract.soft_contract_variables) or "无")
    table.add_row("允许自动剔除", "、".join(contract.allowed_soft_removals) or "无")
    table.add_row("残余风险", "、".join(contract.residual_risks) or "无")
    table.add_row("替代记录", "、".join(contract.substitution_log) or "无")
    console.print(table)


def prompt_gateway_decision() -> GatewayResumeRequest:
    """交互式收集用户的 Approve/Reject 决策。"""
    approved = typer.confirm("是否批准该数据契约？")
    reason = ""
    if not approved:
        reason = typer.prompt("请输入驳回原因", default="")
    decision = GatewayDecision.APPROVED if approved else GatewayDecision.REJECTED
    return GatewayResumeRequest(decision=decision, reason=reason)
