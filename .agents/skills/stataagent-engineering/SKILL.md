---
name: stataagent-engineering
description: Load StataAgent's engineering governance and harness rules. Use when a task involves architecture enforcement, lint and test gates, repository knowledge governance, coding constraints, taste invariants, or deciding how agent-written code is mechanically constrained.
---

# StataAgent Engineering

Read `../../../docs/engineering/agent-harness.md`.

Read `../../../docs/engineering/test-layering.md` for test organization, file naming, and stub conventions.

Use this skill when the task is about:

- harness rules and rule ownership
- architecture and import boundary enforcement
- CI and pre-commit gates
- repository knowledge governance
- code-organization constraints for agent-authored changes
- test layering, file naming, and stub/fake conventions

Read adjacent documents only when needed:

- Read `../../../ARCHITECTURE.md` for fixed source layout and stable contracts.
- Read `../../../docs/references/Harness-engineering.md` only when the task needs the design rationale behind the harness approach.
- Read `../../../docs/product/empirical-analysis-workflow.md` only when a rule depends on stage semantics or workflow checkpoints.
