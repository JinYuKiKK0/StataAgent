# StataAgent Agent Harness 设计

## 目的

本文档是 StataAgent 的 agent harness 单一事实来源，定义用于约束 Agent 编码、架构演进和代码风格的机械化规则。目标不是微观规定实现细节，而是把项目不变量编码成 agent 无法绕过的硬性 gate。

本文档吸收 `docs/references/Harness-engineering.md` 的两条核心经验：

- 仓库知识必须是系统记录，Agent 需要清晰、可导航的文档入口，而不是超长提示词。
- 文档本身不足以维持代码库质量；架构边界、数据契约和少量 taste invariants 必须通过 linter、结构测试和 CI 强制执行。

## 设计原则

- 强制不变量，而不是微观实现。只约束边界、依赖方向、可审计性和可靠性，不限定具体库内写法。
- 固定结构，局部自治。目录角色和允许依赖路径是硬规则；在允许边界内，Agent 可以自主实现。
- 让报错信息成为 Agent 的下一轮上下文。每条规则不仅指出违规，还要解释原因和修复方向。
- 本地与 CI 同标准。Agent 在本地看到的失败条件，必须与 CI 完全一致。
- 新坏味道先沉淀为文档规则，再升级为机械规则。治理资产通过 review 和故障反馈持续收紧。

## 目标目录模型

```text
src/stata_agent/
├── interfaces/          # CLI / Python API / 用户输入输出
├── workflow/            # LangGraph 图、状态机、节点装配
├── domains/
│   ├── request/
│   │   ├── types.py
│   │   ├── ports.py
│   │   ├── service.py
│   │   └── runtime.py
│   ├── spec/
│   ├── mapping/
│   ├── fetch/
│   ├── panel/
│   ├── quality/
│   ├── modeling/
│   ├── execution/
│   └── judgement/
├── providers/           # CSMAR / Stata / storage / logging / settings / LLM
└── testing/             # 共享 fixture factory / harness helper
```

该结构的意义是为 Agent 提供稳定语义：

- `interfaces/` 只负责用户交互和展示。
- `workflow/` 只负责编排，不承载业务规则。
- `domains/*/types.py` 定义边界契约。
- `domains/*/service.py` 只承载纯业务逻辑。
- `domains/*/runtime.py` 负责装配 service、ports 和 providers。
- `providers/` 是唯一允许接触外部世界的层。

禁止再新增无语义目录和文件名，例如 `utils.py`、`helpers.py`、`common.py`、`misc.py`。

## 架构依赖规则

允许依赖方向如下：

```text
interfaces -> workflow -> domains/*/runtime -> domains/*/service -> domains/*/types
                                     |                    |
                                     v                    v
                                 providers <-------- domains/*/ports
```

硬规则如下：

- `types.py` 只能依赖标准库、`pydantic`、枚举和同域基础类型。
- `service.py` 不得访问文件系统、网络、数据库、CLI 输出、环境变量。
- `runtime.py` 可以装配 provider，但不得直接承担富文本输出和用户交互。
- `workflow/` 不得直接实现需求解析、变量映射、质量判断等业务规则。
- `interfaces/` 不得直接调用 `providers/`。
- 一个 domain 只能导入另一个 domain 的 `types.py`，不得导入对方的 `service.py` 或 `runtime.py`。
- `providers/` 之外不得直接接入第三方 SDK 或基础设施客户端。

## 边界数据契约规则

所有跨层输入输出都必须使用显式契约对象。主链路至少需要稳定的类型：

- `ResearchRequest`
- `ResearchSpec`
- `VariableBinding`
- `QueryPlan`
- `PanelDataset`
- `QualityDecision`
- `StataRunPlan`
- `ResearchBundle`
- `ResearchState`

硬规则如下：

- CLI / API 输入必须先进入输入模型，不能把命令行参数直接穿透到 workflow。
- 每个阶段必须输出显式契约对象，不允许以裸 `dict`、`Any`、`object` 作为主通道。
- provider 的 request / response 必须由本项目定义，不能泄露第三方 SDK 对象。
- `ResearchState` 只能保存跨阶段共享且可审计的字段，禁止塞入 logger、console、client、callback 等运行时对象。
- 工作流节点不得向状态中临时塞未声明字段。

必须拦截的反模式：

- `parse(...) -> dict`
- `state.extra["foo"] = ...`
- 裸 `pandas.DataFrame` 直接跨层传播
- `dict[str, Any]` 从 workflow 流到 domains 或 providers

## Taste Invariants

这些规则不是人类审美，而是用于降低 Agent 漫游和代码漂移：

- 边界模型命名只能使用受控后缀：`Request`、`Response`、`Spec`、`Plan`、`Result`、`Bundle`、`Decision`。
- 一个文件只承载一种角色；`types.py` 不得混入 provider 调用，`service.py` 不得输出 rich 或 console。
- 业务文件超过 250 行直接失败，测试文件超过 350 行直接失败。
- 业务函数超过 40 行直接失败。
- 非接口层禁止 `print()`、`Console.print()`、`sys.exit()`。
- 日志必须结构化，要求事件名和关键字段，禁止长字符串拼接日志。
- 禁止 `except Exception: pass`、裸重试、静默 fallback。
- 禁止新增 `utils.py`、`helpers.py`、`common.py`、`misc.py`、`temp.py`。

