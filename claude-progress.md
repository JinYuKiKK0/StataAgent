# 仓库的紧凑跨会话交接

# 在会话开始时阅读此文件并保持其小而精。

# 使用 git 历史记录作为按时间顺序的更改历史。

## 项目状态

- 当前阶段：S1（需求解析与最低可行数据契约）
- 总体进度：7/24 features 完成（S1-T1~S1-T7）
- 最后更新：2026-03-28
- 阻塞问题：无；S1 阶段圆满完成，即将进入 S2 阶段（核心为 `S2-T1` 理论预期与基准方程摘要）

## 当前上下文

<!-- 每个会话覆盖此部分。保持简洁。 -->

- 本会话完成：按 `PLAN.md` 落地 harness 与本地 gate 治理修复。
  - `tools/harness/rule_taste.py`：文件上限统一为 350 行，移除函数 40 行限制；保留 `tools/**/__main__.py` 与 `tools/run_*.py` 输出豁免。
  - `tools/harness/__main__.py`、`tools/harness/rules_manifest.py`：`tools.harness lint` 默认扫描 `src tests tools`，默认排除 `**/__pycache__/**`、`.venv/**`、`tests/fixtures/harness/**`。
  - Gateway 强类型链路：新增 `GatewayResumeRequest`，CLI 决策输入与 `ApplicationOrchestrator.resume` 全部改为显式契约；`gateway_approval_node` 改为返回 `ResearchState`，移除 `dict[str, Any]` 边界泄漏。
  - 类型修复：`ChatTongyi` 直接接收 `SecretStr` API key；`providers/csmar.py` 递归辅助函数补窄化；`workflow/graph.py` 与 `workflow/orchestrator.py` 补 `BaseCheckpointSaver[str]` 等类型收紧；`tests/conftest.py` 对 `request.node` 做协议化 cast。
  - 新增统一入口 `tools/run_quality_gates.py`（顺序执行 ruff、pyright、import-linter、architecture tests、harness；失败不中断，最终统一返回码）。
  - 目录精简：`tests/architecture/` 中用于治理升级过程的中间元测试
    `test_harness_taste_rules.py`、`test_harness_scope_defaults.py`、`test_quality_gates.py` 已移除；保留核心结构契约测试集。
- 文档同步：`AGENTS.md` 与 `docs/engineering/agent-harness.md` 更新为提交前执行 `uv run python -m tools.run_quality_gates`。
- 环境补全：项目根目录新增 `.env` 占位模板（`WORKSPACE_DIR`、`DASHSCOPE_API_KEY`、`TONGYI_MODEL`、`CSMAR_*`）。
- 测试结果：
  - `uv run python -m pyright` ✅
  - `uv run python -m tools.harness lint` ✅
  - `uv run pytest tests/architecture -q` ✅（13 passed）
  - `uv run pytest tests/core_workflow/test_workflow_orchestrator.py tests/entrypoints/test_agent_graph.py tests/entrypoints/test_bootstrap.py -q` ✅（3 passed, 7 skipped）
  - `uv run python -m tools.run_quality_gates` ✅
  - `PRE_COMMIT_HOME=.pre-commit-cache uv run pre-commit run --all-files` ✅
- 当前阶段：S1 交付状态不变；产品 feature 仍待进入 `S2-T1`。
- 分支：main
- 关键文件：
  - `tools/run_quality_gates.py` — 本地统一 gate 入口。
  - `tools/harness/rule_taste.py`、`tools/harness/rules_manifest.py`、`tools/harness/__main__.py` — taste 规则与默认扫描范围更新。
  - `src/stata_agent/workflow/graph.py`、`src/stata_agent/workflow/orchestrator.py`、`src/stata_agent/interfaces/cli.py`、`src/stata_agent/domains/fetch/types.py` — Gateway 审批恢复强类型化。
  - `tests/architecture/` — 仅保留核心架构契约测试文件（边界、导入、模块布局、工具链）。
- 未解决的问题：
  - 当前环境缺少 `csmarapi` SDK，导致 CSMAR live tests 被跳过；安装 SDK 并配置 `CSMAR_ACCOUNT`/`CSMAR_PASSWORD` 后可执行完整真实链路测试
  - 当前沙箱运行 `pre-commit run --all-files` 仍建议显式设置 `PRE_COMMIT_HOME=.pre-commit-cache`
- 已安装依赖：当前 `.venv` 已可用 `langchain`、`langgraph`、`langchain-community`、`dashscope`、`pydantic`、`rich`、`typer`、`pytest`、`pyright`、`import-linter`、`ruff` 和 `pre-commit`
- 开发服务器：不适用

## 已知问题

<!-- 仅保留跨会话相关的活动问题。 -->
<!-- 格式：[开放日期] 问题：<描述> | 状态：开放/已解决 | 已解决：[日期] -->

- [2026-03-23] 问题：`feature_list.json` 仅包含阶段外壳，没有具体的功能条目。 | 状态：已解决 | 已解决：2026-03-23
