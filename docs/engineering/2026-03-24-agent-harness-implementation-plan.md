# Agent Harness Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first hard-gated StataAgent harness stack so agent-generated code is constrained by package boundaries, typed contracts, architecture imports, and repository-specific lint rules.

**Architecture:** The rollout happens in four layers: first stabilize package layout and contracts, then enforce architecture via `import-linter` and `pyright`, then add custom AST-based harness rules, and finally wire the full gate into `pre-commit` and CI. The implementation keeps the codebase green at every step by introducing compatibility shims before removing old paths.

**Tech Stack:** Python 3.12, pytest, pyright, import-linter, ruff, pre-commit, GitHub Actions, AST-based custom linting

---

## File Structure Map

### Root Tooling Files

- Modify: `pyproject.toml`
- Create: `pyrightconfig.json`
- Create: `.importlinter`
- Create: `.pre-commit-config.yaml`
- Create: `.github/workflows/harness.yml`

### Package Layout Convergence

- Create: `src/stata_agent/interfaces/__init__.py`
- Create: `src/stata_agent/interfaces/cli.py`
- Create: `src/stata_agent/workflow/__init__.py`
- Create: `src/stata_agent/workflow/orchestrator.py`
- Create: `src/stata_agent/workflow/state.py`
- Create: `src/stata_agent/providers/__init__.py`
- Create: `src/stata_agent/providers/settings.py`
- Create: `src/stata_agent/providers/logging.py`
- Create: `src/stata_agent/providers/csmar.py`
- Create: `src/stata_agent/providers/stata.py`
- Create: `src/stata_agent/providers/storage.py`
- Modify: `src/stata_agent/__main__.py`
- Modify: `src/stata_agent/cli.py`
- Modify: `src/stata_agent/config.py`
- Modify: `src/stata_agent/logging.py`
- Modify: `src/stata_agent/application/orchestrator.py`
- Modify: `src/stata_agent/workflows/states.py`
- Modify: `src/stata_agent/adapters/csmar_bridge.py`
- Modify: `src/stata_agent/adapters/stata_executor.py`
- Modify: `src/stata_agent/adapters/storage.py`

### Domain Contracts

- Create: `src/stata_agent/domains/__init__.py`
- Create: `src/stata_agent/domains/request/__init__.py`
- Create: `src/stata_agent/domains/request/types.py`
- Create: `src/stata_agent/domains/spec/__init__.py`
- Create: `src/stata_agent/domains/spec/types.py`
- Create: `src/stata_agent/domains/mapping/__init__.py`
- Create: `src/stata_agent/domains/mapping/types.py`
- Create: `src/stata_agent/domains/fetch/__init__.py`
- Create: `src/stata_agent/domains/fetch/types.py`
- Create: `src/stata_agent/domains/panel/__init__.py`
- Create: `src/stata_agent/domains/panel/types.py`
- Create: `src/stata_agent/domains/quality/__init__.py`
- Create: `src/stata_agent/domains/quality/types.py`
- Create: `src/stata_agent/domains/modeling/__init__.py`
- Create: `src/stata_agent/domains/modeling/types.py`
- Create: `src/stata_agent/domains/execution/__init__.py`
- Create: `src/stata_agent/domains/execution/types.py`
- Create: `src/stata_agent/domains/judgement/__init__.py`
- Create: `src/stata_agent/domains/judgement/types.py`
- Modify: `src/stata_agent/domain/models.py`
- Modify: `src/stata_agent/services/requirement_parser.py`
- Modify: `src/stata_agent/services/variable_mapper.py`
- Modify: `src/stata_agent/services/model_planner.py`
- Modify: `src/stata_agent/services/result_judge.py`
- Modify: `src/stata_agent/workflow/state.py`

### Harness Engine

- Create: `tools/harness/__init__.py`
- Create: `tools/harness/__main__.py`
- Create: `tools/harness/diagnostics.py`
- Create: `tools/harness/rules_manifest.py`
- Create: `tools/harness/rule_boundaries.py`
- Create: `tools/harness/rule_logging.py`
- Create: `tools/harness/rule_taste.py`
- Create: `tests/architecture/test_toolchain_files.py`
- Create: `tests/architecture/test_module_layout.py`
- Create: `tests/architecture/test_import_contracts.py`
- Create: `tests/architecture/test_boundary_contracts.py`
- Create: `tests/architecture/test_harness_cli.py`
- Create: `tests/architecture/test_rule_boundaries.py`
- Create: `tests/architecture/test_rule_taste.py`
- Create: `tests/fixtures/harness/boundary_leaks/returns_dict.py`
- Create: `tests/fixtures/harness/boundary_leaks/returns_any.py`
- Create: `tests/fixtures/harness/taste_violations/prints_in_service.py`
- Create: `tests/fixtures/harness/taste_violations/except_pass.py`
- Create: `tests/fixtures/harness/taste_violations/utils.py`

