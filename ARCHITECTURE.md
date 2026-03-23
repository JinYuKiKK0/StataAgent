# StataAgent Architecture

## Purpose

StataAgent is a local Windows empirical-analysis agent. It turns a user research request into a structured research specification, fetches data only through CSMAR, standardizes and merges the data into one analysis-ready long table, generates parameterized Stata code, executes that code through `stata-executor-mcp`, and returns an auditable result bundle.

`AGENTS.md` is the map. This file is the top-level technical source of truth for system shape, technical stack, runtime boundaries, state transitions, and documentation ownership.

## System Boundaries

- Deployment model: local single-user Windows workstation
- Interaction surfaces: CLI and Python API
- Allowed data source: CSMAR only
- Statistical execution engine: local Stata via `stata-executor-mcp`
- Non-goals for v1: web UI, multi-user service mode, remote job queue, user-uploaded raw data

## Technical Stack

- Main runtime: `Python 3.12`
- Workflow orchestration: `langgraph`, `langchain-core`, `langchain-openai`
- Structured models and settings: `pydantic v2`, `pydantic-settings`
- Data processing: `pandas`, `numpy`, `pyarrow`, `pandera`
- Stata code generation: `jinja2`
- Local persistence: `sqlite3`, `parquet`, `.dta`
- CLI and terminal UX: `typer`, `rich`
- Logging and secrets: `structlog`, `python-keyring`
- CSMAR compatibility layer: dedicated `Python 3.6` bridge process with official `CSMAR-PYTHON`
- Stata execution integration: Python MCP client for `stata-executor-mcp`
- Test stack: `pytest`, `pytest-mock`, `pytest-cov`

## Runtime Topology

```text
User Request
  -> CLI / Python API
  -> LangGraph Orchestrator
     -> Requirement Parsing
     -> Variable Mapping
     -> CSMAR Query Planning
     -> CSMAR Bridge
     -> Data Standardization and Panel Merge
     -> Quality Gate
     -> Model Planning
     -> Stata Template Rendering
     -> stata-executor-mcp
     -> Result Judgment and Audit
  -> Research Bundle
```

## Runtime Layers

### Interface Layer

- Accepts `ResearchRequest` from CLI or Python.
- Validates minimum required inputs such as topic, empirical requirements, and scope hints.
- Creates a run id and workspace for each execution.

### Workflow Layer

- Uses LangGraph as the canonical state-machine runtime.
- Stores shared state in a typed `ResearchState`.
- Keeps every stage resumable, inspectable, and auditable.

### Research Specification Layer

- Converts mixed user input into `ResearchSpec`.
- Locks the roles of `Y`, `X`, controls, expected sign, target panel grain, candidate fixed effects, and safe retry boundaries.

### Variable Mapping Layer

- Resolves research variables to CSMAR tables and fields.
- Uses internal variable dictionaries first, then falls back to CSMAR metadata inspection.
- Emits `VariableBinding` records with source table, field, key grain, frequency, unit, and confidence.

### CSMAR Access Layer

- Runs behind a dedicated Python 3.6 bridge because the vendor SDK targets that environment.
- Accepts `CsmarFetchRequest` JSON and returns `CsmarFetchResult` JSON plus materialized data paths.
- Handles pagination, query fingerprinting, cooldown-aware caching, and raw artifact storage.

### Data Pipeline Layer

- Standardizes dates, ids, units, missing-value encodings, and column names.
- Merges all sources into one target analysis grain.
- Rejects unresolved many-to-many joins instead of silently expanding the panel.

### Quality Gate Layer

- Produces descriptive statistics and validation findings before regressions run.
- Enforces checks for duplicate keys, invalid ratios, impossible values, missingness thresholds, and extreme outliers.
- Applies bounded winsorization to continuous variables and records it in the audit trail.

### Modeling and Execution Layer

- Builds a `ModelPlan` first, then renders `.do` files from templates.
- Runs Stata through `stata-executor-mcp` after a preflight environment check.
- Collects logs, result tables, and exported artifacts under the run workspace.

### Judgment and Audit Layer

- Compares outputs with prior theoretical expectations.
- Allows only bounded auto-retries: fixed effects, standard errors, safe control pruning, and predefined sample filters.
- Produces a final `ResearchBundle` with artifacts, decisions, and retry history.

## Workflow State Flow

The canonical state machine is:

```text
requested
-> specified
-> mapped
-> fetched
-> standardized
-> validated
-> modeled
-> executed
-> judged
-> completed | failed
```

Each stage must emit a machine-readable artifact or decision record. No stage should depend on hidden prompt context as its only output.

## Core Data Contracts

- `ResearchRequest`: raw user problem statement plus structured hints
- `ResearchSpec`: normalized research design and analysis constraints
- `VariableBinding`: chosen CSMAR field binding with provenance and confidence
- `QueryPlan`: table, fields, filter condition, paging, and cache fingerprint
- `PanelDataset`: final analysis-grain long table with lineage and coverage metadata
- `StataRunPlan`: input dataset path, template parameters, regression steps, output expectations
- `ResearchBundle`: end-to-end result package containing spec, data artifacts, code artifacts, logs, tables, and final judgment

## Storage and Artifacts

- `sqlite3`: run metadata, audit trail, cache index, query fingerprints
- `parquet`: fetched raw tables, standardized tables, intermediate joins
- `.dta`: Stata-ready analysis table
- `.do` and log files: generated Stata programs and execution traces

## Documentation Boundaries

- Keep workflow instructions and repository navigation in `AGENTS.md`.
- Keep top-level architecture and stack decisions in `ARCHITECTURE.md`.
- Keep durable supporting knowledge in `docs/`.
- Do not rebuild a monolithic `PLAN.md`; split durable knowledge by topic and ownership.
