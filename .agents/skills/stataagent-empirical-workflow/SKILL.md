---
name: stataagent-empirical-workflow
description: Load StataAgent's staged empirical analysis workflow and embedded product requirements. Use when a task depends on phase semantics, required artifacts, stage checkpoints, workflow state transitions, bounded retries, or deciding what each research stage must produce.
---

# StataAgent Empirical Workflow

Read `../../../docs/product/empirical-analysis-workflow.md`.

Use this skill when the task is about:

- what S1 to S5 mean
- which artifact a stage must produce
- when the workflow may advance or must stop
- how bounded retry is allowed
- where product requirements now live in the merged workflow document

Read adjacent documents only when the task crosses boundaries:

- Read `../../../docs/references/CSMAR_PYTHON.md` when workflow behavior depends on CSMAR interface limits.
- Read `../../../docs/engineering/agent-harness.md` when the question shifts from workflow semantics to engineering enforcement.

Do not duplicate workflow facts in this skill. Treat the product document as the single source of truth.
