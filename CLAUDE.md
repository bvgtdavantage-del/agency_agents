# CLAUDE.md — Agency Agents Codebase Guide

## Repository Overview

This repository is an **intelligent agent routing and tooling system** with three main components:

1. **`agent_router/`** — Routes tasks to the appropriate specialized agent via keyword scoring
2. **`second_brain/`** — Persistent JSON-backed knowledge store for cross-session agent memory
3. **`hackingtool/`** — CLI security research framework (WHOIS, DNS, port scanning, crypto, OSINT, CTF)

It also contains **`agents/`**, a library of 50+ Claude agent definition markdown files, and **`protocols/`**, mandatory development workflow documentation.

---

## Repository Structure

```
agency_agents/
├── agent_router/           # Task-to-agent routing engine
│   ├── router.py           # AgentRouter: select_agent(), analyze_task()
│   ├── config.py           # AgentConfig singleton, YAML loader/validator
│   ├── agents.yaml         # All agent definitions with keywords and metadata
│   ├── coordination.py     # Multi-agent coordination planning
│   ├── protocols.py        # Protocol enforcement stubs
│   └── errors.py           # RoutingError, AgentConfigError, ValidationError
│
├── second_brain/           # Persistent knowledge store
│   ├── knowledge.py        # KnowledgeItem dataclass (title, content, category, tags)
│   ├── memory.py           # MemoryStore: atomic JSON CRUD (saves to ~/.agency_second_brain/)
│   ├── retrieval.py        # KnowledgeRetriever: keyword search with relevance scoring
│   └── cli.py              # `second-brain` CLI entry point
│
├── hackingtool/            # Security research CLI (stdlib-only runtime)
│   ├── cli.py              # `hackingtool` entry point, all sub-commands
│   ├── core/               # banner.py, config.py (Config dataclass), utils.py
│   └── modules/
│       ├── recon/          # WhoisLookup, DNSEnumerator, PortScanner
│       ├── web/            # HeaderAnalyzer, SSLChecker
│       ├── crypto/         # HashIdentifier, HashGenerator, Encoder
│       ├── osint/          # IPLookup
│       └── ctf/            # CipherTools (caesar, vigenere, morse, xor), PatternSearch
│
├── agents/                 # Claude agent personality definition files (.md)
│   ├── design/             # 6 agents (UI Designer, UX Architect, UX Researcher, etc.)
│   ├── engineering/        # 7 agents (Senior Developer [default], Frontend, Backend, AI, etc.)
│   ├── marketing/          # 8 agents (Content Creator, Social Media, TikTok, Reddit, etc.)
│   ├── product/            # 3 agents (Sprint Prioritizer, Feedback Synthesizer, Trend Researcher)
│   ├── project-management/ # 5 agents
│   ├── security/           # 3 agents (CTF Specialist, OSINT Analyst, Penetration Tester)
│   ├── spatial-computing/  # 6 agents (visionOS, XR, macOS Metal, etc.)
│   ├── specialized/        # 3 agents (Agents Orchestrator, Second Brain Manager, LSP Engineer)
│   ├── support/            # 6 agents (Analytics, Finance, Legal, Infrastructure, etc.)
│   └── testing/            # 7 agents (Reality Checker, API Tester, Performance, etc.)
│
├── protocols/              # Mandatory workflow documentation
│   ├── DEVELOPMENT-WORKFLOW-PROTOCOL.md   # 11 mandatory rules (932 lines)
│   ├── REQUIREMENTS-GATHERING-PROTOCOL.md # Pre-coding questionnaire (463 lines)
│   ├── TEST-FIRST-DEVELOPMENT.md          # TDD standards (352 lines)
│   └── GIT-WORKFLOW-PROTOCOL.md           # Git hygiene (4 mandatory checks)
│
├── tests/                  # Pytest test suite
├── templates/              # project-brief-template.md
├── setup.py                # Package config (v0.3.0, Python >=3.8)
├── conftest.py             # Root: adds project root to sys.path
└── TODO.md                 # Task tracking (In Progress / Pending / Completed)
```

