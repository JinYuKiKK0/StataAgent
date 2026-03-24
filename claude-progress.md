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

- 正在处理：补齐仓库级 agent harness 文档，定义 Agent 编码、架构边界与代码风格的机械约束方案
- 阶段：治理设计（未推进新的产品 feature）
- 分支：main
- 关键文件：
  - docs/engineering/agent-harness.md — StataAgent 的 harness engineering 单一事实来源，覆盖目标目录模型、边界契约、taste invariants、lint/CI 方案与实施路线。
  - docs/README.md — 已接入 harness 文档到阅读顺序与单一事实来源索引。
  - AGENTS.md — 已补充 harness 文档到仓库导航入口。
- 未解决的问题：
  - 约束方案仍停留在文档设计层，`tools/harness`、`pre-commit`、`mypy`、`ruff` 和结构测试尚未落地
  - 最高优先级产品 feature 仍为 S1-T2（LangChain Parse），本次未推进业务实现
- 已安装依赖：通过 `uv` 管理的本地环境，包含 `pydantic`、`python-dotenv`、`rich`、`typer` 和 `pytest`
- 开发服务器：不适用

## 已知问题

<!-- 仅保留跨会话相关的活动问题。 -->
<!-- 格式：[开放日期] 问题：<描述> | 状态：开放/已解决 | 已解决：[日期] -->

- [2026-03-23] 问题：`feature_list.json` 仅包含阶段外壳，没有具体的功能条目。 | 状态：已解决 | 已解决：2026-03-23
