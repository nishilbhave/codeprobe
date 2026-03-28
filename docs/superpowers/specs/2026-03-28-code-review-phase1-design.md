# Code Review Skill System — Phase 1 Design

## Context

Automated linters catch syntax issues but miss architectural rot — SOLID violations, security anti-patterns, performance traps, and framework misuse. This skill system brings senior-engineer-level code review to Claude Code as a team of specialized sub-skills orchestrated by a central router.

This design covers **Phase 1 (MVP)** of the `code-review-claude` skill system: the orchestrator, 4 sub-skills, 6 reference files, 1 script, 2 templates, and install/uninstall scripts.

**Key decisions made:**
- Replaces the existing `code-review:code-review` plugin entirely
- Repo is self-contained — `install.sh` symlinks into `~/.claude/skills/`
- Follows the flat skill layout (blog/market pattern)
- All Phase 1 components built in parallel
- Strictly read-only — never modifies user code

---

## Repo Structure

```
code-review-claude/
├── skills/
│   ├── review/                        # Orchestrator (user-invokable)
│   │   ├── SKILL.md
│   │   ├── references/
│   │   │   ├── php-laravel.md
│   │   │   ├── javascript-typescript.md
│   │   │   ├── python.md
│   │   │   ├── react-nextjs.md
│   │   │   ├── sql-database.md
│   │   │   └── api-design.md
│   │   ├── templates/
│   │   │   ├── full-audit-report.md
│   │   │   └── quick-review-summary.md
│   │   └── scripts/
│   │       └── file_stats.py
│   │
│   ├── review-solid/
│   │   └── SKILL.md
│   ├── review-security/
│   │   └── SKILL.md
│   ├── review-code-smells/
│   │   └── SKILL.md
│   └── review-architecture/
│       └── SKILL.md
│
├── install.sh
├── uninstall.sh
├── requirements.txt
├── code-review-skill-specs.md         # Original spec (existing)
└── README.md
```

**Install path:** Each `skills/<name>/` symlinks to `~/.claude/skills/<name>/`. Claude Code discovers them as sibling skills.

---

## Orchestrator: `review/SKILL.md`

### Frontmatter

```yaml
---
name: review
description: >
  Code review and audit system with 9 specialized sub-skills covering SOLID
  principles, security, performance, architecture, error handling, testing,
  code smells, design patterns, and framework best practices. Generates
  severity-scored findings with copy-pasteable fix prompts.
  Use when user says "review", "audit", "code review", "check my code",
  "security scan", "code smells", "SOLID check".
user-invokable: true
argument-hint: "[audit|solid|security|smells|architecture|quick|health] <path>"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Agent
  - Task
metadata:
  author: Nishil
  version: "1.0.0"
---
```

### Responsibilities

1. **Parse command** — extract subcommand and target path from user input
2. **Auto-detect stack** — scan file extensions and imports at target path, determine which `references/*.md` to load
3. **Read config** — load `.review-config.json` from project root if present
4. **Route to sub-skills** — single-domain commands route directly; `audit` runs all sub-skills; `quick` does a lightweight pass
5. **Aggregate findings** — collect outputs from all invoked sub-skills, deduplicate, sort by severity
6. **Score** — apply weighted scoring formula (spec section 9)
7. **Render report** — use appropriate template

### Phase 1 Commands

| Command | Behavior | Sub-skills |
|---------|----------|------------|
| `/review audit <path>` | Full audit, sequential execution | All 4 sub-skills |
| `/review solid <path>` | SOLID principles only | `review-solid` |
| `/review security <path>` | Security audit only | `review-security` |
| `/review smells <path>` | Code smells only | `review-code-smells` |
| `/review architecture <path>` | Architecture analysis only | `review-architecture` |
| `/review quick <path>` | Top 5 issues — reads files, runs all sub-skills in scan mode (skip evidence/fix-prompt generation), ranks by severity, returns top 5 with full detail | All 4 sub-skills (scan mode) |
| `/review health <path>` | Codebase vitals dashboard | All sub-skills (scoring only) + `file_stats.py` |

### Stack Detection Logic

