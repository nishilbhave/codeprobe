# CodeProbe

<p align="center">
  <img src="assets/banner.svg" alt="CodeProbe - Senior-Engineer Code Review for Claude Code" width="900"/>
</p>

<p align="center">
  <a href="#install"><img src="https://img.shields.io/badge/install-one--command-f97316?style=flat-square" alt="Install"/></a>
  <img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="License: MIT"/>
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey?style=flat-square" alt="Platform"/>
  <img src="https://img.shields.io/badge/agents-Claude%20Code%20%7C%20Cursor%20%7C%20Windsurf%20%7C%2045+-7c3aed?style=flat-square" alt="45+ Agents"/>
</p>

Senior-engineer code review as an [agent skill](https://skills.sh). Run `/codeprobe audit .` and get a full health report in seconds.

- **9 review categories** -- security, SOLID, architecture, error handling, performance, test quality, code smells, design patterns, framework best practices
- **Severity-scored findings** with file locations and copy-pasteable fix prompts
- **Auto-detects your stack** -- Python, TypeScript, React/Next.js, PHP/Laravel, SQL, and more
- **Strictly read-only** -- never modifies your code
- **Works with 45+ agents** -- Claude Code, Cursor, Codex, Windsurf, Cline, and more

---

## Sample Output

Every `/codeprobe audit` opens with a **health dashboard** (category scores, codebase stats, hot-spot files), then lists detailed P0–P3 findings with fix prompts, and saves the whole report to `./codeprobe-reports/<timestamp>.md`.

### Code Health Report — growth-engine

**Overall Health:** 58/100 [Critical]

**Category Scores**

| Category | Score | Bar | Status |
|---|---|---|---|
| Security | 72/100 | `██████████████░░░░░░` | Needs Attention |
| SOLID | 45/100 | `█████████░░░░░░░░░░░` | Critical |
| Architecture | 55/100 | `███████████░░░░░░░░░` | Critical |
| Error Handling | 38/100 | `████████░░░░░░░░░░░░` | Critical |
| Performance | 62/100 | `████████████░░░░░░░░` | Needs Attention |
| Test Quality | 48/100 | `██████████░░░░░░░░░░` | Critical |
| Code Smells | 65/100 | `█████████████░░░░░░░` | Needs Attention |
| Patterns | 78/100 | `████████████████░░░░` | Needs Attention |
| Framework | 86/100 | `█████████████████░░░` | Healthy |

**Codebase:** 391 files · 64,146 LOC · Python 3.11 / FastAPI + Next.js / PostgreSQL / Redis

**Hot spots:**

1. `services/order_processor.py` — 7 categories flagged (SOLID, Error Handling, Performance, Code Smells, Test Quality, Patterns, Architecture)
2. `api/routers/checkout.py` — 5 categories flagged (Security, SOLID, Error Handling, Performance, Test Quality)
3. `frontend/src/pages/dashboard.tsx` — 4 categories flagged (Architecture, Code Smells, Patterns, Test Quality)

**Executive Summary:** Systemic issues across four categories. The biggest blocker is **error handling (38)** — 14 swallowed exceptions in payment paths, no top-level `try/except` in any of the three async workers, and transaction boundaries leak across service calls. **SOLID (45)** is dominated by `OrderProcessor` as a 1,420-LOC god class handling pricing, inventory, fulfillment, and notifications. **Architecture (55)** has a bidirectional dependency between `services/` and `api/` that makes the checkout path near-impossible to test in isolation. Security (72) is mostly sound but string-concatenation SQL in `reports/query_builder.py:88` needs to be fixed before the next release.

**Critical (P0 — 3 findings):**

- **SEC-001** | `reports/query_builder.py:88` — SQL built with string concatenation against the unsanitized `filters` request param. Direct injection via `POST /reports`. **Fix:** parameterize with SQLAlchemy `text(...)` + bind params, or move the query to the ORM.
- **ERR-007** | `workers/payment_worker.py:42-139` — `process_refund` wraps the Stripe call in a bare `try/except Exception: pass`. Failed refunds are silently dropped from the retry queue. **Fix:** catch `stripe.error.StripeError` explicitly, enqueue the payload on a dead-letter queue, alert on `InvalidRequestError`.
- **ARCH-003** | `services/order_processor.py` ↔ `api/routers/checkout.py` — Bidirectional coupling: the service imports router types for validation while the router constructs service internals directly. Blocks both service-level unit tests and independent router evolution. **Fix:** introduce `checkout/schemas.py` as a dependency-free Pydantic layer both sides depend on.

```
--> Report saved to ./codeprobe-reports/2026-04-23-221047.md
```

---

## Install

```bash
npx skills add nishilbhave/codeprobe
```

Then run `/codeprobe audit .` in any project.

**Manage:** `npx skills update` • `npx skills remove`

**Optional:** Python 3.8+ enables codebase statistics in the `/codeprobe audit` dashboard.

**Reports are saved** to `./codeprobe-reports/<timestamp>.md` in your current directory. Add `codeprobe-reports/` to your `.gitignore` to keep them out of source control.

---

## Commands

| Command | Description |
|---------|-------------|
| `/codeprobe audit <path>` | Full audit -- health dashboard (scores, file statistics, hot spots) plus detailed findings with fix prompts |
| `/codeprobe quick <path>` | Top 5 most impactful issues with fix prompts |
| `/codeprobe security <path>` | Security vulnerability detection |
| `/codeprobe solid <path>` | SOLID principles analysis |
| `/codeprobe architecture <path>` | Architecture and dependency analysis |
| `/codeprobe performance <path>` | Performance audit |
| `/codeprobe errors <path>` | Error handling audit |
| `/codeprobe tests <path>` | Test quality audit |
| `/codeprobe smells <path>` | Code smell detection |
| `/codeprobe patterns <path>` | Design patterns analysis |
| `/codeprobe framework <path>` | Framework best practices |

If no path is given, the current working directory is used.

### Running on a specific path

The `<path>` argument works the same way for every command above. It can be a directory *or* a single file, and can be relative or absolute.

```bash
# Current directory (same as passing no path)
/codeprobe audit .

# A subdirectory
/codeprobe audit ./src/backend

# An absolute path
/codeprobe audit /Users/me/projects/myapp

# A single file
/codeprobe audit ./src/api/auth.ts

# Scope a single category to a subfolder
/codeprobe security ./src/api
/codeprobe solid    ./backend/services
/codeprobe quick    ./src/checkout
```

**Notes on paths:**

- Relative paths are resolved against the directory Claude Code was started in.
- Only files inside the given path are analyzed — everything else is ignored.
- The report is always saved to `./codeprobe-reports/<timestamp>.md` in your **current working directory**, regardless of which path you scanned. `cd` into the project first if you want the report to land there.

---

## How It Works

The system uses an **orchestrator + sub-skill** architecture:

1. **Orchestrator** (`skills/codeprobe/SKILL.md`) -- Routes commands, detects your tech stack, loads config, and invokes specialized sub-skills.
2. **Sub-skills** -- Domain experts that each analyze one category:
   - `codeprobe-security` -- SQL injection, XSS, hardcoded secrets, auth issues
   - `codeprobe-error-handling` -- Swallowed exceptions, missing try/catch, transaction safety
   - `codeprobe-solid` -- Single Responsibility, Open/Closed, Liskov, Interface Segregation, Dependency Inversion
   - `codeprobe-architecture` -- Coupling, layering violations, circular dependencies, god objects
   - `codeprobe-patterns` -- Design pattern opportunities and anti-patterns
   - `codeprobe-performance` -- N+1 queries, unbounded queries, algorithmic efficiency, caching
   - `codeprobe-code-smells` -- Long methods, deep nesting, duplicate code, primitive obsession
   - `codeprobe-testing` -- Missing tests, test smells, mock abuse, coverage gaps
   - `codeprobe-framework` -- Laravel, React/Next.js, Python/Django framework idiom violations
3. **Reference guides** (`skills/codeprobe/references/`) -- Stack-specific best practices loaded based on auto-detected languages.
4. **Scripts** (`skills/codeprobe/scripts/`) -- Deterministic analysis utilities:
   - `file_stats.py` -- LOC, file counts, method counts per file
   - `complexity_scorer.py` -- Cyclomatic complexity per function
   - `dependency_mapper.py` -- Import graph and circular dependency detection
   - `generate_report.py` -- Markdown report generation from audit findings

Stack detection is automatic. The orchestrator scans for file extensions and project markers (e.g., `next.config.*`, `migrations/` directory) and loads the appropriate reference guides.

---

## Scoring

Each category is scored independently:

```
crit_penalty  = min(50, critical_count * 15)
major_penalty = min(30, major_count * 6)
minor_penalty = min(10, minor_count * 2)

category_score = max(0, 100 - crit_penalty - major_penalty - minor_penalty)
```

Suggestions do not affect scores. The overall score is a weighted average of active categories:

| Category | Weight |
|----------|--------|
| Security | 20% |
| SOLID | 15% |
| Architecture | 15% |
| Error Handling | 12% |
| Performance | 12% |
| Test Quality | 10% |
| Code Smells | 8% |
| Design Patterns | 4% |
| Framework | 4% |

| Score Range | Status |
|-------------|--------|
| 80-100 | Healthy |
| 60-79 | Needs Attention |
| 0-59 | Critical |

---

## Configuration

Create a `.codeprobe-config.json` in your project root to customize behavior:

```json
{
  "severity_overrides": {
    "long_method_loc": 50,
    "large_class_loc": 500,
    "deep_nesting_max": 4,
    "max_constructor_deps": 6
  },
  "skip_categories": ["codeprobe-testing"],
  "skip_rules": ["SPEC-GEN-001"],
  "framework": "laravel",
  "extra_references": [],
  "report_format": "markdown"
}
```

All fields are optional. If the file is absent, defaults apply. If `skip_categories` is set, weights are normalized to 100%.

---

## Stack Support

Auto-detected languages and frameworks with dedicated reference guides:

- **Python** -- PEP standards, Django/Flask patterns, type hinting
- **JavaScript / TypeScript** -- ES modules, async patterns, type safety
- **React / Next.js** -- Component patterns, hooks, SSR/SSG
- **PHP / Laravel** -- Eloquent, service patterns, blade templates
- **SQL / Database** -- Query optimization, schema design, migrations
- **API Design** -- REST conventions, validation, error responses

Additional languages recognized for file statistics: Java, Ruby, Go, Rust, Vue, Svelte, Shell, CSS/SCSS, HTML.

---

## Claude.ai Support

When used on Claude.ai (without filesystem access), the skill runs in **degraded mode**: it analyzes pasted or uploaded code directly, skips codebase statistics and diff review, and notes the limitation. Findings and scoring still work normally.

## License

MIT

## Author

Nishil
