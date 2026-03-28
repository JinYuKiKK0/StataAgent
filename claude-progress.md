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

- 本会话完成：按“去 mock”目标重构 S1 相关测试，移除 `s1_feasibility/`、`core_workflow/test_workflow_orchestrator.py`、`entrypoints/test_agent_graph.py`、`entrypoints/test_bootstrap.py` 中的 Successful/Failing 替身与 `monkeypatch` 注入路径，统一改为 `live_api` 真实接口集成测试；新增 `tests/live_api_support.py` 作为真实 Tongyi/CSMAR 夹具层。
- provider 更新：`src/stata_agent/providers/csmar.py` 从本地静态目录模拟改为真实 `csmarapi` SDK 调用（登录、`getListFields`、`queryCount`）；`src/stata_agent/providers/settings.py` 新增 `CSMAR_ACCOUNT`、`CSMAR_PASSWORD`、`CSMAR_LANGUAGE` 配置；`src/stata_agent/workflow/orchestrator.py` 注入真实 CSMAR 配置构造 provider。
- 测试结果：执行 `RUN_LIVE_API_TESTS=1 pytest tests/s1_feasibility tests/core_workflow/test_workflow_orchestrator.py tests/entrypoints/test_agent_graph.py tests/entrypoints/test_bootstrap.py -rs -q`，结果 **12 passed, 15 skipped**；跳过原因为当前环境未安装 `csmarapi` SDK，Tongyi 真实解析测试已实际运行通过。
- 当前阶段：S1 测试体系已完成真实接口化改造；后续候选仍为 `S2-T1`。
- 分支：main
- 关键文件：
  - `src/stata_agent/providers/csmar.py` — 真实 CSMAR 元数据/计数探针接入。
  - `src/stata_agent/providers/settings.py` — CSMAR 凭证配置入口。
  - `tests/live_api_support.py` — live API fixture 与运行前置检查。
  - `tests/s1_feasibility/`、`tests/core_workflow/test_workflow_orchestrator.py`、`tests/entrypoints/test_agent_graph.py`、`tests/entrypoints/test_bootstrap.py` — 已移除 mock/stub 路径并切换为 live_api 测试。
- 未解决的问题：
  - `pre-commit run --all-files` 在当前沙箱中需要显式设置 `PRE_COMMIT_HOME` 到仓库内可写目录；普通开发机默认缓存目录通常可直接工作
  - 当前环境缺少 `csmarapi` SDK，导致 CSMAR live tests 被跳过；安装 SDK 并配置 `CSMAR_ACCOUNT`/`CSMAR_PASSWORD` 后可执行完整真实链路测试
- 已安装依赖：当前 `.venv` 已可用 `langchain`、`langgraph`、`langchain-community`、`dashscope`、`pydantic`、`rich`、`typer`、`pytest`、`pyright`、`import-linter`、`ruff` 和 `pre-commit`
- 开发服务器：不适用

## 已知问题

<!-- 仅保留跨会话相关的活动问题。 -->
<!-- 格式：[开放日期] 问题：<描述> | 状态：开放/已解决 | 已解决：[日期] -->

- [2026-03-23] 问题：`feature_list.json` 仅包含阶段外壳，没有具体的功能条目。 | 状态：已解决 | 已解决：2026-03-23
