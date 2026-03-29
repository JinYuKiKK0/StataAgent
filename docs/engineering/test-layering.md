# StataAgent 测试分层规范

## 目的

本文档是 StataAgent `tests/` 目录组织结构和测试编写规范的单一事实来源。它面向所有在该项目开发功能的 Agent，规定分包结构、文件命名、测试类型边界和通用测试约束。

## 分包结构

`tests/` 按**工作流演进阶段**分包。每个功能阶段对应一个子包，跨阶段共享的入口和编排逻辑单独成包。

```text
tests/
├── architecture/           # 不变量 结构测试、导入契约、模块布局（不随功能增减）
├── entrypoints/            # 接入层 CLI、Agent UI 入口、包暴露契约
├── core_workflow/          # 总编排层 ApplicationOrchestrator、Gateway 恢复路径
├── s1_feasibility/         # Phase 1节点内单元测试 需求解析 → 数据契约（S1-T2 ~ S1-T7）
├── s2_data_assembly/       # Phase 2节点内单元测试 CSMAR 下载、解压、清洗、面板拼接
├── s3_empirical_modeling/  # Phase 3节点内单元测试 Stata 代码生成、回归执行与解释
├── fixtures/               # 跨阶段共享的测试数据文件（CSV、JSON 样本）
└── conftest.py             # 顶层 pytest 配置，全局 fixture
```

### 分包规则

- **一个功能阶段一个包**。S1、S2、S3 各自独立。跨阶段的节点或服务按其所属的**第一个消费阶段**归类。
- `architecture/` 是唯一的"恒定包"，不随功能阶段增减而变化，只随工程约束演进。
- `entrypoints/` 和 `core_workflow/` 承载跨阶段横切面，不属于任何单一阶段。

## 文件命名规则

- 测试文件一律以 `test_` 开头，后接**被测组件的模块名**。
  - ✅ `test_t2_requirement_parser.py`
  - ✅ `test_phase1_orchestrator.py`
  - ❌ `test_s1_utils.py`（万能文件名）
  - ❌ `test_misc.py`
- 一个测试文件只覆盖一个被测组件（对应 `services/` 或 `workflow/stages/` 中的一个模块）。若需要联调多个组件，测试文件名应反映**上层编排者**（如 `test_phase1_orchestrator.py` 而不是 `test_s1_pipeline.py`）。

## 测试函数规范

- 每个测试函数包含一个清晰的 `"""` docstring，说明：
  1. 被测功能点（对应哪个 Task）
  2. 触发条件（什么输入/注入）
  3. 预期行为（不是"assert 通过"，而是业务语义）
- 一个测试函数只覆盖一个具体场景，禁止在同一函数内组合多个行为断言（一个函数多个 `assert` 可以，但必须属于同一逻辑路径）。