---

## Development Setup

```bash
# Install in editable mode (includes dev dependencies)
pip install -e ".[dev]"

# Runtime dependency only
pip install PyYAML>=6.0

# hackingtool has no runtime external dependencies (stdlib only)
# Install test dependencies for hackingtool
pip install -r requirements-hackingtool.txt
```

Python requirement: **>=3.8**. Shared venv convention: `/Users/gagan/Desktop/gagan_projects/venv` (original author path — adapt to your local path).

---

## Running Tests

```bash
# Full test suite with coverage
pytest tests/ -v --cov=agent_router --cov=second_brain --cov=hackingtool

# Run a specific test file
pytest tests/test_agent_router.py -v

# Run all 37-agent integration test
pytest tests/test_all_37_agents.py -v
```

Coverage minimum: **80%**. All tests must pass before any commit.

### Critical Test Isolation

`AgentConfig` is a **singleton**. Every test that exercises the router must clear the cache:

```python
# tests/conftest.py already handles this with autouse=True fixture
from agent_router.config import AgentConfig

@pytest.fixture(autouse=True)
def clear_singleton_cache():
    AgentConfig.clear_cache()
    yield
    AgentConfig.clear_cache()
```

When writing new tests for `agent_router`, rely on the autouse fixture in `tests/conftest.py` — do not call `clear_cache()` manually unless you're adding a new conftest outside `tests/`.

---

## Key Architectural Details

### Agent Router (`agent_router/`)

**Routing algorithm** (`router.py:AgentRouter.analyze_task`):
- Scores all agents by keyword matching against the task string
- Exact word boundary match: **+2.0 points** base, **+0.5 per extra word** in multi-word keyword
- Partial (substring) match: **+1.0 point**
- Agent name appears in task: **+5.0 points**
- Pattern boost for multi-agent tasks (full-stack, design+build, deploy): **+3.0 points**
- Minimum confidence threshold: **2.0** — tasks below this fall back to the default agent
- Multi-agent threshold: top agents within **60% of the highest score**, different categories triggers `is_multi_agent = True`

**Default agent**: `Senior Developer` (`is_default: true` in `agents.yaml`)

**AgentConfig singleton** (`config.py`): Loads `agents.yaml` once and caches it. Validates required fields (`name`, `description`, `keywords`, `file_path`) and that `file_path` exists on disk. Call `AgentConfig.clear_cache()` to reset between tests.

**Adding a new agent**: Add an entry to `agent_router/agents.yaml` under the appropriate category. Required fields: `name`, `description`, `keywords` (list), `file_path` (must exist), `category`, `is_default` (bool), `protocols`.

### Second Brain (`second_brain/`)

- Persistent store: `~/.agency_second_brain/memories.json` (overridable via `--store` flag)
- **Atomic writes**: writes to a `.tmp` file then `os.replace()` — never leaves a partially-written store
- `KnowledgeItem` fields: `id` (UUID), `title`, `content`, `category`, `tags`, `metadata`, `created_at`, `updated_at`
- Retrieval scoring: title match **3×**, tag match **2×**, content match **1×**, normalized by query length
- CLI entry point: `second-brain` (installed via `setup.py` console_scripts)

```bash
second-brain add --title "Title" --content "..." --category engineering --tags tag1 tag2
second-brain search "react performance"
second-brain list --category engineering
second-brain related <item-id>
second-brain stats
```

### HackingTool (`hackingtool/`)

- Entry point: `hackingtool` CLI
- **Zero runtime external dependencies** — uses Python stdlib only
- Sub-commands: `whois`, `dns`, `scan`, `headers`, `ssl`, `hash-id`, `hash-gen`, `encode`, `ip`, `cipher`, `pattern`
- Global flags: `--timeout`, `--threads`, `--verbose`, `--no-banner`
- `Config` dataclass (`core/config.py`): `timeout`, `verbose`, `max_threads`