### Documentation

- Modify: `docs/engineering/agent-harness.md`
- Modify: `claude-progress.md`

## Rollout Order

1. Tooling scaffolding and config files
2. Package layout convergence with compatibility shims
3. Contract extraction and side-effect boundary cleanup
4. Architecture enforcement via `import-linter` and structure tests
5. Type enforcement via `pyright`
6. Custom harness CLI and rule engine
7. Local and CI gate wiring

## Task 1: Bootstrap Tooling Config

**Files:**
- Modify: `pyproject.toml`
- Create: `pyrightconfig.json`
- Create: `.importlinter`
- Create: `.pre-commit-config.yaml`
- Create: `.github/workflows/harness.yml`
- Test: `tests/architecture/test_toolchain_files.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


def test_harness_tooling_files_exist() -> None:
    assert Path("pyrightconfig.json").exists()
    assert Path(".importlinter").exists()
    assert Path(".pre-commit-config.yaml").exists()
    assert Path(".github/workflows/harness.yml").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/architecture/test_toolchain_files.py -v`  
Expected: FAIL because the new governance files do not exist yet

- [ ] **Step 3: Write minimal implementation**

```toml
# pyproject.toml
[dependency-groups]
dev = [
  "pytest>=8.3,<9.0",
  "pyright>=1.1.0",
  "import-linter>=2.0",
  "ruff>=0.11.0",
  "pre-commit>=4.0.0",
]
```

```ini
; .importlinter
[importlinter]
root_package = stata_agent
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/architecture/test_toolchain_files.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml pyrightconfig.json .importlinter .pre-commit-config.yaml .github/workflows/harness.yml tests/architecture/test_toolchain_files.py
git commit -m "build: bootstrap harness tooling configs"
```

## Task 2: Create Target Package Layout With Compatibility Shims

**Files:**
- Create: `src/stata_agent/interfaces/__init__.py`
- Create: `src/stata_agent/interfaces/cli.py`
- Create: `src/stata_agent/workflow/__init__.py`
- Create: `src/stata_agent/workflow/orchestrator.py`
- Create: `src/stata_agent/workflow/state.py`
- Create: `src/stata_agent/providers/__init__.py`
- Create: `src/stata_agent/providers/settings.py`
- Create: `src/stata_agent/providers/logging.py`
- Create: `src/stata_agent/providers/csmar.py`
- Create: `src/stata_agent/providers/stata.py`
- Create: `src/stata_agent/providers/storage.py`
- Modify: `src/stata_agent/__main__.py`
- Modify: `src/stata_agent/cli.py`
- Modify: `src/stata_agent/config.py`
- Modify: `src/stata_agent/logging.py`
- Modify: `src/stata_agent/application/orchestrator.py`
- Modify: `src/stata_agent/workflows/states.py`
- Modify: `src/stata_agent/adapters/csmar_bridge.py`
- Modify: `src/stata_agent/adapters/stata_executor.py`
- Modify: `src/stata_agent/adapters/storage.py`
- Test: `tests/architecture/test_module_layout.py`
- Test: `tests/test_bootstrap.py`

- [ ] **Step 1: Write the failing test**

```python
def test_new_layout_modules_import() -> None:
    from stata_agent.interfaces.cli import app
    from stata_agent.providers.settings import get_settings
    from stata_agent.workflow.orchestrator import ApplicationOrchestrator
    from stata_agent.workflow.state import ResearchState

    assert app is not None
    assert get_settings is not None
    assert ApplicationOrchestrator is not None
    assert ResearchState is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/architecture/test_module_layout.py -v`  
Expected: FAIL with import errors for missing packages

- [ ] **Step 3: Write minimal implementation**

```python
# src/stata_agent/cli.py
from stata_agent.interfaces.cli import app, main

__all__ = ["app", "main"]
```

