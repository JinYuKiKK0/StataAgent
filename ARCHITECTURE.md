# StataAgent 架构

## 目的

StataAgent 是一个本地 Windows 实证分析代理。它将用户研究请求转化为结构化研究规范，仅通过 CSMAR 获取数据，将数据标准化并合并为一个可分析的长表，生成参数化的 Stata 代码，通过 `stata-executor-mcp` 执行代码，并返回可审计的结果包。

`AGENTS.md` 是导航地图。本文件是系统形态、技术栈、运行时边界、状态转换和文档所有权的顶层技术单一事实来源。

## 系统边界

- 部署模式：本地单用户 Windows 工作站
- 交互界面：CLI 和 Python API
- 允许的数据源：仅 CSMAR
- 统计执行引擎：通过 `stata-executor-mcp` 的本地 Stata
- v1 非目标：Web UI、多用户服务模式、远程作业队列、用户上传原始数据

## 技术栈

- 主运行时：`Python 3.12`
- 工作流编排：`langgraph`、`langchain-core`、`langchain-openai`
- 结构化模型和设置：`pydantic v2`、`pydantic-settings`
- 数据处理：`pandas`、`numpy`、`pyarrow`、`pandera`
- Stata 代码生成：`jinja2`
- 本地持久化：`sqlite3`、`parquet`、`.dta`
- CLI 和终端 UX：`typer`、`rich`
- 日志和密钥：`structlog`、`python-keyring`
- CSMAR 兼容层：专用的 `Python 3.6` 桥接进程，配合官方 `CSMAR-PYTHON`
- Stata 执行集成：用于 `stata-executor-mcp` 的 Python MCP 客户端
- 测试栈：`pytest`、`pytest-mock`、`pytest-cov`

## 运行时拓扑

```text
用户请求
  -> CLI / Python API
  -> LangGraph 编排器
     -> 需求解析
     -> 变量映射
     -> CSMAR 查询规划
     -> CSMAR 桥接
     -> 数据标准化和面板合并
     -> 质量检查点
     -> 模型规划
     -> Stata 模板渲染
     -> stata-executor-mcp
     -> 结果判断和审计
  -> 研究包
```

## 运行时层次

### 接口层

- 从 CLI 或 Python 接受 `ResearchRequest`。
- 验证最低必需输入，如主题、实证要求和范围提示。
- 为每次执行创建运行 ID 和工作区。

### 工作流层

- 使用 LangGraph 作为规范的状态机运行时。
- 在类型化的 `ResearchState` 中存储共享状态。
- 保持每个阶段可恢复、可检查和可审计。

### 研究规范层

- 将混合用户输入转换为 `ResearchSpec`。
- 锁定 `Y`、`X`、控制变量、预期符号、目标面板粒度、候选固定效应和安全重试边界的角色。

### 变量映射层

- 将研究变量解析为 CSMAR 表和字段。
- 首先使用内部变量字典，然后回退到 CSMAR 元数据检查。
- 输出包含源表、字段、键粒度、频率、单位和置信度的 `VariableBinding` 记录。

### CSMAR 访问层

- 在专用的 Python 3.6 桥接后运行，因为供应商 SDK 针对该环境。
- 接受 `CsmarFetchRequest` JSON 并返回 `CsmarFetchResult` JSON 以及物化数据路径。
- 处理分页、查询指纹识别、冷却感知缓存和原始工件存储。

### 数据管道层

- 标准化日期、ID、单位、缺失值编码和列名。
- 将所有源合并到一个目标分析粒度。
- 拒绝未解析的多对多连接，而不是静默扩展面板。

### 质量检查点层

- 在回归运行之前生成描述性统计和验证发现。
- 强制检查重复键、无效比率、不可能值、缺失阈值和极端异常值。
- 对连续变量应用有界的缩尾处理并将其记录在审计跟踪中。

### 建模和执行层

- 首先构建 `ModelPlan`，然后从模板渲染 `.do` 文件。
- 在预飞行环境检查后通过 `stata-executor-mcp` 运行 Stata。
- 在运行工作区下收集日志、结果表和导出的工件。

### 判断和审计层

- 将输出与先前的理论期望进行比较。
- 仅允许有界的自动重试：固定效应、标准误差、安全控制修剪和预定义的样本筛选器。
- 生成包含工件、决策和重试历史的最终 `ResearchBundle`。

## 工作流状态流程

规范的状态机是：

```text
requested
-> specified
-> mapped
-> fetched
-> standardized
-> validated
-> modeled
-> executed
-> judged
-> completed | failed
```

每个阶段必须输出机器可读的工件或决策记录。任何阶段都不应仅依赖隐藏的提示上下文作为输出。

## 核心数据契约

- `ResearchRequest`：原始用户问题陈述加上结构化提示
- `ResearchSpec`：规范化的研究设计和分析约束
- `VariableBinding`：包含来源和置信度的所选 CSMAR 字段绑定
- `QueryPlan`：表、字段、筛选条件、分页和缓存指纹
- `PanelDataset`：具有谱系和覆盖元数据的最终分析粒度长表
- `StataRunPlan`：输入数据集路径、模板参数、回归步骤、输出期望
- `ResearchBundle`：端到端结果包，包含规范、数据工件、代码工件、日志、表和最终判断

## 存储和工件

- `sqlite3`：运行元数据、审计跟踪、缓存索引、查询指纹
- `parquet`：获取的原始表、标准化表、中间连接
- `.dta`：Stata 就绪分析表
- `.do` 和日志文件：生成的 Stata 程序和执行跟踪

## 文档边界

- 将工作流指令和仓库导航保留在 `AGENTS.md` 中。
- 将顶层架构和栈决策保留在 `ARCHITECTURE.md` 中。
- 将持久的支持知识保留在 `docs/` 中。
- 不要重建单块 `PLAN.md`；按主题和所有权拆分持久知识。
