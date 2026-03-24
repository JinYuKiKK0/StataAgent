# 仓库的紧凑跨会话交接

# 在会话开始时阅读此文件并保持其小而精。

# 使用 git 历史记录作为按时间顺序的更改历史。

## 项目状态

- 当前阶段：S1（需求解析与数据定义）
- 总体进度：1/18 features 完成（S1-T1）
- 最后更新：2026-03-23
- 阻塞问题：无；下一优先任务为 `S1-T2`

## 当前上下文

<!-- 每个会话覆盖此部分。保持简洁。 -->

- 正在处理：仓库级 agent harness 第一阶段已落地，已完成工具链配置、包布局收口、契约拆分、`import-linter`、`pyright`、自定义 harness CLI 与第一批 taste 规则
- 阶段：治理实施（未推进新的产品 feature）
- 分支：main
- 关键文件：
  - docs/engineering/agent-harness.md — StataAgent 的 harness engineering 单一事实来源，覆盖目标目录模型、边界契约、taste invariants、lint/CI 方案与实施路线。
  - docs/engineering/2026-03-24-agent-harness-implementation-plan.md — 将 harness 设计拆成可执行 backlog，包含文件清单、任务切分、测试命令与推荐提交边界。
  - pyrightconfig.json / .importlinter — 已形成可运行的类型边界检查与架构导入约束。
  - tools/harness/ — 已落地最小可用自定义 harness，当前实现 `SA2001`、`SA2002`、`SA3001`、`SA3002`、`SA3003`、`SA3004`、`SA3005`、`SA4001`、`SA4002`。
  - tools/run_import_linter.py — 提供跨平台、非 `uv` 别名依赖的 import-linter 执行入口。
  - .pre-commit-config.yaml / .github/workflows/harness.yml — 已接入 `pyright`、`import-linter`、architecture tests 和 harness CLI 的阻断入口。
  - src/stata_agent/workflow/ — 已成为唯一保留的工作流包；旧 `src/stata_agent/workflows/` shim 已移除。
  - docs/README.md — 已接入 harness 文档到阅读顺序与单一事实来源索引。
  - AGENTS.md — 已补充 harness 文档到仓库导航入口。
- 未解决的问题：
  - `pre-commit run --all-files` 在当前沙箱中需要显式设置 `PRE_COMMIT_HOME` 到仓库内可写目录；普通开发机默认缓存目录通常可直接工作
  - 设计文档中的部分“未来规则”仍未全部实现，目前只落地了第一批核心规则和基础 taste/logging 约束
  - 最高优先级产品 feature 仍为 S1-T2（LangChain Parse），本次主要推进治理 harness 而非业务实现
- 已安装依赖：当前 `.venv` 已可用 `pydantic`、`python-dotenv`、`rich`、`typer`、`pytest`、`pyright`、`import-linter`、`ruff` 和 `pre-commit`
- 开发服务器：不适用

## 已知问题

<!-- 仅保留跨会话相关的活动问题。 -->
<!-- 格式：[开放日期] 问题：<描述> | 状态：开放/已解决 | 已解决：[日期] -->

- [2026-03-23] 问题：`feature_list.json` 仅包含阶段外壳，没有具体的功能条目。 | 状态：已解决 | 已解决：2026-03-23