```python
# src/stata_agent/config.py
from stata_agent.providers.settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/architecture/test_module_layout.py tests/test_bootstrap.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/stata_agent/interfaces src/stata_agent/workflow src/stata_agent/providers src/stata_agent/cli.py src/stata_agent/config.py src/stata_agent/logging.py src/stata_agent/application/orchestrator.py src/stata_agent/workflows/states.py src/stata_agent/adapters tests/architecture/test_module_layout.py tests/test_bootstrap.py
git commit -m "refactor: introduce harness-aligned package layout"
```

## Task 3: Split Boundary Contracts By Domain

**Files:**
- Create: `src/stata_agent/domains/request/types.py`
- Create: `src/stata_agent/domains/spec/types.py`
- Create: `src/stata_agent/domains/mapping/types.py`
- Create: `src/stata_agent/domains/fetch/types.py`
- Create: `src/stata_agent/domains/panel/types.py`
- Create: `src/stata_agent/domains/quality/types.py`
- Create: `src/stata_agent/domains/modeling/types.py`
- Create: `src/stata_agent/domains/execution/types.py`
- Create: `src/stata_agent/domains/judgement/types.py`
- Modify: `src/stata_agent/domain/models.py`
- Modify: `src/stata_agent/services/requirement_parser.py`
- Modify: `src/stata_agent/services/variable_mapper.py`
- Modify: `src/stata_agent/services/model_planner.py`
- Modify: `src/stata_agent/services/result_judge.py`
- Modify: `src/stata_agent/workflow/state.py`
- Test: `tests/architecture/test_boundary_contracts.py`
- Test: `tests/test_bootstrap.py`

- [ ] **Step 1: Write the failing test**

```python
def test_research_state_uses_domain_contracts() -> None:
    from stata_agent.domains.request.types import ResearchRequest
    from stata_agent.domains.spec.types import ResearchSpec
    from stata_agent.workflow.state import ResearchState

    assert ResearchState.model_fields["request"].annotation is ResearchRequest
    assert ResearchState.model_fields["spec"].annotation == ResearchSpec | None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/architecture/test_boundary_contracts.py -v`  
Expected: FAIL because the new contract modules do not exist yet

- [ ] **Step 3: Write minimal implementation**

```python
# src/stata_agent/domains/request/types.py
from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    topic: str = Field(...)
    dependent_variable: str = Field(...)
```

```python
# src/stata_agent/domain/models.py
from stata_agent.domains.request.types import ResearchRequest
from stata_agent.domains.spec.types import ResearchSpec
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/architecture/test_boundary_contracts.py tests/test_bootstrap.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/stata_agent/domains src/stata_agent/domain/models.py src/stata_agent/services src/stata_agent/workflow/state.py tests/architecture/test_boundary_contracts.py tests/test_bootstrap.py
git commit -m "refactor: split domain boundary contracts"
```

## Task 4: Enforce Architecture Imports With Import Linter

**Files:**
- Modify: `.importlinter`
- Create: `tests/architecture/test_import_contracts.py`
- Modify: `src/stata_agent/interfaces/cli.py`
- Modify: `src/stata_agent/workflow/orchestrator.py`
- Modify: `src/stata_agent/providers/*.py`

- [ ] **Step 1: Write the failing test**

```python
import subprocess


def test_import_linter_contracts_pass() -> None:
    result = subprocess.run(["lint-imports"], check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/architecture/test_import_contracts.py -v`  
Expected: FAIL until `.importlinter` declares the contracts and the imports follow the new layout

- [ ] **Step 3: Write minimal implementation**

```ini
[importlinter:contract:top_level_layers]
name = StataAgent top-level package layering
type = layers
layers =
    stata_agent.interfaces
    stata_agent.workflow
    stata_agent.domains
    stata_agent.providers
```

```ini
[importlinter:contract:interfaces_forbid_providers]
name = Interfaces may not import providers
type = forbidden
source_modules = stata_agent.interfaces
forbidden_modules = stata_agent.providers
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run lint-imports`  
Expected: `Contracts: 100% kept`

Run: `pytest tests/architecture/test_import_contracts.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .importlinter src/stata_agent/interfaces src/stata_agent/workflow src/stata_agent/providers tests/architecture/test_import_contracts.py
git commit -m "build: enforce architecture imports with import-linter"
```

## Task 5: Enforce Typed Boundaries With Pyright

