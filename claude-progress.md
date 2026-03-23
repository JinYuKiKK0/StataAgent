# 仓库的紧凑跨会话交接

# 在会话开始时阅读此文件并保持其小而精。

# 使用 git 历史记录作为按时间顺序的更改历史。

## 项目状态

- 当前阶段：PROJECT_BOOTSTRAP
- 总体进度：0/5 阶段完成
- 最后更新：2026-03-23
- 阻塞问题：`feature_list.json` 仍没有具体的功能条目

## 架构决策

<!-- 仅当持久决策影响未来工作时才附加。 -->
<!-- 格式：[日期] 决策：<描述> | 原因：<为什么> -->

- [2026-03-23] 决策：将 `AGENTS.md` 视为简短的导航地图，将持久知识保留在 `ARCHITECTURE.md` 和 `docs/` 中。 | 原因：保留上下文预算，实现渐进式披露，并减少文档腐烂。
- [2026-03-23] 决策：退役根 `PLAN.md`，按所有权将持久内容拆分为 `ARCHITECTURE.md` 和 `docs/`。 | 原因：避免单块文档，并使知识库与主题边界保持一致。
- [2026-03-23] 决策：保持 `claude-progress.md` 为紧凑的交接文件，不含会话日志。 | 原因：保留跨会话记忆，同时保持重复的启动上下文较小；依赖 git 获取按时间顺序的记录。
- [2026-03-23] 决策：使用 `uv` 作为项目依赖管理工具，并采用 `src/stata_agent` 分层包布局。 | 原因：与本地 Python 3.12 工作流兼容，便于后续按应用层、领域层、服务层、适配器层和工作流层扩展。

## 当前上下文

<!-- 每个会话覆盖此部分。保持简洁。 -->

- 正在处理：已完成 UV 项目初始化和最小可导入包骨架；下一个可能的工作是补充具体 feature 条目并开始 S1 实现
- 阶段：项目 bootstrap
- 分支：main
- 关键文件：
  - pyproject.toml — UV 项目配置、依赖和脚本入口
  - uv.lock — 锁定的 Python 依赖
  - src/stata_agent/cli.py — CLI 入口和根命令回调
  - src/stata_agent/domain/models.py — 核心领域数据契约
  - src/stata_agent/workflows/states.py — 工作流共享状态模型
  - tests/test_bootstrap.py — bootstrap 导入和 CLI 帮助测试
- 未解决的问题：
  - `feature_list.json` 的阶段仍为空的功能数组
  - 具体业务实现仍停留在骨架阶段，CSMAR、LangGraph 和 Stata executor 适配尚未接入
- 已安装依赖：通过 `uv` 管理的本地环境，包含 `pydantic`、`pydantic-settings`、`rich`、`typer` 和 `pytest`
- 开发服务器：不适用

## 已知问题

<!-- 仅保留跨会话相关的活动问题。 -->
<!-- 格式：[开放日期] 问题：<描述> | 状态：开放/已解决 | 已解决：[日期] -->

- [2026-03-23] 问题：`feature_list.json` 仅包含阶段外壳，没有具体的功能条目。 | 状态：开放
