# 仓库的紧凑跨会话交接

# 在会话开始时阅读此文件并保持其小而精。

# 使用 git 历史记录作为按时间顺序的更改历史。

## 项目状态

- 当前阶段：S2（理论预判与模型构建）
- 总体进度：3/18 features 完成（S1-T1、S1-T2、S1-T3）
- 最后更新：2026-03-25
- 阻塞问题：无；下一优先任务为 `S2-T1`

## 当前上下文

<!-- 每个会话覆盖此部分。保持简洁。 -->

- 正在处理：按用户要求收敛 `docs/product/empirical-analysis-workflow-v2.md`，保留三阶段叙事形式，同时补上 `Hard/Soft Contract`、Gateway 审批对象、核心 X/Y 探针失败即中止、`D3` 组装审计节点，以及 `E3` 技术性有界重试节点
- 阶段：S2 进行中（`S2-T1` 仍是下一优先功能）；本次仅修改 v2 工作流提案文档与交接，不变更业务实现与 feature 状态
- 分支：main
- 关键文件：
  - `docs/product/empirical-analysis-workflow-v2.md` — V2 提案文档；保留原有文风，补齐最低可行数据契约、软硬边界、可选扩展模块边界与技术性重试约束
  - `docs/product/empirical-analysis-workflow.md` — 当前产品流程单一事实来源；本次仅作为对照参考，未在本次任务中更新
  - `AGENTS.md` — 会话工作流和项目 skill 入口；本次按其要求补充交接
- 未解决的问题：
  - `pre-commit run --all-files` 在当前沙箱中需要显式设置 `PRE_COMMIT_HOME` 到仓库内可写目录；普通开发机默认缓存目录通常可直接工作
  - 真实 Tongyi API 需要用户在 `.env` 中提供可用的 `DASHSCOPE_API_KEY`；当前验证以注入式测试替身覆盖，不包含线上密钥调用
- 已安装依赖：当前 `.venv` 已可用 `langchain`、`langgraph`、`langchain-community`、`dashscope`、`pydantic`、`rich`、`typer`、`pytest`、`pyright`、`import-linter`、`ruff` 和 `pre-commit`
- 开发服务器：不适用

## 已知问题

<!-- 仅保留跨会话相关的活动问题。 -->
<!-- 格式：[开放日期] 问题：<描述> | 状态：开放/已解决 | 已解决：[日期] -->

- [2026-03-23] 问题：`feature_list.json` 仅包含阶段外壳，没有具体的功能条目。 | 状态：已解决 | 已解决：2026-03-23
