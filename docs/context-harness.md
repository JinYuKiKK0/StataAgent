# Context Harness

## Purpose

This repository uses a context-harness model:

- `AGENTS.md` is the map, not the encyclopedia.
- `ARCHITECTURE.md` is the top-level technical source of truth.
- `docs/` holds durable knowledge that agents should progressively discover as needed.

The goal is to keep injected context small, stable, and navigable while still making deeper knowledge available on demand.

## Progressive Disclosure

Agents should traverse the knowledge base in layers:

1. Read `AGENTS.md` for workflow and navigation.
2. Read `claude-progress.md` for compact current session state.
3. Read `feature_list.json` for task ordering and pass criteria.
4. Read `ARCHITECTURE.md` for system boundaries and runtime responsibilities.
5. Read only the focused docs needed for the current task.

## Document Roles

- `AGENTS.md`: stable workflow, repository map, and entrypoint
- `ARCHITECTURE.md`: system shape, stack, state machine, interfaces, and boundaries
- `docs/`: stable domain knowledge too detailed for `AGENTS.md` but too durable for ephemeral notes
- `Requirements.md`: upstream product requirement baseline
- `CSMAR-PYTHON.md`: upstream vendor reference for SDK usage and limits

## Writing Rules

- Keep `AGENTS.md` short. Add links and boundaries, not essays.
- Keep architecture decisions centralized in `ARCHITECTURE.md`.
- Split durable knowledge by topic rather than growing another catch-all plan document.
- Prefer one source of truth per topic; cross-link instead of copying.
- Keep `claude-progress.md` compact. Do not append session-by-session narrative there; use git history for chronology.
- If a document stops matching the code or the active design, update or remove it promptly.

## When to Add a New Doc

Create a new document only if at least one of these is true:

- The knowledge is needed across multiple sessions.
- The topic has stable ownership and a clear boundary.
- Re-reading the same context repeatedly would otherwise bloat `AGENTS.md` or `ARCHITECTURE.md`.

Otherwise keep the information in task-local notes or progress logs.
