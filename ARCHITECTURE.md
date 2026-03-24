# StataAgent 架构

## 目的

StataAgent 是一个本地 Windows 实证分析代理。它将用户研究请求转化为结构化研究规范，仅通过 CSMAR 获取数据，将数据标准化并合并为一个可分析的长表，生成参数化的 Stata 代码，通过 `stata-executor-mcp` 执行代码，并返回可审计的结果包。

`AGENTS.md` 是会话入口和导航地图。本文件只固定顶层系统边界、源码目录结构、分层职责和稳定契约，避免新上下文窗口中的 Agent 擅自迁移包结构或引入兼容 shim。更细的工作流状态、阶段工件和工程 gate 放在 `docs/` 中按需阅读。

## 系统边界

- 部署模式：本地单用户 Windows 工作站
- 交互界面：CLI 和 Python API
- 允许的数据源：仅 CSMAR
- 统计执行引擎：通过 `stata-executor-mcp` 的本地 Stata
- v1 非目标：Web UI、多用户服务模式、远程作业队列、用户上传原始数据

## 技术栈

- 运行时与编排：`Python 3.12`、`langgraph`、`langchain`、`langchain-community`
- 契约与配置：`pydantic v2`、`pydantic-settings`
- 数据与渲染：`pandas`、`numpy`、`pyarrow`、`pandera`、`jinja2`
- 交互与运维：`typer`、`rich`、`structlog`、`python-keyring`
- 外部集成：Tongyi `DashScope`、官方 `CSMAR-PYTHON`（经 Python 3.6 桥接）、`stata-executor-mcp`
- 测试与治理：`pytest`、`pyright`、`import-linter`、`ruff`、`pre-commit`

## 固定源码目录结构

以下结构是当前唯一允许的顶层源码布局。未先更新本文件前，不得新增平行顶层包、批量迁移 `.py` 模块，或通过 shim 维持“双结构并存”。

```text
src/stata_agent/
├── __main__.py
├── interfaces/   # CLI / Python API 入口与输出格式化
├── workflow/     # LangGraph 编排、ResearchState、状态推进
├── domains/      # 按研究域划分的边界契约与少量端口定义
│   ├── request/
│   ├── spec/
│   ├── mapping/
│   ├── fetch/
│   ├── panel/
│   ├── quality/
│   ├── modeling/
│   ├── execution/
│   └── judgement/
├── services/     # 当前业务逻辑的正式归属目录
├── providers/    # LLM、CSMAR、Stata、存储、日志、设置等外部集成
└── templates/    # 受版本控制的模板与执行资产
```

约束如下：

- `services/` 是当前纯业务逻辑的正式归属目录；不要在常规 feature 开发中把它迁到新的 `application/`、`adapters/`、`runtime/`、`use_cases/` 等平行根目录。
- `domains/` 负责稳定的跨阶段边界类型；新增研究域时优先在现有 `domains/` 下扩展，而不是发明新的顶层包。
- `providers/` 是唯一允许直接接触 SDK、文件系统持久化、模型后端和执行器客户端的目录。
- `templates/` 只保存模板和受控资产，不是通用 Python 代码落点。
- 顶层包导入边界由 `.importlinter` 和 `uv run python -m tools.run_import_linter` 机械执行，不在本文中重复维护软约束。

## 稳定数据契约

当前稳定数据契约定义如下：

- `ResearchRequest`
- `ResearchSpec`
- `VariableBinding`
- `QueryPlan`
- `PanelDataset`
- `QualityDecision`
- `StataRunPlan`
- `ResearchBundle`
- `ResearchState`
