# StataAgent 本地单机版系统设计（含技术栈）

**Summary**

- 目标是构建一个运行在 Windows 本机的单用户 Agent：用户输入“选题 + 实证步骤要求”，系统自动完成变量定义、CSMAR 检索、数据清洗合并成长表、Stata 代码生成、通过 `stata-executor-mcp` 执行并回收结果。
- 主架构采用 `LangGraph` 状态化工作流，不采用单提示词大 Agent。原因是这条链路包含外部数据接口、跨粒度合并、质量门禁、有限自动重试和执行审计，必须可回放、可重试、可解释。
- v1 只做 `CLI + Python API`，不纳入 Web 前端、多用户、队列调度和远程服务化部署。

**Tech Stack**

- 主应用运行时：`Python 3.12`
  理由：兼容 `LangGraph`、`Pydantic v2`、现代测试栈和数据处理库，适合作为主控编排层。
- CSMAR 兼容层：独立 `Python 3.6` 虚拟环境 + 官方 `CSMAR-PYTHON`
  理由：本地文档明确指向 `Python 3.6.X`；不应为了兼容旧 SDK 把整套系统锁死在旧版本 Python。
- 工作流与 LLM 编排：`langgraph`、`langchain-core`、`langchain-openai`
  约束：模型接入采用 OpenAI-compatible 接口，供应商可替换，但状态机和结构化输出接口不变。
- 结构化类型与配置：`pydantic v2`、`pydantic-settings`
  用于定义 `ResearchRequest`、`ResearchSpec`、`VariableBinding`、`QueryPlan`、`ResearchBundle` 等核心类型。
- 数据处理：`pandas`、`numpy`、`pyarrow`、`pandera`
  其中 `pandas` 负责清洗与合并，`pyarrow/parquet` 负责本地缓存和中间产物，`pandera` 负责长表 schema 校验。
- 模板与代码生成：`jinja2`
  Stata `.do` 文件采用模板参数化生成，不允许核心回归骨架完全由 LLM 自由生成。
- 数据持久化：`PostgreSQL` + `parquet`
  `PostgreSQL` 保存任务元数据、查询指纹、缓存索引和审计记录；支持复杂的查询和并发控制；`parquet` 保存原始表、标准化表和最终长表；对 Stata 输出 `.dta`。
- CLI 与本地体验：`typer`、`rich`
  用于命令行入口、任务状态展示和错误输出。
- 凭据与日志：`python-keyring`、`structlog`
  CSMAR 账号默认写入 Windows Credential Manager；运行日志输出为结构化 JSONL。
- Stata 执行集成：Python `mcp` 客户端接入 `stata-executor-mcp`
  入口前必须做 preflight；当前环境里 Stata 可执行文件未解析成功，因此“执行器配置检查”是强制前置步骤。
- 测试栈：`pytest`、`pytest-mock`、`pytest-cov`
  回归代码生成、数据拼接、查询规划、结果判断均用 fixture/golden tests 覆盖。

**Key Design Changes**

- 系统拆成两层运行时：
  `main-app` 负责 LangGraph 编排、需求解析、变量映射、清洗合并、Stata 计划生成、结果判断。
  `csmar-bridge` 运行在 Python 3.6 环境，专门封装 CSMAR 调用。
- `csmar-bridge` 与主应用的固定接口为：
  主应用写入 `CsmarFetchRequest` JSON，bridge 返回 `CsmarFetchResult` JSON 和生成的 parquet/csv 路径。
  不通过内存直接共享对象，避免跨 Python 版本耦合。
- 工作流状态固定为：
  `requested -> specified -> mapped -> fetched -> standardized -> validated -> modeled -> executed -> judged -> completed/failed`
- 核心公共接口：
  `run_research(request: ResearchRequest) -> ResearchBundle`
  `plan_research(request: ResearchRequest) -> ResearchSpec`
  CLI 对应 `stata-agent run`、`stata-agent plan`、`stata-agent inspect-run`
- 关键类型保持显式：
  `ResearchRequest`、`ResearchSpec`、`VariableBinding`、`QueryPlan`、`PanelDataset`、`StataRunPlan`、`ResearchBundle`
- 有限自动重试上限默认 3 次，仅允许调整固定效应、稳健标准误、控制变量剔除和预定义样本过滤；禁止自动改核心 `X/Y` 语义。

**Test Plan**

- 需求解析：混合输入能稳定产出完整 `ResearchSpec`，缺失研究对象或时间范围时拒绝继续。
- 变量映射：词典命中优先；未命中时走 CSMAR 元数据候选排序；低置信度映射必须终止或请求确认。
- CSMAR 访问：分页、30 分钟重复查询保护、无权限表、空结果和桥接层异常都能正确处理。
- 长表构建：支持一对一合并和宏观变量向下附着；遇到 many-to-many 直接失败；主键重复和缺失率超阈值被拦截。
- Stata 生成与执行：给定 `ModelPlan` 能稳定生成 `.do` 文件；preflight 失败时立刻报错；成功执行时能收回日志和结果表。
- 端到端：固定 fixture 覆盖“输入请求 -> 变量定义 -> CSMAR 抽数 -> 长表 -> 基准回归 -> 结果判断 -> 审计记录”。

**Assumptions**

- 主系统默认选型为 `Python 3.12 + LangGraph + pandas + PostgreSQL + Parquet + Typer`。
- CSMAR 官方 SDK 继续按 `Python 3.6` 兼容层处理，除非后续验证其稳定支持更高版本 Python。
- 默认模型接入为 OpenAI-compatible API，但不把具体模型名称写死到业务接口。
- 默认不引入 `FastAPI`、消息队列、PostgreSQL、前端框架；这些只在从本地单机版演进为共享服务版时再纳入。
- `stata-executor-mcp` 已存在，但当前本地 Stata 路径未配置完成，因此执行链路在实施时必须先补齐环境检查与错误提示。