---

## The 11 Mandatory Workflow Rules

All engineering agents enforce these rules. When implementing features, follow the same discipline:

1. **Pre-Work Test Approval** — write tests, get approval, then implement
2. **Git Commit Checkpoint** — ask user before committing; follow 4-check git protocol
3. **Logging Standards** — `logging.INFO` for production; no `print()` or `console.log()`
4. **Bash Validation** — create bash scripts to independently verify math/logic
5. **Code Organization** — no duplicate functions; single responsibility
6. **Local Testing** — run all tests locally, verify 100% pass before deployment
7. **Production-Ready Code** — no TODOs, no commented-out blocks, no debug statements
8. **User Decision Points** — present options with pros/cons; get approval before proceeding
9. **Copy-Paste Ready Commands** — no `<placeholder>` values; use real paths
10. **Virtual Environment** — use shared venv consistently
11. **TODO.md Tracking** — update `TODO.md` (In Progress / Pending / Completed) before and after tasks

---

## Git Workflow (4 Mandatory Checks)

Before every push:
1. Verify remote tracking is configured (`git remote -v`)
2. Remove unnecessary files (`__pycache__`, `.env`, `node_modules`)
3. Confirm requirements file exists and is valid
4. Validate authentication necessity before implementing auth

```bash
git status
git diff --staged
git push -u origin <branch-name>
```

---

## Code Conventions

- **No comments** unless the WHY is non-obvious (hidden constraint, bug workaround, subtle invariant)
- **No docstrings** beyond a single short line where needed
- **No error handling for impossible paths** — trust framework guarantees; validate only at system boundaries
- **No backwards-compat shims** — delete unused code cleanly
- Module-level `__all__` is not used; imports are explicit
- Test files mirror source structure: `tests/test_agent_router.py` ↔ `agent_router/router.py`

---

## Agent Definition Files (`agents/`)

Each `.md` file in `agents/` defines a Claude subagent personality with YAML frontmatter:

```yaml
---
name: agent-name
description: One-line description used for routing
color: blue
---
```

The body contains the agent's identity, mission, tools, workflow, and communication style. These files are the source of truth for agent behavior — `agents.yaml` references them via `file_path`.

The `agents.yaml` `file_path` values are currently absolute paths from the original author's machine (`/Users/gaganarora/...`). When deploying, either update these paths or make them relative to the project root. The `AgentConfig._validate_agent` method calls `os.path.exists(agent['file_path'])` and will raise `AgentConfigError` if the path doesn't exist.

**Workaround for local development**: Ensure `file_path` values in `agents.yaml` point to valid local paths, or update `_validate_agent` to skip the existence check in dev environments.

---

## Common Development Tasks

### Add a new hackingtool sub-command
1. Create a module in the appropriate `hackingtool/modules/<category>/` directory
2. Export it from the category's `__init__.py`
3. Add `cmd_<name>` function in `hackingtool/cli.py`
4. Register the subparser in `build_parser()`

### Add a new Second Brain category
No code changes needed — categories are free-form strings on `KnowledgeItem`. Just use the new string in `--category`.

### Extend the routing score
Edit `AgentRouter._calculate_agent_score` in `agent_router/router.py`. Keyword specificity bonuses and pattern detection live in `_detect_multi_agent_patterns`.

### Run only fast unit tests (skip integration)
```bash
pytest tests/ -v -k "not integration"
```

---

## What NOT to Do

- Do not add `print()` statements to production modules — use `logging`
- Do not hardcode values in tests — import from actual modules
- Do not commit `__pycache__/`, `.env`, or `*.pyc` files
- Do not skip the `AgentConfig.clear_cache()` in test fixtures — it causes cross-test contamination
- Do not update `agents.yaml` `file_path` values to non-existent paths without updating the validation logic