**Files:**
- Modify: `pyrightconfig.json`
- Modify: `pyproject.toml`
- Modify: `src/stata_agent/interfaces/cli.py`
- Modify: `src/stata_agent/providers/settings.py`
- Modify: `src/stata_agent/workflow/orchestrator.py`
- Modify: `src/stata_agent/workflow/state.py`
- Modify: `src/stata_agent/services/requirement_parser.py`
- Modify: `src/stata_agent/services/variable_mapper.py`
- Modify: `src/stata_agent/services/model_planner.py`
- Modify: `src/stata_agent/services/result_judge.py`
- Test: `tests/architecture/test_boundary_contracts.py`

- [ ] **Step 1: Write the failing test**

```json
{
  "typeCheckingMode": "strict",
  "include": ["src", "tests"],
  "reportUnknownParameterType": "error",
  "reportUnknownVariableType": "error",
  "reportUnknownMemberType": "error",
  "reportMissingTypeArgument": "error"
}
```

- [ ] **Step 2: Run type check to verify it fails**

Run: `uv run pyright`  
Expected: FAIL on missing annotations, implicit `Any`, and stale import paths

- [ ] **Step 3: Write minimal implementation**

```python
class RequirementParser:
    def parse(self, request: ResearchRequest) -> ResearchSpec:
        return ResearchSpec(
            topic=request.topic,
            dependent_variable=request.dependent_variable,
            independent_variables=request.independent_variables,
            controls=[],
            analysis_grain="unknown",
        )
```

```python
class SettingsError(RuntimeError):
    """Raised when runtime settings are invalid."""
```

- [ ] **Step 4: Run checks to verify they pass**

Run: `uv run pyright`  
Expected: `0 errors, 0 warnings`

Run: `pytest tests/architecture/test_boundary_contracts.py tests/test_bootstrap.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyrightconfig.json pyproject.toml src/stata_agent/interfaces/cli.py src/stata_agent/providers/settings.py src/stata_agent/workflow src/stata_agent/services tests/architecture/test_boundary_contracts.py tests/test_bootstrap.py
git commit -m "build: enforce typed harness boundaries with pyright"
```

## Task 6: Implement Harness CLI, Diagnostics, And Boundary Rules

**Files:**
- Create: `tools/harness/__init__.py`
- Create: `tools/harness/__main__.py`
- Create: `tools/harness/diagnostics.py`
- Create: `tools/harness/rules_manifest.py`
- Create: `tools/harness/rule_boundaries.py`
- Create: `tests/architecture/test_harness_cli.py`
- Create: `tests/architecture/test_rule_boundaries.py`
- Create: `tests/fixtures/harness/boundary_leaks/returns_dict.py`
- Create: `tests/fixtures/harness/boundary_leaks/returns_any.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_harness_cli_reports_boundary_violation(tmp_path) -> None:
    from tools.harness.__main__ import main

    exit_code = main(["tests/fixtures/harness/boundary_leaks/returns_dict.py"])
    assert exit_code == 1
```

```python
def test_boundary_rule_flags_dict_return() -> None:
    from tools.harness.rule_boundaries import check_file

    diagnostics = check_file("tests/fixtures/harness/boundary_leaks/returns_dict.py")
    assert diagnostics[0].code == "SA2001"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/architecture/test_harness_cli.py tests/architecture/test_rule_boundaries.py -v`  
Expected: FAIL because the harness package and rules do not exist yet

- [ ] **Step 3: Write minimal implementation**

```python
# tools/harness/diagnostics.py
from dataclasses import dataclass


@dataclass(slots=True)
class Diagnostic:
    code: str
    path: str
    message: str
    why: str
    fix: str
```

```python
# tools/harness/rule_boundaries.py
if returns_bare_dict(node):
    diagnostics.append(
        Diagnostic(
            code="SA2001",
            path=path,
            message="Boundary leak: function returns bare dict",
            why="Cross-layer outputs must use explicit contracts",
            fix="Return a contract model such as ResearchSpec or ParseResult",
        )
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/architecture/test_harness_cli.py tests/architecture/test_rule_boundaries.py -v`  
Expected: PASS

Run: `uv run python -m tools.harness lint tests/fixtures/harness/boundary_leaks/returns_dict.py`  
Expected: non-zero exit with `SA2001`

- [ ] **Step 5: Commit**

```bash
git add tools/harness tests/architecture/test_harness_cli.py tests/architecture/test_rule_boundaries.py tests/fixtures/harness/boundary_leaks
git commit -m "feat: add harness CLI and boundary rules"
```

## Task 7: Implement Logging And Taste Rules

