# StataAgent Docs

The repository documentation is the system of record for agent context. `AGENTS.md` stays short and points here; deeper knowledge lives in focused documents with clear topic boundaries.

## Reading Order

1. `AGENTS.md`
2. `claude-progress.md`
3. `feature_list.json`
4. `ARCHITECTURE.md`
5. `docs/context-harness.md`
6. `docs/product/research-workflow.md`
7. `Requirements.md` or `docs/references/CSMAR_PYTHON.md` when the task touches product rules or vendor constraints

## Source of Truth

- Session workflow and repository map: `AGENTS.md`
- Architecture and tech stack: `ARCHITECTURE.md`
- Context harness conventions: `docs/context-harness.md`
- Research-stage semantics: `docs/product/research-workflow.md`
- Product requirement baseline: `Requirements.md`
- Vendor SDK constraints: `docs/references/CSMAR_PYTHON.md`
- Progress and open context: `claude-progress.md`

## Minimum Knowledge Base

This repository currently keeps the docs knowledge base intentionally small:

- `docs/README.md`
- `docs/context-harness.md`
- `docs/product/research-workflow.md`
- `docs/references/CSMAR_PYTHON.md`

Add a new document only when the knowledge is stable enough to outlive a single task or session.

## Retired Root Plan

`PLAN.md` is retired. Durable architecture content now lives in `ARCHITECTURE.md`, and domain workflow context lives under `docs/`.
