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

- 正在处理：已去除 `agent-harness.md` 对目录结构、架构依赖和稳定数据契约的重复复述；顶层包依赖现由 `.importlinter` 机械执行，并已收掉 `interfaces -> providers.settings` 与 `services -> workflow.types` 的现存违例
- 阶段：S1 架构收口
- 分支：main
- 关键文件：
  - `.importlinter` — 现匹配正式顶层结构 `interfaces / workflow / services / providers / domains`，并显式禁止活跃目录依赖 legacy shim
  - `src/stata_agent/workflow/orchestrator.py` — 现包裹配置启动错误，作为 `interfaces` 访问设置的唯一允许入口
  - `src/stata_agent/interfaces/cli.py` — 已移除对 `providers.settings` 的直接依赖
  - `ARCHITECTURE.md` / `docs/engineering/agent-harness.md` — 现分别承担“定义一次”与“治理执行”职责，不再重复维护依赖规则
- 未解决的问题：
  - `pre-commit run --all-files` 在当前沙箱中需要显式设置 `PRE_COMMIT_HOME` 到仓库内可写目录；普通开发机默认缓存目录通常可直接工作
  - 真实 Tongyi API 需要用户在 `.env` 中提供可用的 `DASHSCOPE_API_KEY`；当前验证以注入式测试替身覆盖，不包含线上密钥调用
- 已安装依赖：当前 `.venv` 已可用 `langchain`、`langgraph`、`langchain-community`、`dashscope`、`pydantic`、`rich`、`typer`、`pytest`、`pyright`、`import-linter`、`ruff` 和 `pre-commit`
- 开发服务器：不适用

## 已知问题

<!-- 仅保留跨会话相关的活动问题。 -->
<!-- 格式：[开放日期] 问题：<描述> | 状态：开放/已解决 | 已解决：[日期] -->

- [2026-03-23] 问题：`feature_list.json` 仅包含阶段外壳，没有具体的功能条目。 | 状态：已解决 | 已解决：2026-03-23
