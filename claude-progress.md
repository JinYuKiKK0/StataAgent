# 仓库的紧凑跨会话交接

# 在会话开始时阅读此文件并保持其小而精。

# 使用 git 历史记录作为按时间顺序的更改历史。

## 项目状态

- 当前阶段：S1（需求解析与最低可行数据契约）
- 总体进度：7/24 features 完成（S1-T1~S1-T7）
- 最后更新：2026-03-26
- 阻塞问题：无；S1 阶段圆满完成，即将进入 S2 阶段（核心为 `S2-T1` 理论预期与基准方程摘要）

## 当前上下文

<!-- 每个会话覆盖此部分。保持简洁。 -->

- 正在处理：收敛 LangGraph 编排定义，抽出共享 `workflow/graph.py`，修复 LangSmith 入口 `agent.py:graph` 绕过 `ApplicationOrchestrator` 后在 `phase1_feasibility` 无参实例化 `Phase1FeasibilityOrchestrator` 的崩溃。
- 阶段：S1（需求解析与最低可行数据契约）已完成；当前主线候选仍为 `S2-T1`
- 分支：main
- 关键文件：
  - `feature_list.json` — `S1` 已全部通过，未改动 feature 定义；下一个候选仍为 `S2-T1`。
  - `src/stata_agent/workflow/graph.py` — 新增共享 LangGraph 拓扑与 Gateway 节点，成为 `agent.py` / `orchestrator.py` 的单一事实来源。
  - `src/stata_agent/workflow/orchestrator.py` — 改为复用共享 graph builder，并支持通过 `checkpointer_factory` 区分 CLI 本地持久化与 LangSmith Server 托管持久化。
  - `src/stata_agent/agent.py` — 精简为 LangSmith 薄适配层，仅导出复用核心编排的 `graph`。
  - `tests/test_agent_graph.py` — 新增 LangSmith 入口 smoke tests，覆盖 Gateway interrupt 和 Phase1 失败路径，防止编排漂移再次漏检。
- 未解决的问题：
  - `pre-commit run --all-files` 在当前沙箱中需要显式设置 `PRE_COMMIT_HOME` 到仓库内可写目录；普通开发机默认缓存目录通常可直接工作
  - 真实 Tongyi API 需要用户在 `.env` 中提供可用的 `DASHSCOPE_API_KEY`；当前验证以注入式测试替身覆盖，不包含线上密钥调用
- 已安装依赖：当前 `.venv` 已可用 `langchain`、`langgraph`、`langchain-community`、`dashscope`、`pydantic`、`rich`、`typer`、`pytest`、`pyright`、`import-linter`、`ruff` 和 `pre-commit`
- 开发服务器：不适用

## 已知问题

<!-- 仅保留跨会话相关的活动问题。 -->
<!-- 格式：[开放日期] 问题：<描述> | 状态：开放/已解决 | 已解决：[日期] -->

- [2026-03-23] 问题：`feature_list.json` 仅包含阶段外壳，没有具体的功能条目。 | 状态：已解决 | 已解决：2026-03-23
