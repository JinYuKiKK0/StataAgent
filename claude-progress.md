# 仓库的紧凑跨会话交接

# 在会话开始时阅读此文件并保持其小而精。

# 使用 git 历史记录作为按时间顺序的更改历史。

## 项目状态

- 当前阶段：S2（理论预判与模型构建）
- 总体进度：3/18 features 完成（S1-T1、S1-T2、S1-T3）
- 最后更新：2026-03-24
- 阻塞问题：无；下一优先任务为 `S2-T1`

## 当前上下文

<!-- 每个会话覆盖此部分。保持简洁。 -->

- 正在处理：完成 LangChain/LangGraph 最小工程加固，补齐核心依赖显式声明并将工作流节点更新改为 LangGraph 推荐的局部状态更新
- 阶段：S2 进行中（S2-T1 仍是下一优先功能），本次为后续 S5-T4 编排与 HITL/持久化预留基础
- 分支：main
- 关键文件：
  - `pyproject.toml` — 显式新增 `langchain-core` 与 `langsmith` 依赖，维持 LangChain/LangGraph 1.x 版本区间
  - `src/stata_agent/workflow/orchestrator.py` — `StateGraph.compile` 接入 `InMemorySaver`；`run` 调用增加 `thread_id`；节点返回值改为 partial update dict
- 未解决的问题：
  - `pre-commit run --all-files` 在当前沙箱中需要显式设置 `PRE_COMMIT_HOME` 到仓库内可写目录；普通开发机默认缓存目录通常可直接工作
  - 真实 Tongyi API 需要用户在 `.env` 中提供可用的 `DASHSCOPE_API_KEY`；当前验证以注入式测试替身覆盖，不包含线上密钥调用
- 已安装依赖：当前 `.venv` 已可用 `langchain`、`langgraph`、`langchain-community`、`dashscope`、`pydantic`、`rich`、`typer`、`pytest`、`pyright`、`import-linter`、`ruff` 和 `pre-commit`
- 开发服务器：不适用

## 已知问题

<!-- 仅保留跨会话相关的活动问题。 -->
<!-- 格式：[开放日期] 问题：<描述> | 状态：开放/已解决 | 已解决：[日期] -->

- [2026-03-23] 问题：`feature_list.json` 仅包含阶段外壳，没有具体的功能条目。 | 状态：已解决 | 已解决：2026-03-23
