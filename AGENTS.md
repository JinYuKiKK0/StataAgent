# AGENTS.md — StataAgent 工作流

## 会话开始

1. 运行 `git log --oneline -10` 并阅读 `claude-progress.md` 以了解当前状态。
2. 阅读 `feature_list.json`，选择最高优先级的未完成功能（遵循 governance 中的 `task_ordering`）。
3. 在编写任何代码前，宣布将要处理的功能。

## 开发期间

- **一次处理一个功能**。不要批量处理多个功能。
- 不要删除或编辑 `feature_list.json` 中的功能定义。只能修改 `status` 和 `passes` 字段。

## 会话结束

1. **自验证**：端到端测试功能。仅在确认功能正常后设置 `"passes": true`。
2. **Git 提交**：提交所有更改并附带描述性消息。
3. **更新进度**：更新 `claude-progress.md` 作为紧凑的交接文件。覆盖 `CURRENT CONTEXT`，仅在这些事实实质性变化时更新 `PROJECT STATUS`、`ARCHITECTURE DECISIONS` 或 `KNOWN ISSUES`。不要在其中保留逐会话的日志。

## 按需加载

- 产品阶段语义、工件检查点和需求约束：使用 `$stataagent-empirical-workflow`
- 工程约束、harness 规则和代码治理：使用 `$stataagent-engineering`
- CSMAR 接口限制和供应商行为：使用 `$stataagent-csmar-reference`

## 稳定入口

- `AGENTS.md`：会话工作流与 skill 入口
- `ARCHITECTURE.md`：固定源码目录结构、系统边界和稳定契约
- `feature_list.json`：分阶段待办事项与验证状态
- `claude-progress.md`：跨会话紧凑交接
