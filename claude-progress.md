# Compact cross-session handoff for the repository.
#
# Read this file at session start and keep it small.
# Do not append a session-by-session log here.
# Use git history for chronological change history.

## PROJECT STATUS

- Current Phase: FOUNDATION_DOCS
- Overall Progress: 0/5 stages complete
- Last Updated: 2026-03-23
- Blocking Issues: `feature_list.json` still has no concrete feature entries

## ARCHITECTURE DECISIONS

<!-- Append only when a durable decision changes future work. -->
<!-- Format: [date] DECISION: <description> | RATIONALE: <why> -->
- [2026-03-23] DECISION: Treat `AGENTS.md` as a short navigation map and keep durable knowledge in `ARCHITECTURE.md` plus `docs/`. | RATIONALE: Preserve context budget, enable progressive disclosure, and reduce documentation rot.
- [2026-03-23] DECISION: Retire root `PLAN.md` and split durable content by ownership into `ARCHITECTURE.md` and `docs/`. | RATIONALE: Avoid monolithic documentation and keep the knowledge base aligned with topic boundaries.
- [2026-03-23] DECISION: Keep `claude-progress.md` as a compact handoff file with no session log. | RATIONALE: Preserve cross-session memory while keeping recurring startup context small; rely on git for chronology.

## CURRENT CONTEXT

<!-- Overwrite this section each session. Keep it concise. -->

- Working On: Compact handoff model established; next likely work is defining concrete features
- Stage: Documentation maintenance
- Branch: main
- Key Files:
  - AGENTS.md — workflow instructions plus short repository map
  - claude-progress.md — compact handoff file for current state only
  - docs/context-harness.md — context harness rules
  - docs/README.md — docs entrypoint and source-of-truth index
- Open Questions:
  - `feature_list.json` stages still have empty feature arrays
  - implementation modules and package layout have not been created yet
  - local Stata executor path still needs environment validation before implementation
- Dependencies Installed: None
- Dev Server: N/A

## KNOWN ISSUES

<!-- Keep only active issues that matter across sessions. -->
<!-- Format: [date-opened] ISSUE: <description> | STATUS: open/resolved | RESOLVED: [date] -->
- [2026-03-23] ISSUE: `feature_list.json` contains stage shells only and no concrete feature entries. | STATUS: open