**Files:**
- Create: `tools/harness/rule_logging.py`
- Create: `tools/harness/rule_taste.py`
- Modify: `tools/harness/rules_manifest.py`
- Create: `tests/architecture/test_rule_taste.py`
- Create: `tests/fixtures/harness/taste_violations/prints_in_service.py`
- Create: `tests/fixtures/harness/taste_violations/except_pass.py`
- Create: `tests/fixtures/harness/taste_violations/utils.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_taste_rule_flags_console_print_outside_interface() -> None:
    from tools.harness.rule_taste import check_file

    diagnostics = check_file("tests/fixtures/harness/taste_violations/prints_in_service.py")
    assert diagnostics[0].code == "SA3002"
```

```python
def test_taste_rule_flags_banned_filename() -> None:
    from tools.harness.rule_taste import check_path

    diagnostics = check_path("tests/fixtures/harness/taste_violations/utils.py")
    assert diagnostics[0].code == "SA4001"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/architecture/test_rule_taste.py -v`  
Expected: FAIL because the taste rules do not exist yet

- [ ] **Step 3: Write minimal implementation**

```python
BANNED_FILENAMES = {"utils.py", "helpers.py", "common.py", "misc.py", "temp.py"}

if filename in BANNED_FILENAMES:
    diagnostics.append(...)

if has_console_print_outside_interfaces(tree, path):
    diagnostics.append(...)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/architecture/test_rule_taste.py -v`  
Expected: PASS

Run: `uv run python -m tools.harness lint tests/fixtures/harness/taste_violations/prints_in_service.py`  
Expected: non-zero exit with `SA3002`

- [ ] **Step 5: Commit**

```bash
git add tools/harness/rule_logging.py tools/harness/rule_taste.py tools/harness/rules_manifest.py tests/architecture/test_rule_taste.py tests/fixtures/harness/taste_violations
git commit -m "feat: add harness logging and taste rules"
```

## Task 8: Wire Pre-Commit, CI, And Final Verification

**Files:**
- Modify: `.pre-commit-config.yaml`
- Modify: `.github/workflows/harness.yml`
- Modify: `docs/engineering/agent-harness.md`
- Modify: `claude-progress.md`

- [ ] **Step 1: Write the failing smoke check**

```python
import subprocess


def test_full_harness_stack_passes() -> None:
    commands = [
        ["uv", "run", "ruff", "check", "."],
        ["uv", "run", "pyright"],
        ["uv", "run", "lint-imports"],
        ["uv", "run", "pytest", "tests/architecture", "-q"],
    ]
    for command in commands:
        result = subprocess.run(command, check=False)
        assert result.returncode == 0
```

- [ ] **Step 2: Run the smoke check to verify it fails**

Run: `pytest tests/architecture/test_toolchain_files.py tests/architecture/test_import_contracts.py -v`  
Expected: FAIL until pre-commit hooks, workflow jobs, and all rules are wired together

- [ ] **Step 3: Write minimal implementation**

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: pyright
      name: pyright
      entry: uv run pyright
      language: system
    - id: import-linter
      name: import-linter
      entry: uv run lint-imports
      language: system
```

```yaml
# .github/workflows/harness.yml
jobs:
  static:
  imports:
  architecture:
  harness:
  tests:
```

- [ ] **Step 4: Run final verification**

Run: `uv run ruff check .`  
Expected: PASS

Run: `uv run pyright`  
Expected: `0 errors, 0 warnings`

Run: `uv run lint-imports`  
Expected: `Contracts: 100% kept`

Run: `uv run pytest tests/architecture -q`  
Expected: PASS

Run: `uv run pytest -q`  
Expected: PASS

Run: `uv run pre-commit run --all-files`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .pre-commit-config.yaml .github/workflows/harness.yml docs/engineering/agent-harness.md claude-progress.md
git commit -m "ci: wire full agent harness gate"
```

## Final Verification Matrix

- `uv run ruff check .`
- `uv run pyright`
- `uv run lint-imports`
- `uv run pytest tests/architecture -q`
- `uv run pytest -q`
- `uv run pre-commit run --all-files`

## Handoff Notes

- Keep the old module paths as re-export shims until every import has been migrated and the harness is green.
- Do not enable file-length checks before the package layout convergence is complete, or the existing flat modules will fail prematurely.
- Do not remove legacy shims in the same commit that introduces new directories; make import movement reviewable.
- If `pyright` and `import-linter` disagree about a boundary, treat `import-linter` as the source of truth for package direction and adjust annotations separately.
