# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

A multi-package Python monorepo that ships three independent, installable packages:

1. **`agent_router`** — keyword-based task router that selects which AI agent definition to use for a given task, backed by `agent_router/agents.yaml`
2. **`second_brain`** — persistent JSON knowledge store with CLI for storing, searching, and retrieving knowledge items
3. **`hackingtool`** — all-in-one security research CLI with modules for recon, web analysis, crypto utilities, OSINT, and CTF tools (uses Python stdlib only — no external dependencies)

Agent definitions live in `agents/` (51 Markdown files across 9 categories). They are source-of-truth personality/prompt files read by `AgentPersonality`, not Python modules. The `protocols/` directory documents workflow rules enforced by `ProtocolEnforcer`.

## Commands

**Install (editable, with dev deps):**
```bash
pip install -e ".[dev]"
```

**Run all tests:**
```bash
python -m pytest tests/
```

**Run a single test file:**
```bash
python -m pytest tests/test_agent_router.py -v
```

**Run a single test:**
```bash
python -m pytest tests/test_agent_router.py::TestAgentSelectionLogic::test_frontend_task_routes_to_frontend_developer -v
```

**Run tests with coverage:**
```bash
python -m pytest tests/ --cov=agent_router --cov=second_brain --cov=hackingtool --cov-report=term-missing
```

**Run only the currently-passing subset** (many tests fail due to hardcoded macOS paths in `agents.yaml` — see Known Issues):
```bash
python -m pytest tests/test_second_brain.py tests/test_agent_router.py tests/test_coordination.py tests/hackingtool/ -v
```

**Quick routing sanity check:**
```bash
python batch_test_agents.py
```

**second-brain CLI:**
```bash
python -m second_brain add --title "Title" --content "..." --category engineering --tags tag1 tag2
python -m second_brain search "react performance"
python -m second_brain list --category engineering
python -m second_brain stats
```

**hackingtool CLI:**
```bash
python -m hackingtool whois example.com
python -m hackingtool scan example.com -p 80,443
python -m hackingtool headers https://example.com
python -m hackingtool hash-id <hash>
python -m hackingtool cipher caesar-brute "encrypted text"
python -m hackingtool encode smart "c29tZXRoaW5n"
```

## Architecture

### `agent_router` package

- **`config.py` (`AgentConfig`)** — singleton YAML loader. Reads `agents.yaml`, validates all agent entries, caches the config. Each agent entry requires `name`, `description`, `keywords`, `file_path`. The `file_path` fields currently contain hardcoded macOS absolute paths, which is the primary source of test failures on other machines.
- **`router.py` (`AgentRouter`)** — core routing logic. `select_agent(task)` tokenizes the task, scores every agent by keyword match weight (exact word boundary match = 2.0 pts + specificity bonus; partial = 1.0 pt; agent name match = 5.0 pt boost), applies a `MIN_CONFIDENCE_THRESHOLD = 2.0`, and falls back to the default agent (Senior Developer). `analyze_task()` additionally detects multi-agent patterns (full-stack, dashboard, deploy, etc.) and returns up to 5 agents.
- **`coordination.py` (`CoordinationPlanner`)** — generates structured multi-agent execution plans with sequences, handoff points, time estimates, and parallel-work groups.
- **`personality.py` (`AgentPersonality`)** — parses `##`-sectioned Markdown agent files into structured dicts (core mission, communication style, deliverables, workflow, critical rules). Caches loaded personalities in memory.
- **`protocols.py` (`ProtocolEnforcer`)** — stateful enforcer tracking per-task workflow state (requirements gathered, tests written/approved, reflection done, implementation complete, etc.). Exposes validators for logging standards, production code, git workflow, command placeholders, and TODO structure.
- **`errors.py`** — custom exceptions: `AgentConfigError`, `PersonalityLoadError`, `RoutingError`, `ValidationError`.

### `second_brain` package

- **`knowledge.py` (`KnowledgeItem`)** — dataclass for a single knowledge unit with `id` (UUID), `title`, `content`, `category`, `tags`, `metadata`, timestamps.
- **`memory.py` (`MemoryStore`)** — JSON-backed store at `~/.agency_second_brain/memories.json`. All writes are atomic (write-to-tmp then `os.replace`).
- **`retrieval.py` (`KnowledgeRetriever`)** — relevance-scored search over a `MemoryStore`. Scoring: title match = 3×, tag match = 2×, content match = 1×; normalised by query token count.
- **`cli.py`** — argparse CLI exposing `add`, `get`, `update`, `delete`, `search`, `list`, `related`, `tags`, `categories`, `stats`.

### `hackingtool` package

Modules are in `hackingtool/modules/`:
- `recon/` — WHOIS, DNS enumeration, TCP port scanner (threaded)
- `web/` — HTTP security header analyzer (grades A+–F), SSL/TLS certificate checker
- `crypto/` — hash identifier, hash generator (MD5/SHA family), encoder (base64, hex, URL, HTML, rot13, binary, XOR brute, smart-decode)
- `osint/` — IP/hostname geolocation via ipinfo.io (no API key required for basic use)
- `ctf/` — classic cipher tools (Caesar, Vigenère, Atbash, Morse, XOR brute), pattern/secret searcher

All modules use Python stdlib only; `requirements-hackingtool.txt` only lists pytest for testing.

### `agents/` directory

51 Markdown agent definition files organised by category: `design/`, `engineering/`, `marketing/`, `product/`, `project-management/`, `security/`, `spatial-computing/`, `specialized/`, `support/`, `testing/`. Each file has optional YAML frontmatter and `##`-headed sections parsed by `AgentPersonality`.

## Key Conventions

**`AgentConfig` is a singleton.** Tests must call `AgentConfig.clear_cache()` before each test to avoid cross-test contamination. The `tests/conftest.py` fixture does this automatically via `autouse=True`.

**Agent YAML `file_path` values are absolute.** They currently point to `/Users/gaganarora/Desktop/...`. When running on any other machine, `AgentConfig._validate_config` will raise `AgentConfigError` for every agent whose file doesn't exist. To test routing logic locally you must either update `agents.yaml` paths or mock the file existence check.

**`hackingtool` has zero runtime external dependencies.** Adding any `import` that requires a third-party package breaks the stdlib-only constraint.

**`second_brain` store path defaults to `~/.agency_second_brain/memories.json`.** Pass a custom path in tests to avoid touching the real user store.

**Routing confidence threshold is 2.0.** Any task scoring below this falls back to Senior Developer. When adding new agent keywords, prefer multi-word phrases (they get a `+0.5 × (word_count - 1)` specificity bonus) and exact-word matches over substring matches.

## Known Issues

- `agents.yaml` `file_path` entries are hardcoded to a macOS developer machine. Many tests in `test_agent_config.py`, `test_agent_personality.py`, `test_all_37_agents.py`, and `test_protocol_enforcement.py` fail on this repo because those paths don't exist. The routing tests that mock or skip file validation still pass.
- `ProtocolEnforcer.check_venv_setup()` hardcodes `/Users/gaganarora/Desktop/gagan_projects/venv` — always returns `ready: False` outside that machine.
