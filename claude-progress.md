# 仓库的紧凑跨会话交接

# 在会话开始时阅读此文件并保持其小而精。

# 使用 git 历史记录作为按时间顺序的更改历史。

## 项目状态

- 当前阶段：S1（需求解析与最低可行数据契约）
- 总体进度：6/24 features 完成（S1-T1、S1-T2、S1-T3、S1-T4、S1-T5、S1-T6）
- 最后更新：2026-03-26
- 阻塞问题：无；下一优先任务为 `S1-T7`

## 当前上下文

<!-- 每个会话覆盖此部分。保持简洁。 -->

- 正在处理：完成 `S1-T6`（最低可行数据契约构建）全链路落地，新增契约包类型、契约构建服务、编排节点与 `CONTRACTED` 阶段。
- 阶段：S1（需求解析与最低可行数据契约）
- 分支：main
- 关键文件：
  - `feature_list.json` — `S1-T6` 已设置 `passes: true`；下一优先任务按列表顺序为 `S1-T7`（Gateway 审批中断与恢复）。
  - `src/stata_agent/domains/fetch/types.py` — 新增 `DataContractBundle` 最低可行数据契约模型。
  - `src/stata_agent/services/data_contract_builder.py` — 新增契约聚合服务，整合 Hard/Soft 分层、允许剔除列表、替代记录与残余风险。
  - `src/stata_agent/workflow/ports.py` — 提取编排端口协议，控制 `orchestrator.py` 行数满足 harness 限制。
  - `src/stata_agent/workflow/orchestrator.py` — 新增 `build_data_contract` 节点，成功路径推进到 `RunStage.CONTRACTED`。
  - `src/stata_agent/workflow/state.py` / `src/stata_agent/workflow/types.py` — 新增 `data_contract_bundle` 状态字段与 `CONTRACTED` 阶段。
  - `tests/test_data_contract_builder.py` / `tests/test_workflow_orchestrator.py` — 补齐 S1-T6 契约构建与状态机测试。
  - `tests/test_variable_mapper.py` — 补充 `query_count` 测试替身方法，修复 pyright 协议校验。
  - `docs/product/empirical-analysis-workflow.md` — 当前产品流程单一事实来源。
  - `AGENTS.md` — 会话工作流逻辑；现在按照列表顺序选择下一项。
- 未解决的问题：
  - `pre-commit run --all-files` 在当前沙箱中需要显式设置 `PRE_COMMIT_HOME` 到仓库内可写目录；普通开发机默认缓存目录通常可直接工作
  - 真实 Tongyi API 需要用户在 `.env` 中提供可用的 `DASHSCOPE_API_KEY`；当前验证以注入式测试替身覆盖，不包含线上密钥调用
- 已安装依赖：当前 `.venv` 已可用 `langchain`、`langgraph`、`langchain-community`、`dashscope`、`pydantic`、`rich`、`typer`、`pytest`、`pyright`、`import-linter`、`ruff` 和 `pre-commit`
- 开发服务器：不适用

## 已知问题

<!-- 仅保留跨会话相关的活动问题。 -->
<!-- 格式：[开放日期] 问题：<描述> | 状态：开放/已解决 | 已解决：[日期] -->

- [2026-03-23] 问题：`feature_list.json` 仅包含阶段外壳，没有具体的功能条目。 | 状态：已解决 | 已解决：2026-03-23
