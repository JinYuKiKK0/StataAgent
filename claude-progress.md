# 仓库的紧凑跨会话交接

# 在会话开始时阅读此文件并保持其小而精。

# 使用 git 历史记录作为按时间顺序的更改历史。

## 项目状态

- 当前阶段：S1（需求解析与最低可行数据契约）
- 总体进度：7/24 features 完成（S1-T1~S1-T7）
- 最后更新：2026-04-06
- 阻塞问题：无；S1 阶段圆满完成，即将进入 S2 阶段（核心为 `S2-T1` 理论预期与基准方程摘要）

## 当前上下文

<!-- 每个会话覆盖此部分。保持简洁。 -->

- 本会话完成：继续清理 Phase1 重构后的遗留代码，把旧变量语义判别链路和 app 层 `search_*` 快捷接口从主仓库退场。
  - `src/stata_agent/providers/llm.py`：删除旧 `TongyiVariableSemanticJudge`、候选判别 payload 和相关格式化逻辑；该文件现在只承载研究请求解析器。
  - `src/stata_agent/domains/mapping/types.py`、`ports.py`、`__init__.py`：删除仅服务旧链路的 `VariableSemanticJudgePort`、`VariableMatchDecision`、`CsmarFieldCandidate` 以及 app 层不再消费的 `CsmarTableSearchRequest/Candidate`、`CsmarFieldSearchRequest/Hit`。
  - `src/stata_agent/providers/csmar/client.py`：删除 `search_tables()` 与 `search_fields()` 两个 app 层快捷接口，桥接客户端只保留当前主流程在用的 `list_databases/list_tables/get_table_schema/probe/materialize` 能力。
  - `tests/s1_feasibility/test_csmar_bridge_mcp_adapter.py`：删掉面向旧 `search_*` 快捷接口的测试，改为覆盖 `list_databases -> list_tables -> get_table_schema` 的现行桥接契约和 trace 行为。
  - `tests/s1_feasibility/test_t4_variable_mapper_core.py`：把仍然有效的构造器内联进测试文件；删除旧中间支撑文件 `tests/s1_feasibility/t4_variable_mapper_support.py`。
  - `tests/architecture/test_legacy_mapping_cleanup.py`：新增回归测试，禁止旧 semantic judge 和 app 层 `search_*` 接口再次暴露。
  - `src/stata_agent/workflow/stages/phase1_feasibility.py` 已复核；其中 trace 收口/合并逻辑仍在主路径生效，本轮未删改。
- 测试结果：
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/architecture/test_legacy_mapping_cleanup.py -q` ✅
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/s1_feasibility/test_t4_variable_mapper_core.py -q` ✅
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/s1_feasibility/test_csmar_bridge_mcp_adapter.py -q` ✅
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests -q -m 'not live_api'` ✅（43 passed, 15 deselected）
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python -m pyright` ✅
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python -m tools.run_quality_gates` ⚠️：`ruff` / `pyright` / `import-linter` / `architecture` 通过；`tools.harness lint` 仍只剩仓库既有问题 `src/stata_agent/interfaces/cli.py` 触发 `SA4002`，非本会话引入。
- 当前阶段：产品总体阶段不变，`feature_list.json` 未改动，S2 待办顺序不变。
- 分支：main
- 关键文件：
  - `src/stata_agent/providers/llm.py` — 已收缩为纯研究请求解析器。
  - `src/stata_agent/providers/csmar/client.py` — app 层桥接客户端不再暴露旧 `search_*` 快捷能力。
  - `tests/architecture/test_legacy_mapping_cleanup.py` — 遗留链路退场回归约束。
- 未解决的问题：
  - 当前环境缺少 `RUN_LIVE_API_TESTS=1` 与完整 CSMAR/Tongyi live 配置，因此真实 E2E 仅保留 smoke 测试代码，未在本会话执行。
  - `src/stata_agent/interfaces/cli.py` 仍触发既有 `SA4002` 文件超长告警；若要让统一质量门全绿，需要单独拆分 CLI 文件。
- 已安装依赖：当前 `.venv` 已可用 `langchain`、`langgraph`、`langchain-community`、`dashscope`、`pydantic`、`rich`、`typer`、`pytest`、`pyright`、`import-linter`、`ruff` 和 `pre-commit`
- 开发服务器：不适用

## 已知问题

<!-- 仅保留跨会话相关的活动问题。 -->
<!-- 格式：[开放日期] 问题：<描述> | 状态：开放/已解决 | 已解决：[日期] -->

- [2026-03-23] 问题：`feature_list.json` 仅包含阶段外壳，没有具体的功能条目。 | 状态：已解决 | 已解决：2026-03-23
