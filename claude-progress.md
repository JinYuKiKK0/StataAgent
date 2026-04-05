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

- 本会话完成：重做 S1 内部映射/探针能力，并将 `providers/csmar.py` 重构为 package façade。
  - `src/stata_agent/providers/csmar/`：新增 `client.py`、`catalog.py`、`errors.py`；`CsmarBridgeClient` 改为 `search_field_candidates + probe_field_availability` 的 gateway-first 形状，删除 `_DEFAULT_CATALOG` 主路径。
  - `src/stata_agent/domains/mapping/types.py`、`ports.py`：新增 `CsmarFieldSearchRequest`、`CsmarFieldProbeRequest`、`CsmarFieldProbeResult`、`VariableMatchDecision`，并为 `VariableMappingResult` 补 `resolved_variable_definitions`。
  - `src/stata_agent/providers/llm.py`：新增 `TongyiVariableSemanticJudge`，默认编排改为 `metadata provider + semantic judge` 的组合映射。
  - `src/stata_agent/services/variable_requirements_builder.py`：`source_domain_hint` 改为 `pending_resolution`；域解析从 builder 阶段后移。
  - `src/stata_agent/services/variable_mapper.py`：改为“候选检索 + 语义判别 + 启发式回退”，并在映射成功后回填 `VariableDefinition.source_domain_hint`。
  - `src/stata_agent/services/probe_executor.py`：改为消费结构化 scoped probe 结果，保留 `query_fingerprint`、`scope_level` 与供应商消息。
  - `src/stata_agent/workflow/stages/phase1_feasibility.py`：映射节点会把解析后的 `resolved_variable_definitions` 写回 `ResearchState`，不改阶段顺序。
- 测试同步：
  - `tests/s1_feasibility/test_t4_variable_mapper.py`、`test_t5_probe_executor.py` 现在同时覆盖 fake 单测与 live smoke；新增语义同义映射、soft gap、不阻断与供应商冷却错误场景。
  - `tests/live_api_support.py` 的 live Phase 1 fixture 现在会注入 `TongyiVariableSemanticJudge`。
- 测试结果：
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/s1_feasibility/test_t3_variable_requirements_builder.py tests/s1_feasibility/test_t4_variable_mapper.py tests/s1_feasibility/test_t5_probe_executor.py tests/s1_feasibility/test_t6_data_contract_builder.py -q` ✅（14 passed, 4 skipped）
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python -m pyright` ✅
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/architecture -q tests/entrypoints/test_bootstrap.py -q` ✅
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python -m tools.run_quality_gates` ⚠️：`pyright` / `import-linter` / `architecture` / `harness` 通过；`ruff check .` 因工作区已有 `docs/references/csmarapi/**` 参考代码报错失败，不是本会话改动引入。
- 当前阶段：产品总体阶段仍是 S1 已交付后回炉增强；`feature_list.json` 未改动，S2 待办顺序不变。
- 分支：main
- 关键文件：
  - `src/stata_agent/providers/csmar/client.py`、`src/stata_agent/providers/csmar/catalog.py` — CSMAR gateway 与 catalog 归一化入口。
  - `src/stata_agent/providers/llm.py` — `TongyiVariableSemanticJudge`。
  - `src/stata_agent/services/variable_mapper.py`、`src/stata_agent/services/probe_executor.py` — S1 映射与 scoped probe 新实现。
  - `src/stata_agent/domains/mapping/types.py` — 新的检索/探针/语义判别契约。
- 未解决的问题：
  - 当前环境缺少 `csmarapi` SDK，导致 CSMAR live tests 被跳过；安装 SDK 并配置 `CSMAR_ACCOUNT`/`CSMAR_PASSWORD` 后可执行完整真实链路测试
  - 当前沙箱运行 `pre-commit run --all-files` 仍建议显式设置 `PRE_COMMIT_HOME=.pre-commit-cache`
- 已安装依赖：当前 `.venv` 已可用 `langchain`、`langgraph`、`langchain-community`、`dashscope`、`pydantic`、`rich`、`typer`、`pytest`、`pyright`、`import-linter`、`ruff` 和 `pre-commit`
- 开发服务器：不适用

## 已知问题

<!-- 仅保留跨会话相关的活动问题。 -->
<!-- 格式：[开放日期] 问题：<描述> | 状态：开放/已解决 | 已解决：[日期] -->

- [2026-03-23] 问题：`feature_list.json` 仅包含阶段外壳，没有具体的功能条目。 | 状态：已解决 | 已解决：2026-03-23
