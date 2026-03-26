# 仓库的紧凑跨会话交接

# 在会话开始时阅读此文件并保持其小而精。

# 使用 git 历史记录作为按时间顺序的更改历史。

## 项目状态

- 当前阶段：S1（需求解析与最低可行数据契约）
- 总体进度：4/24 features 完成（S1-T1、S1-T2、S1-T3、S1-T4）
- 最后更新：2026-03-26
- 阻塞问题：无；下一优先任务为 `S1-T5`

## 当前上下文

<!-- 每个会话覆盖此部分。保持简洁。 -->

- 正在处理：完成 `S1-T4`（CSMAR 探针级变量映射）全链路落地，新增映射契约、provider 元数据探针、映射服务与编排节点。
- 阶段：S1（需求解析与最低可行数据契约）
- 分支：main
- 关键文件：
  - `feature_list.json` — `S1-T4` 已设置 `passes: true`；下一优先任务按列表顺序为 `S1-T5`（探针执行与覆盖摘要）。
  - `src/stata_agent/domains/mapping/types.py` — 扩展 `VariableBinding` 并新增 `VariableMappingResult`/`CsmarFieldCandidate`。
  - `src/stata_agent/providers/csmar.py` — 新增元数据候选检索与字段存在性探针能力。
  - `src/stata_agent/services/variable_mapper.py` — 实现 Hard/Soft Contract 判定与 fail-fast 映射逻辑。
  - `src/stata_agent/workflow/orchestrator.py` — 新增 `map_variables` 节点并推进到 `RunStage.MAPPED`。
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
