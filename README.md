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

### `/codeprobe health`

```
Code Health Report — Growth Engine

Overall Health: 55/100 🟡 Needs Attention

Category Scores:
    Architecture       █████████████████░░░  91/100  ✅ Healthy
    Security           ████████████░░░░░░░░  62/100  🟡 Needs Attention
    Framework          ████████████░░░░░░░░  60/100  🟡 Needs Attention
    Performance        ███████████░░░░░░░░░  58/100  🔴 Critical
    SOLID              ███████████░░░░░░░░░  55/100  🔴 Critical
    Design Patterns    ███████████░░░░░░░░░  55/100  🔴 Critical
    Code Smells        █████████░░░░░░░░░░░  46/100  🔴 Critical
    Test Quality       █████░░░░░░░░░░░░░░░  28/100  🔴 Critical
    Error Handling     ████░░░░░░░░░░░░░░░░  22/100  🔴 Critical

Codebase Stats:
    Files: 391        | Total LOC: 64,146
    Backend: 170 py (20,907 LOC)   | Frontend: 221 ts/tsx (43,239 LOC)
    Largest file: frontend/app/growth-engine/ads/page.tsx (1,979 LOC)
    Test files: 29 / 391 (7.4%)
    Comment ratio: 1.1%

Hot Spots (files needing most attention):
    1. frontend/app/growth-engine/ads/page.tsx  — 3 categories flagged (SOLID, Code Smells, Architecture)
    2. backend/app/routers/agents.py            — 3 categories flagged (SOLID, Architecture, Design Patterns)
    3. backend/app/services/dependency_resolver.py — 3 categories flagged (Error Handling, Performance, Patterns)
```

### `/codeprobe audit`

Each finding includes an ID, severity, file location, evidence, and a fix prompt you can run directly in Claude Code:

```
SEC-003 | Critical | src/auth/login.php:22-35

  Problem:  SQL query built with string concatenation using unsanitized user input.
  Evidence: Line 25: $query = "SELECT * FROM users WHERE email = '" . $_POST['email'] . "'";
  Fix:      Refactor src/auth/login.php lines 22-35 to use PDO prepared statements
            instead of string concatenation for the SQL query.
```

---

## Install

```bash
npx skills add nishilbhave/codeprobe-claude
```

The installer will prompt you to pick skills (select all 10 with `*`), target agents (Claude Code, Cursor, Windsurf, Codex, Cline, etc.), and scope (global or per-project). To skip prompts and install everything:

```bash
npx skills add nishilbhave/codeprobe-claude --all
```

**Optional:** Python 3.8+ enables `/codeprobe health` codebase statistics.

Then in any project:

```
/codeprobe audit .
```

To update:

```bash
npx skills update          # project scope (from inside a project)
npx skills update -g       # global scope
```

To uninstall:

```bash
# Remove every codeprobe skill in one shot:
npx skills remove codeprobe codeprobe-security codeprobe-solid \
  codeprobe-architecture codeprobe-error-handling codeprobe-performance \
  codeprobe-testing codeprobe-code-smells codeprobe-patterns codeprobe-framework

# Or remove an individual sub-skill:
npx skills remove codeprobe-security

# Or pick interactively from all installed skills:
npx skills remove
```

Add `-g` to target global installs, or `-a claude-code` to remove from a specific agent only.

> **Note:** `npx skills remove --all` exists but removes **every** skill on your machine from every repo, not just codeprobe's. Avoid it unless that's what you want.

---

## Commands

| Command | Description |
|---------|-------------|
| `/codeprobe audit <path>` | Full audit -- all 9 categories, detailed findings, refactoring roadmap |
| `/codeprobe health <path>` | Codebase vitals dashboard -- scores, file statistics, hot spots |
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
