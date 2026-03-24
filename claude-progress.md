# 仓库的紧凑跨会话交接

# 在会话开始时阅读此文件并保持其小而精。

# 使用 git 历史记录作为按时间顺序的更改历史。

## 项目状态

- 当前阶段：S1（需求解析与数据定义）
- 总体进度：2/18 features 完成（S1-T1、S1-T2）
- 最后更新：2026-03-24
- 阻塞问题：无；下一优先任务为 `S1-T3`

## 当前上下文

<!-- 每个会话覆盖此部分。保持简洁。 -->

- 正在处理：已将 `ARCHITECTURE.md` 收口为固定源码目录结构和分层边界的单一事实来源，并把运行状态机与阶段工件要求下沉到 `docs/product/research-workflow.md`
- 阶段：S1 架构收口
- 分支：main
- 关键文件：
  - `ARCHITECTURE.md` — 现固定 `src/stata_agent/` 的正式根目录为 `interfaces/`、`workflow/`、`domains/`、`services/`、`providers/`、`templates/`
  - `docs/engineering/agent-harness.md` — 现只保留稳定 harness 规则，不再承载迁移目标目录模型或实施计划
  - `docs/product/research-workflow.md` — 现承接运行状态机和阶段工件检查点
  - `AGENTS.md` / `docs/README.md` — 已同步新的文档边界和阅读导航
- 未解决的问题：
  - `pre-commit run --all-files` 在当前沙箱中需要显式设置 `PRE_COMMIT_HOME` 到仓库内可写目录；普通开发机默认缓存目录通常可直接工作
  - 真实 Tongyi API 需要用户在 `.env` 中提供可用的 `DASHSCOPE_API_KEY`；当前验证以注入式测试替身覆盖，不包含线上密钥调用
- 已安装依赖：当前 `.venv` 已可用 `langchain`、`langgraph`、`langchain-community`、`dashscope`、`pydantic`、`rich`、`typer`、`pytest`、`pyright`、`import-linter`、`ruff` 和 `pre-commit`
- 开发服务器：不适用

## 已知问题

<!-- 仅保留跨会话相关的活动问题。 -->
<!-- 格式：[开放日期] 问题：<描述> | 状态：开放/已解决 | 已解决：[日期] -->

- [2026-03-23] 问题：`feature_list.json` 仅包含阶段外壳，没有具体的功能条目。 | 状态：已解决 | 已解决：2026-03-23
