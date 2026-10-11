# 🤖 Development Workflow Protocol for Claude Code Agents

> **Comprehensive development workflow enforcement system** - Transform Claude Code agents into disciplined, professional developers who follow best practices automatically.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Repository](https://img.shields.io/badge/repo-agency--agents-blue)](https://github.com/gagan114662/agency_agents)

---

## 🎯 What Is This?

This repository contains a comprehensive **Development Workflow Protocol** that enforces professional development practices across all Claude Code engineering agents. It ensures that every agent follows best practices for requirements gathering, test-first development, git hygiene, and production-ready code delivery.

### What Makes This Special

- **🚫 No Shortcuts**: Agents MUST gather requirements before coding
- **✅ Test-First Always**: Tests written and approved before implementation
- **📋 11 Mandatory Rules**: Every rule enforced for every task
- **🔍 Bash Validation**: Independent verification of logic and calculations
- **🎯 Production-Ready**: Clean code with no TODOs, debug statements, or commented code
- **📝 Full Transparency**: TODO.md tracking for all tasks

---

## 🧩 Install as a Claude Code Plugin

`.claude-plugin/marketplace.json` publishes the agents as a Claude Code marketplace named `agency-agents`, one plugin per category: `design`, `engineering`, `marketing`, `product`, `project-management`, `security`, `spatial-computing`, `specialized`, `support`, `testing`.

```
/plugin marketplace add bvgtdavantage-del/agency_agents
/plugin install engineering@agency-agents
```

All ten from a shell:

```bash
claude plugin marketplace add bvgtdavantage-del/agency_agents
for c in design engineering marketing product project-management security spatial-computing specialized support testing; do
  claude plugin install "$c@agency-agents"
done
```

Installed agents are namespaced by plugin, e.g. `engineering:engineering-senior-developer` or `security:security-penetration-tester`. `tests/test_marketplace.py` fails if an agent file is added without a manifest entry or without `name`/`description` frontmatter.

---

## 📚 Repository Structure

```
agency_agents/
├── agents/                    # All agent definitions (51 agents)
│   ├── design/               # 6 design agents
│   ├── engineering/          # 7 engineering agents
│   ├── marketing/            # 8 marketing agents
│   ├── product/              # 3 product agents
│   ├── project-management/   # 5 PM agents
│   ├── spatial-computing/    # 6 XR/spatial agents
│   ├── specialized/          # 3 specialized agents
│   ├── support/              # 6 support agents
│   └── testing/              # 7 testing agents
├── protocols/                 # Protocol documentation (2,849 lines)
│   ├── REQUIREMENTS-GATHERING-PROTOCOL.md (463 lines)
│   ├── TEST-FIRST-DEVELOPMENT.md (352 lines)
│   ├── GIT-WORKFLOW-PROTOCOL.md (858 lines)
│   └── DEVELOPMENT-WORKFLOW-PROTOCOL.md (932 lines)
├── tests/                     # Test files and validation scripts
├── templates/                 # Project templates
├── TODO.md                    # Project tracking
├── README.md                  # This file
├── CONTRIBUTING.md            # Contribution guidelines
└── LICENSE                    # MIT License
```

### Protocol Documentation

**Location**: `protocols/` directory (also installed globally in `~/.claude/`)

1. **[protocols/DEVELOPMENT-WORKFLOW-PROTOCOL.md](protocols/DEVELOPMENT-WORKFLOW-PROTOCOL.md)** (932 lines)
   - Complete implementation of all 11 mandatory workflow rules
   - Bash validation scripts for each rule
   - Real-world examples and enforcement guidelines
   - Quick reference commands and checklists

2. **[protocols/REQUIREMENTS-GATHERING-PROTOCOL.md](protocols/REQUIREMENTS-GATHERING-PROTOCOL.md)** (463 lines)
   - 10 essential question categories
   - Systematic requirements gathering workflow
   - Project brief generation templates

3. **[protocols/TEST-FIRST-DEVELOPMENT.md](protocols/TEST-FIRST-DEVELOPMENT.md)** (352 lines)
   - Test-first examples for all major languages
   - Anti-patterns to avoid
   - Coverage requirements

4. **[protocols/GIT-WORKFLOW-PROTOCOL.md](protocols/GIT-WORKFLOW-PROTOCOL.md)** (858 lines)
   - 4 mandatory git checks before every commit
   - Remote push verification
   - File cleanup automation

5. **[TODO.md](TODO.md)** (Project tracking)
   - In Progress/Pending/Completed sections
   - Complete milestone tracking
   - Task completion history

---

## 🚀 The 11 Mandatory Workflow Rules

Every engineering agent now enforces these rules for EVERY task:

### Rule 1: Pre-Work Test Approval ✅
- **ALWAYS** get user approval on tests BEFORE writing any implementation code
- Tests must import from actual modules (no hardcoded values)
- Ensures mutual understanding of expected behavior

### Rule 2: Git Commit Checkpoint Protocol ✅
- Ask user before creating git commits
- Create commits at logical milestones
- Follow 4 mandatory git checks before every push

### Rule 3: Logging Standards Enforcement ✅
- Use INFO level for production logging
- DEBUG for development only
- NO print() or console.log() in production code

### Rule 4: Bash Test Validation for Math/Logic ✅
- Create bash validation scripts for calculations
- Independent verification of critical logic
- Test edge cases and error handling

### Rule 5: Code Organization Standards ✅
- No duplicate functions across codebase
- Proper file structure and organization
- Single responsibility principle

### Rule 6: Local Testing Before Deployment ✅
- Run ALL tests locally
- Verify 100% pass rate
- Check coverage meets minimum threshold (80%+)

### Rule 7: Production-Ready Code Standards ✅
- No commented-out code blocks
- No TODO/FIXME comments
- No debug statements or logging

### Rule 8: User Decision Points with Options ✅
- Present options at key decision points
- Include pros/cons for each option
- Get user approval before proceeding

### Rule 9: Copy-Paste Ready Commands ✅
- All commands must be executable as-is
- No placeholders like `<your-path>`
- Use actual values and paths

### Rule 10: Virtual Environment Management ✅
- Use shared virtual environment
- Path: `/Users/gagan/Desktop/gagan_projects/venv`
- Python 3.13.7 with proper dependency management

### Rule 11: TODO.md File Tracking ✅
- Maintain TODO.md in project root
- Track In Progress/Pending/Completed tasks
- Update before and after each task

---

## 📦 Related Protocols

This workflow protocol integrates with three prerequisite protocols:

1. **REQUIREMENTS-GATHERING-PROTOCOL.md** (prerequisite)
   - 10-question framework covering all aspects
   - Mandatory before any coding begins
   - Creates comprehensive project briefs

2. **GIT-WORKFLOW-PROTOCOL.md** (integrated)
   - 4 mandatory git checks before every commit/push
   - Remote push verification
   - File cleanup enforcement

3. **TEST-FIRST-DEVELOPMENT.md** (integrated)
   - TDD standards and best practices
   - Test structure guidelines
   - Language-specific examples

---

## 🤖 Updated Engineering Agents

All engineering agents in `~/.claude/agents/engineering/` have been updated with the 11-rule workflow checklist:

1. ✅ **engineering-senior-developer.md**
2. ✅ **engineering-frontend-developer.md**
3. ✅ **engineering-backend-architect.md**
4. ✅ **engineering-ai-engineer.md**

### What Changed

Each agent now includes:
- Complete 11-rule workflow checklist
- Quick reference for all mandatory rules
- Integration with Git Workflow Protocol
- TODO.md tracking requirements
- Virtual environment management instructions

---

## 📊 Implementation History

### Commit Timeline

#### [3b4e6fe](https://github.com/gagan114662/agency_agents/commit/3b4e6fe) - docs: Update TODO.md - mark all tasks as completed
**Date**: 2024-10-14

- All 11 tests written and verified
- Protocol documentation complete (2,251 lines)
- Engineering agents updated with workflow
- Git commit created and pushed to remote
- Remote push verified successfully

---

#### [5ac9144](https://github.com/gagan114662/agency_agents/commit/5ac9144) - feat: Add comprehensive Development Workflow Protocol with 11 mandatory rules
**Date**: 2024-10-14

**Major Features Added**:

1. **Development Workflow Protocol** (MANDATORY for all agents)
   - 11 mandatory workflow rules enforced for all tasks
   - Pre-work test approval requirement
   - Git commit checkpoint protocol
   - Logging standards (INFO only, no print/debug)
   - Bash validation for math/logic
   - Code organization standards (no duplicates)
   - Local testing requirements (100% pass rate)
   - Production-ready code standards (no TODOs/comments)
   - User decision points with options
   - Copy-paste ready commands (no placeholders)
   - Virtual environment management
   - TODO.md file tracking

2. **Complete Test Suite** (11 comprehensive tests)
   - tests/test_development_workflow.md (1,183 lines)
   - Bash validation scripts for each rule
   - Pass/fail criteria documented
   - Edge case coverage

3. **Project Tracking System**
   - TODO.md with In Progress/Pending/Completed sections
   - Complete project history and milestones
   - Task status tracking

4. **Infrastructure Setup**
   - Cloned aitutor project (https://github.com/vandanchopra/aitutor)
   - Cloned ipop project (https://github.com/gagan114662/ipop)
   - Created shared venv at /Users/gagan/Desktop/gagan_projects/venv
   - Python 3.13.7 with dependencies installed

5. **Engineering Agents Updated** (in ~/.claude/agents/)
   - engineering-senior-developer.md
   - engineering-frontend-developer.md
   - engineering-backend-architect.md
   - engineering-ai-engineer.md
   - All agents now enforce the 11-rule workflow protocol

**This protocol ensures**:
- Test-first development (tests approved before implementation)
- Professional git hygiene (4 mandatory checks)
- Clean production code (no debug/print statements)
- Proper code organization (no duplicates)
- User decision involvement (options with pros/cons)
- Copy-paste ready documentation (no placeholders)
- Consistent virtual environment setup
- Task tracking transparency

**Total Lines**: 2,251 lines of comprehensive protocol documentation

---

#### [247ab2b](https://github.com/gagan114662/agency_agents/commit/247ab2b) - feat: Add Git Workflow Protocol with 4 mandatory checks
**Date**: 2024-10-14

**Tests Written FIRST** (TDD):
- test_git_workflow.md with all 4 feature tests
- Comprehensive test scenarios and validation

**Features Implemented**:

1. **Verify Remote Push (Not Local)**
   - Check remote tracking
   - Verify remote branch exists
   - Confirm local/remote sync
   - Prevent "pushed to GitHub" lies

2. **Remove Unnecessary Files Before Commit**
   - node_modules, __pycache__, .env cleanup
   - Comprehensive .gitignore
   - Pre-commit file scanning
   - Build artifacts removal

3. **Ensure Requirements File Exists**
   - Language detection (Python, Node, PHP, Go, Rust)
   - Validate requirements file presence
   - Check file content validity
   - Import/dependency matching

4. **Validate Authentication Necessity**
   - Question protocol before auth implementation
   - Decision tree (8 questions)
   - Document auth decision in project brief
   - Prevent unnecessary auth complexity

**Updated Engineering Agents**:
- Senior Developer
- Frontend Developer
- Backend Architect
- AI Engineer

**Added Files**:
- GIT-WORKFLOW-PROTOCOL.md (complete protocol)
- tests/test_git_workflow.md (test suite)
- .gitignore (comprehensive)

This ensures proper git hygiene and prevents common mistakes.

---

#### [2164a54](https://github.com/gagan114662/agency_agents/commit/2164a54) - feat: Add comprehensive requirements gathering and test-first development
**Date**: 2024-10-14

**Major Features Added**:

1. **Requirements Gathering Protocol** (MANDATORY before coding)
   - 10 essential question categories
   - Systematic questioning workflow
   - Project brief generation
   - User confirmation checkpoint

2. **Test-First Development Standards**
   - Comprehensive testing guidelines
   - Language-specific examples (JS, Python, PHP, etc.)
   - No hardcoded values in tests
   - Import from actual implementations

3. **Project Brief Template System**
   - 16-section comprehensive template
   - Technical stack documentation
   - Data models and business logic
   - Security, testing, deployment specs

4. **Complete Test Suite**
   - Requirements gathering tests (10 scenarios)
   - Question protocol validation tests
   - Project brief template tests

5. **Updated Engineering Agents**
   - Senior Developer
   - Frontend Developer
   - Backend Architect
   - AI Engineer

**All agents now MUST**:
- Gather requirements FIRST (no premature coding)
- Write tests BEFORE implementation
- Create project briefs
- Get user confirmation

This ensures Claude Code has complete understanding before starting any project.

---

## 🎯 What This Achieves

Your Claude Code engineering agents will now **automatically**:

✅ Gather comprehensive requirements before any coding
✅ Write tests first and get approval before implementation
✅ Follow all 11 workflow rules without exceptions
✅ Ask for approval at key checkpoints
✅ Maintain clean, production-ready code
✅ Track all tasks transparently in TODO.md
✅ Use shared virtual environments correctly
✅ Provide copy-paste ready commands
✅ Present options with pros/cons at decision points
✅ Validate math/logic with bash scripts
✅ Ensure 100% test pass rate before deployment

### Before vs After

#### Before 😰
- Agents jump straight into coding without requirements
- No tests or tests written after implementation
- Debug statements left in production code
- Placeholders in documentation (`<your-path>`)
- Unclear what tasks remain
- Commits without user approval

#### After 😎
- Requirements gathered first, every time
- Tests written and approved before code
- Clean production code, zero debug statements
- All commands copy-paste ready
- Full task transparency in TODO.md
- User controls all commits

---

## 🚀 Quick Start

### 1. Update Your Agents

The engineering agents in `~/.claude/agents/engineering/` have already been updated with the workflow protocol. When you use any of these agents in Claude Code, they will automatically follow all 11 rules.

### 2. Use the Protocols

When starting a new project with Claude Code:

```bash
# 1. Agent will automatically gather requirements first
# 2. Agent will write tests and ask for approval
# 3. Agent will follow all 11 workflow rules
# 4. Agent will ask before creating git commits
```

### 3. Verify Compliance

Check that agents are following the protocol:

```bash
# Check TODO.md is being maintained
cat TODO.md

# Verify no print statements in production code
grep -r "print(" src/

# Verify tests exist
ls -la tests/

# Check git is clean
git status
```

---

## 📋 Protocol Compliance Checklist

Before completing ANY task, verify:

- [ ] **Rule 1**: Tests written and approved BEFORE implementation
- [ ] **Rule 2**: Git commit checkpoint asked and completed properly
- [ ] **Rule 3**: Logging standards followed (INFO level, no prints)
- [ ] **Rule 4**: Bash validation scripts created for math/logic
- [ ] **Rule 5**: Code organization checked (no duplicates, proper structure)
- [ ] **Rule 6**: All tests run locally and pass (100%)
- [ ] **Rule 7**: Production code clean (no TODOs, comments, debug)
- [ ] **Rule 8**: User consulted on all major decisions
- [ ] **Rule 9**: All commands are copy-paste ready (no placeholders)
- [ ] **Rule 10**: Virtual environment properly configured
- [ ] **Rule 11**: TODO.md updated with current status

---

## 📊 Stats

- 🎯 **4 Commits**: Complete development workflow implementation
- 📝 **2,251 Lines**: Comprehensive protocol documentation
- ✅ **11 Rules**: Mandatory workflow enforcement
- 🧪 **11 Tests**: Comprehensive test suite with bash validation
- 🤖 **4 Agents**: Updated engineering agents with workflow
- 📦 **3 Protocols**: Requirements, Git, Test-First, and Workflow
- 🐍 **Python 3.13.7**: Shared virtual environment setup
- 🔧 **2 Projects**: aitutor and ipop cloned and configured

---

## 🤝 Contributing

This is a personal development workflow repository. Feel free to fork and adapt to your own needs!

### To Adapt for Your Own Use

1. Fork this repository
2. Update virtual environment paths in Rule 10
3. Modify project-specific requirements
4. Customize agent behaviors as needed
5. Add your own validation scripts

---

## 📖 Usage Examples

### Example 1: Starting a New Feature

```bash
USER: "Add a shipping cost calculator to the app"

AGENT:
Step 1: Requirements Gathering (Rule 1 - Pre-requisite)
- What weight units? (lbs, kg, oz)
- How to calculate distance? (zip codes, GPS, manual?)
- Pricing tiers or flat rate?
[... 10+ questions covering all aspects]

Step 2: Write Tests First (Rule 1)
Creates tests/test_shipping_calculator.py
"I've written 15 tests for the shipping calculator. May I proceed with implementation?"

Step 3: Implementation (After Approval)
Implements feature to make tests pass

Step 4: Bash Validation (Rule 4)
Creates tests/validation/test_shipping_calc.sh
Validates calculations independently

Step 5: Update TODO.md (Rule 11)
Moves task to "Completed" section

Step 6: Git Commit (Rule 2)
"Feature complete. Would you like me to create a git commit?"
```

### Example 2: Code Review Check

The agent will automatically verify:

```bash
# No print statements
✅ grep -r "print(" src/  # Returns nothing

# No TODO comments
✅ grep -r "TODO" src/  # Returns nothing

# All tests pass
✅ pytest tests/ -v  # 100% pass rate

# Requirements file exists
✅ ls requirements.txt  # File exists

# TODO.md is updated
✅ cat TODO.md  # Shows current status
```

---

## 📜 License

MIT License - Use freely, commercially or personally.

---

## 🙏 Acknowledgments

Built with Claude Code using test-first development and following all 11 workflow rules.

Special thanks to the MathematricksTrader project for inspiring these workflow standards.

---

## 💬 Repository Information

- **Repository**: https://github.com/gagan114662/agency_agents
- **Latest Commit**: 3b4e6fe
- **Status**: All tasks completed ✅
- **Last Updated**: 2024-10-14

---

## 🚀 Get Started

1. **Clone** this repository for reference
   ```bash
   git clone https://github.com/gagan114662/agency_agents.git
   ```

2. **Review** the protocols
   - Read DEVELOPMENT-WORKFLOW-PROTOCOL.md
   - Understand the 11 mandatory rules
   - Check the test suite in tests/

3. **Use** with Claude Code
   - Your agents already have the workflow integrated
   - They will automatically follow all rules
   - No additional configuration needed

4. **Adapt** for your projects
   - Fork and modify for your needs
   - Update paths and project-specific settings
   - Add custom validation scripts

---

<div align="center">

**🤖 Development Workflow Protocol: Professional Development, Automatically Enforced 🤖**

[⭐ Star this repo](https://github.com/gagan114662/agency_agents) • [🍴 Fork it](https://github.com/gagan114662/agency_agents/fork) • [📖 Read the Docs](DEVELOPMENT-WORKFLOW-PROTOCOL.md)

Built with ❤️ and test-first development

</div>
