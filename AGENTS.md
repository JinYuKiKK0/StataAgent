# AGENTS.md — StataAgent Workflow

## Session Start

1. Run `git log --oneline -10` and read `claude-progress.md` to understand current state.
2. Read `feature_list.json`, pick the highest-priority incomplete feature (follow `task_ordering` in governance).
3. Announce which feature you will work on before writing any code.

## During Development

- Work on **one feature at a time**. Do not batch multiple features.
- Do not remove or edit feature definitions in `feature_list.json`. You may only change `status` and `passes` fields.

## Session End

1. **Self-verify**: Test the feature end-to-end. Only set `"passes": true` after confirming it works.
2. **Git commit**: Commit all changes with a descriptive message.
3. **Update progress**: Update `claude-progress.md` as a compact handoff file. Overwrite `CURRENT CONTEXT`, and only update `PROJECT STATUS`, `ARCHITECTURE DECISIONS`, or `KNOWN ISSUES` when those facts materially change. Do not keep a session-by-session log there.

## Repository Map

- `AGENTS.md`: session workflow and repository navigation entrypoint.
- `ARCHITECTURE.md`: top-level architecture, tech stack, runtime boundaries, and workflow state flow.
- `Requirements.md`: product requirements and the five-stage empirical-analysis flow.
- `feature_list.json`: staged backlog and verification state.
- `claude-progress.md`: compact cross-session handoff, architecture decisions, and current working context.
- `docs/README.md`: docs hub, reading order, and source-of-truth index.
- `docs/context-harness.md`: rules for using repository docs as the context harness.
- `docs/product/research-workflow.md`: stage semantics, required outputs, and failure gates.
- `docs/references/CSMAR_PYTHON.md`: vendor SDK reference material and usage constraints.

## Directory Structure

```text
.
├── AGENTS.md
├── ARCHITECTURE.md
├── Requirements.md
├── feature_list.json
├── claude-progress.md
└── docs/
    ├── README.md
    ├── context-harness.md
    ├── product/
    │   └── research-workflow.md
    └── references/
        └── CSMAR_PYTHON.md
```
