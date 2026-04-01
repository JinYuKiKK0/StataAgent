# StataAgent Agent Harness 设计

## 目的

本文档是 StataAgent 的 agent harness 单一事实来源，定义用于约束 Agent 编码、架构边界和代码风格的机械化规则。目标不是微观规定实现细节，而是把项目不变量编码成 Agent 无法绕过的硬性 gate。

源码目录结构和稳定数据契约以 `ARCHITECTURE.md` 为准；研究阶段语义和工件检查点以 `docs/product/empirical-analysis-workflow.md` 为准；顶层包导入边界以 `.importlinter` 为准；本文件只保留治理入口、工具分工、taste invariants 和规则维护方式。

本文档吸收 `docs/references/Harness-engineering.md` 的两条核心经验：

- 仓库知识必须是系统记录，Agent 需要清晰、可导航的文档入口，而不是超长提示词。
- 文档本身不足以维持代码库质量；架构边界、数据契约和少量 taste invariants 必须通过 linter、结构测试和 CI 强制执行。

## 设计原则

- 强制不变量，而不是微观实现。只约束边界、依赖方向、可审计性和可靠性，不限定具体库内写法。
- 固定结构，局部自治。目录角色和允许依赖路径是硬规则；在允许边界内，Agent 可以自主实现。
- 让报错信息成为 Agent 的下一轮上下文。每条规则不仅指出违规，还要解释原因和修复方向。
- 本地与 CI 同标准。Agent 在本地看到的失败条件，必须与 CI 完全一致。
- 新坏味道先沉淀为文档规则，再升级为机械规则。治理资产通过 review 和故障反馈持续收紧。

## 机械治理边界

- `ARCHITECTURE.md` 定义固定源码目录结构和稳定数据契约；这里不再重复抄写。
- 顶层包导入边界由 `.importlinter` 机械执行，入口命令为 `uv run python -m tools.run_import_linter`。
- 边界对象建模、类型收紧和禁止裸对象扩散由 `pydantic`、`pyright` 和 `tools.harness` 共同执行。
- 本文档只描述治理系统如何工作，不再承担架构依赖的软约束职责。

## Taste Invariants

这些规则不是人类审美，而是用于降低 Agent 漫游和代码漂移：

- 边界模型命名只能使用受控后缀：`Request`、`Response`、`Spec`、`Plan`、`Result`、`Bundle`、`Decision`。
- 一个文件只承载一种角色；`types.py` 不得混入 provider 调用，`services/*` 不得输出 rich 或 console。
- Python 文件超过 350 行直接失败。
- 非接口层禁止 `print()`、`Console.print()`、`sys.exit()`。
- 日志必须结构化，要求事件名和关键字段，禁止长字符串拼接日志。
- 禁止 `except Exception: pass`、裸重试、静默 fallback。
- 禁止新增 `utils.py`、`helpers.py`、`common.py`、`misc.py`、`temp.py`。

## 强制工具栈

本地统一治理入口为：

```text
uv run python -m tools.run_quality_gates
```

其中 `tools.harness lint` 默认扫描 `src tests tools`，并默认排除：

- `**/__pycache__/**`
- `.venv/**`
- `tests/fixtures/harness/**`

内部由五类工具分工：

- `ruff`：基础静态规则、导入排序、禁用 `print` 等低成本检查。
- `pyright`：类型边界、`Any` 扩散、返回值和 Optional 处理。
- `import-linter`：顶层包导入边界和遗留 shim 依赖禁令的机械执行器。
- `pytest tests/architecture`：结构测试和工作流不变量测试。
- `tools/harness`：仓库特有的 AST 级硬规则，包括边界契约、日志、文件职责和禁用模式。

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
    ├── test_import_contracts.py
    ├── test_boundary_contracts.py
    ├── test_module_layout.py
    └── test_toolchain_files.py
```

## pre-commit 与 CI 规则

本地提交和 CI 必须执行同一套 gate，顺序如下：

1. `uv run python -m ruff check .`
2. `uv run python -m pyright`
3. `uv run python -m tools.run_import_linter`
4. `uv run pytest tests/architecture -q`
5. `uv run python -m tools.harness lint`

本地提交前推荐仅执行统一入口 `uv run python -m tools.run_quality_gates`；
该入口会按上述顺序串行执行全部 gate，并在出现失败时继续执行后续 gate，最后统一返回状态码。

CI 建议拆成五个 job：

- `static`
- `imports`
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
Why: top-level package imports are mechanically enforced by import-linter and this edge bypasses the configured boundary.
Fix: move the dependency behind an allowed workflow/service boundary or adjust the architecture before changing the contract.
```

## 当前核心规则

当前必须持续保持的核心规则：

- `SA1001` 禁止非法层级导入
- `SA1002` 禁止活跃目录依赖 legacy shim
- `SA1003` 禁止 `providers/` 之外接入外部 SDK
- `SA2001` 跨边界函数禁止返回裸 `dict`
- `SA2002` 跨边界函数禁止使用 `Any`
- `SA2003` `ResearchState` 禁止保存运行时对象
- `SA3001` 非接口层禁止 `print()`
- `SA3002` 非接口层禁止 `Console.print()`
- `SA3003` 非接口层禁止 `sys.exit()`
- `SA3004` 禁止 `except Exception: pass`
- `SA4001` 禁止万能文件名
- `SA4002` 文件长度超限直接失败

## 文档维护规则

- `ARCHITECTURE.md` 负责固定源码目录结构和文档边界；本文件不再承载迁移计划。
- 本文档是 StataAgent agent harness 规则的单一事实来源。
- 当 review、故障或回归暴露出新的共性坏味道时，先更新本文档，再决定是否升级为规则。
- 当规则已机械化后，应保证本文档、`tools/harness` 和 CI 配置同步。