```
1. Glob for file extensions at target path
2. Map extensions to stacks:
   - .php → php-laravel (check for artisan/composer.json to confirm Laravel)
   - .js/.ts/.jsx/.tsx → javascript-typescript
   - .py → python (check for django/fastapi imports)
   - .jsx/.tsx + next.config.* → react-nextjs
   - .sql / migration files → sql-database
   - routes/ + controllers/ + API patterns → api-design
3. Load matching references/*.md files
4. Pass detected stack info to each sub-skill
```

### Severity Levels

| Level | Label | Meaning |
|-------|-------|---------|
| critical | Critical | Will cause bugs, security holes, or data loss in production |
| major | Major | Significant maintainability/scalability problem |
| minor | Minor | Code smell or sub-optimal pattern, low risk |
| suggestion | Suggestion | Improvement idea, not a problem |

### Scoring Formula

```
category_score = 100 - (critical * 25) - (major * 10) - (minor * 3)
overall_score = sum(category_score * weight)
```

Weights: Security 20%, SOLID 15%, Architecture 15%, Error Handling 12%, Performance 12%, Test Quality 10%, Code Smells 8%, Design Patterns 4%, Framework 4%.

Phase 1 categories (4 of 9) are scored with their weights. Missing categories don't penalize — overall score is normalized to the active weights.

### Config: `.review-config.json`

Read from project root if present. Optional — all defaults apply if absent.

```json
{
  "severity_overrides": {
    "long_method_loc": 50,
    "large_class_loc": 500,
    "deep_nesting_max": 4,
    "max_constructor_deps": 6
  },
  "skip_categories": ["review-testing"],
  "skip_rules": ["SPEC-GEN-001"],
  "framework": "laravel",
  "extra_references": [],
  "report_format": "markdown"
}
```

### Claude.ai Degraded Mode

Orchestrator detects Claude.ai environment (no filesystem paths, no subagent capability) and:
- Switches to sequential single-skill execution on in-context code
- Skips script-dependent analysis
- Informs user of unavailable features briefly

---

## Sub-Skill Pattern

All 4 Phase 1 sub-skills follow this structure.

### Frontmatter Template

```yaml
---
name: review-{domain}
description: "{What this sub-skill audits — one line}"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---
```

### Body Structure

Each SKILL.md contains:

1. **READ-ONLY constraint** — bold reminder at top
2. **Domain scope** — what this skill checks
3. **What it does NOT flag** — false positive suppression
4. **Detection instructions** — patterns/signals per sub-category, organized as tables
5. **Reference loading** — conditional: "If codebase uses {framework}, Read `../review/references/{ref}.md`"
6. **Output contract** — JSON finding structure with all required fields
7. **ID prefix** — unique per sub-skill

### Output Contract (All Sub-Skills)

Every finding must include:

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | `{PREFIX}-{NNN}` (e.g., `SRP-001`, `SEC-003`) |
| `severity` | Yes | `critical`, `major`, `minor`, or `suggestion` |
| `location` | Yes | File path + line range |
| `problem` | Yes | What's wrong — one sentence |
| `evidence` | Yes | Concrete proof from the code |
| `suggestion` | Yes | What to do about it |
| `fix_prompt` | Yes | Copy-pasteable prompt for Claude Code to apply the fix |
| `refactored_sketch` | No | Optional minimal code showing fix direction |

### Sub-Skill: `review-solid`

- **ID prefix:** `SRP-`, `OCP-`, `LSP-`, `ISP-`, `DIP-`
- **Checks:** Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
- **Key signals:** Class with 5+ unrelated public methods, switch/if-else chains on type, subclass overrides changing semantics, interfaces with 8+ methods, `new ConcreteClass()` in business logic
- **Does NOT flag:** Simple DTOs, small scripts, stable enum switches

### Sub-Skill: `review-security`

- **ID prefix:** `SEC-`
- **Checks:** OWASP Top 10 — Injection, Auth/AuthZ, XSS, Mass Assignment, CSRF, Insecure Deserialization, Sensitive Data Exposure, Broken Access Control, Misconfiguration
- **Key signals:** Raw SQL with user input, missing auth middleware, `dangerouslySetInnerHTML`, `$request->all()`, secrets in code, IDOR patterns
- **Does NOT flag:** Internal admin tools with IP restrictions, test file hardcoded values

### Sub-Skill: `review-code-smells`