## 强制工具栈

治理入口统一为：

```text
uv run python -m tools.harness lint
```

内部由四类工具分工：

- `ruff`：基础静态规则、导入排序、禁用 `print` 等低成本检查。
- `mypy`：类型边界、`Any` 扩散、返回值和 Optional 处理。
- `pytest tests/architecture`：结构测试和工作流不变量测试。
- `tools/harness`：仓库特有的硬规则，包括层级依赖、边界契约、日志与文件职责。

建议治理目录：

```text
tools/
└── harness/
    ├── __main__.py
    ├── diagnostics.py
    ├── rules_manifest.py
    ├── rule_architecture.py
    ├── rule_boundaries.py
    ├── rule_logging.py
    ├── rule_taste.py
    └── rule_docs.py
tests/
└── architecture/
    ├── test_layer_dependencies.py
    ├── test_boundary_contracts.py
    └── test_workflow_invariants.py
```

## pre-commit 与 CI 规则

本地提交和 CI 必须执行同一套 gate，顺序如下：

1. `ruff check .`
2. `mypy src`
3. `pytest tests/architecture -q`
4. `uv run python -m tools.harness lint`

CI 建议拆成四个 job：

- `static`
- `architecture`
- `harness`
- `tests`

任一 job 失败都必须阻断合并，不允许 warning-only 模式。

## 规则编号与错误信息

所有自定义规则使用统一编号，便于 review 和迭代：

- `SA1xxx`：架构与依赖方向
- `SA2xxx`：边界契约与类型
- `SA3xxx`：日志与错误处理
- `SA4xxx`：文件组织与命名
- `SA5xxx`：工作流与阶段不变量
- `SA6xxx`：文档与知识库一致性

每条错误信息必须包含四段：

1. 规则编号
2. 发现了什么
3. 为什么违规
4. 应如何修复

示例：

```text
SA1001 Illegal dependency: interfaces -> providers
Found: src/stata_agent/interfaces/cli.py imports providers.storage
Why: interfaces may not access providers directly; all side effects must flow through workflow/runtime boundaries.
Fix: move this call into workflow runtime or expose an application service interface.
```

## 第一批必须上线的规则

第一期只上线最关键的 12 条规则：

- `SA1001` 禁止非法层级导入
- `SA1002` 禁止跨域导入对方 `service.py` 或 `runtime.py`
- `SA1003` 禁止 `providers/` 之外接入外部 SDK
- `SA2001` 跨边界函数禁止返回裸 `dict`
- `SA2002` 跨边界函数禁止使用 `Any`
- `SA2003` `ResearchState` 禁止保存运行时对象
- `SA3001` 非接口层禁止 `print()`
- `SA3002` 非接口层禁止 `Console.print()`
- `SA3003` 非接口层禁止 `sys.exit()`
- `SA3004` 禁止 `except Exception: pass`
- `SA4001` 禁止万能文件名
- `SA4002` 文件长度和函数长度超限直接失败

## 实施顺序

### 阶段 0：先做目录和职责收口

先把当前仓库收敛到目标目录语义，再打开硬性 gate。否则新规则会先阻断现有骨架。

### 阶段 1：上线最小可用 harness

新增 `tools/harness`、`tests/architecture`、`ruff`、`mypy`、`pre-commit`，先落第一批 12 条规则。

### 阶段 2：收紧工作流边界契约

把 `ResearchRequest` 到 `ResearchBundle` 的主链路类型完全定型，禁止隐式字段和裸对象。

### 阶段 3：补齐 taste invariants

在架构稳定后增加文件长度、函数长度、结构化日志和异常处理等规则。

### 阶段 4：建立治理升级闭环

治理规则按以下路径升级：

```text
review comment -> docs rule -> harness rule -> CI gate
```

同类问题重复出现两次后，应考虑升级为自定义规则。

## 与当前仓库的直接改造建议

当前仓库已经具备“文档系统作为系统记录”的基础，但仍缺少机械约束。优先改造点：

- 将 `src/stata_agent/services/` 拆分到 `domains/*/service.py`
- 将 `src/stata_agent/adapters/` 收敛到 `providers/`
- 将 `src/stata_agent/workflows/` 收敛到 `workflow/`
- 将 `src/stata_agent/domain/models.py` 按边界归属拆到各 domain 的 `types.py`
- 将 `src/stata_agent/config.py` 中的 console 输出和进程退出移回接口层
- 将 `src/stata_agent/logging.py` 收敛为结构化日志 provider

## 文档维护规则

- 本文档是 StataAgent agent harness 的单一事实来源。
- 当 review、故障或回归暴露出新的共性坏味道时，先更新本文档，再决定是否升级为规则。
- 当规则已机械化后，应保证本文档、`tools/harness` 和 CI 配置同步。