- **ID prefix:** `SMELL-`
- **Checks:** Long Method, Large Class, Feature Envy, Data Clumps, Primitive Obsession, Shotgun Surgery, Dead Code, Magic Numbers, Boolean Blindness, Deep Nesting, Inappropriate Intimacy, Speculative Generality, Middle Man, Refused Bequest, Temporal Coupling
- **Thresholds (configurable):** Long Method > 30 LOC, Large Class > 300 LOC, Deep Nesting > 3 levels

### Sub-Skill: `review-architecture`

- **ID prefix:** `ARCH-`
- **Checks:** Layer Violations, Circular Dependencies, God Objects, Anemic Domain Model, Missing Boundaries, Directory Structure, Config/Environment
- **Key signals:** Business logic in controllers, models with presentation logic, files > 500 LOC, classes with 20+ methods, cross-feature direct imports
- **Uses:** `../review/scripts/file_stats.py` for LOC/complexity data when available

---

## Reference Files (All 6)

Each reference is a markdown file loaded on-demand when the orchestrator detects the relevant stack.

| File | Stack | Contents |
|------|-------|----------|
| `php-laravel.md` | PHP/Laravel | Eloquent patterns, service container, facades vs DI, PHP 8.x features, Laravel conventions |
| `javascript-typescript.md` | JS/TS | ES6+ patterns, TypeScript strict mode, async/await pitfalls, module systems |
| `python.md` | Python | PEP 8, Pythonic patterns, Django/FastAPI conventions, type hints |
| `react-nextjs.md` | React/Next.js | Component patterns, hooks rules, server components, rendering strategies |
| `sql-database.md` | SQL/DB | Query optimization, indexing strategy, migration patterns, N+1 detection |
| `api-design.md` | REST/GraphQL | Conventions, status codes, error format, versioning, rate limiting, pagination |

---

## Templates

### `full-audit-report.md`

Template for `/review audit` output. Sections:
- Project name, date, detected stack
- Overall score (0-100)
- Score breakdown table (per category)
- Critical issues (fix immediately)
- Major issues (fix this sprint)
- Minor issues (tech debt backlog)
- Suggestions
- Top 5 Quick Wins
- Refactoring Roadmap (ordered by dependencies)
- Fix Prompts section (numbered, copy-pasteable, sorted by severity)

### `quick-review-summary.md`

Template for `/review quick` output. Sections:
- Top 5 issues with severity, location, one-line problem, fix prompt
- Overall impression (1-2 sentences)
- "Run `/review audit` for full analysis"

---

## Scripts

### `file_stats.py`

- **Input:** Directory path as CLI argument
- **Output:** JSON to stdout
- **Fields per file:** `{file, loc, class_count, method_count, comment_ratio, blank_lines}`
- **Aggregate fields:** `{total_files, total_loc, avg_method_length, largest_file, test_file_count, test_file_ratio}`
- **Read-only:** Only reads source files, never writes
- **Dependencies:** Python 3.8+ standard library only (no pip deps for Phase 1)
- **Used by:** `/review health` command for codebase vitals dashboard

---

## Install / Uninstall

### `install.sh`

```bash
#!/bin/bash
# 1. Check ~/.claude/skills/ exists, create if not
# 2. For each dir in skills/: create symlink ~/.claude/skills/<name> -> <repo>/skills/<name>
# 3. Warn if existing skill found (prompt to overwrite)
# 4. Verify Python 3.8+ available for scripts
# 5. Print success message with available commands
```

### `uninstall.sh`

```bash
#!/bin/bash
# 1. For each dir in skills/: remove symlink ~/.claude/skills/<name>
# 2. Confirm removal
```

---

## Verification Plan

1. **Install test:** Run `install.sh`, verify all skills appear in Claude Code's `/review` list
2. **Quick review:** `/review quick <real-codebase-path>` — confirm top 5 findings with severity and fix prompts
3. **Single sub-skill:** `/review security <path-with-known-issues>` — verify detection accuracy, finding format, fix prompt quality
4. **Full audit:** `/review audit <small-project>` — all 4 sub-skills produce output, report renders with scores
5. **Health dashboard:** `/review health <path>` — file_stats.py runs, dashboard renders with stats
6. **Config overrides:** Create `.review-config.json` with `skip_categories` and threshold overrides, verify they apply
7. **Degraded mode:** Paste code in Claude.ai (no filesystem), confirm sub-skills work on in-context code
8. **Edge cases:** Empty directory, single file, binary files, very large files (>1000 LOC)
