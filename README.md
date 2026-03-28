# code-review-claude

Senior-engineer-level code review for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

Reads your codebase, generates severity-scored findings across security, SOLID principles, architecture, and code smells -- each with a copy-pasteable fix prompt you can run directly in Claude Code. **Strictly read-only: never modifies your code.**

## Quick Start

```bash
git clone https://github.com/nishil/code-review-claude.git
cd code-review-claude
./install.sh
```

Then in any project:

```
/review audit .
```

## Available Commands

| Command | Description | Status |
|---------|-------------|--------|
| `/review audit <path>` | Full audit -- all categories, detailed findings, refactoring roadmap | Phase 1 |
| `/review solid <path>` | SOLID principles analysis | Phase 1 |
| `/review security <path>` | Security vulnerability detection | Phase 1 |
| `/review smells <path>` | Code smell detection | Phase 1 |
| `/review architecture <path>` | Architecture and dependency analysis | Phase 1 |
| `/review quick <path>` | Top 5 most impactful issues with fix prompts | Phase 1 |
| `/review health <path>` | Codebase vitals dashboard -- scores + file statistics | Phase 1 |
| `/review patterns <path>` | Design patterns analysis | Phase 2 |
| `/review performance <path>` | Performance audit | Phase 2 |
| `/review errors <path>` | Error handling audit | Phase 2 |
| `/review tests <path>` | Test quality audit | Phase 2 |
| `/review framework <path>` | Framework best practices | Phase 2 |
| `/review diff [branch]` | PR-style review of changed files | Phase 3 |
| `/review report` | Generate report from last audit | Phase 3 |

If no path is given, the current working directory is used.

## How It Works

The system uses an **orchestrator + sub-skill** architecture:

1. **Orchestrator** (`skills/review/SKILL.md`) -- Routes commands, detects your tech stack, loads config, and invokes specialized sub-skills.
2. **Sub-skills** -- Domain experts that each analyze one category:
   - `review-security` -- SQL injection, XSS, hardcoded secrets, auth issues
   - `review-solid` -- Single Responsibility, Open/Closed, Liskov, Interface Segregation, Dependency Inversion
   - `review-architecture` -- Coupling, layering violations, circular dependencies, god objects
   - `review-code-smells` -- Long methods, deep nesting, duplicate code, primitive obsession
3. **Reference guides** (`skills/review/references/`) -- Stack-specific best practices loaded based on auto-detected languages.
4. **Statistics script** (`skills/review/scripts/file_stats.py`) -- Deterministic codebase analysis (LOC, file counts, method counts) used by `/review health`.

Stack detection is automatic. The orchestrator scans for file extensions and project markers (e.g., `next.config.*`, `migrations/` directory) and loads the appropriate reference guides.

## Output Format

Every finding follows a consistent format:

```
### SEC-003 | Critical | `src/auth/login.php:22-35`

**Problem:** SQL query built with string concatenation using unsanitized user input.

**Evidence:**
> Line 25: `$query = "SELECT * FROM users WHERE email = '" . $_POST['email'] . "'";`

**Suggestion:** Use parameterized queries via PDO prepared statements.

**Fix prompt:**
> Refactor `src/auth/login.php` lines 22-35 to use PDO prepared statements
> instead of string concatenation for the SQL query.
```

Each finding includes: ID, severity, file location, problem description, evidence from the code, suggestion, and a fix prompt you can paste directly into Claude Code.

## Configuration

Create a `.review-config.json` in your project root to customize behavior:

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

All fields are optional. If the file is absent, defaults apply.

## Scoring

Each category is scored independently:

```
category_score = max(0, 100 - (critical * 25) - (major * 10) - (minor * 3))
```

Suggestions do not affect scores. The overall score is a weighted average of active categories:

| Category | Weight | Phase |
|----------|--------|-------|
| Security | 20% | 1 |
| SOLID | 15% | 1 |
| Architecture | 15% | 1 |
| Error Handling | 12% | 2 |
| Performance | 12% | 2 |
| Test Quality | 10% | 2 |
| Code Smells | 8% | 1 |
| Design Patterns | 4% | 2 |
| Framework | 4% | 2 |

In Phase 1, only active category weights are used (normalized to 100%).

| Score Range | Status |
|-------------|--------|
| 80-100 | Healthy |
| 60-79 | Needs Attention |
| 0-59 | Critical |

## Stack Support

Auto-detected languages and frameworks with dedicated reference guides:

- **Python** -- PEP standards, Django/Flask patterns, type hinting
- **JavaScript / TypeScript** -- ES modules, async patterns, type safety
- **React / Next.js** -- Component patterns, hooks, SSR/SSG
- **PHP / Laravel** -- Eloquent, service patterns, blade templates
- **SQL / Database** -- Query optimization, schema design, migrations
- **API Design** -- REST conventions, validation, error responses

Additional languages recognized for file statistics: Java, Ruby, Go, Rust, Vue, Svelte, Shell, CSS/SCSS, HTML.

## Claude.ai Support

When used on Claude.ai (without filesystem access), the skill runs in **degraded mode**: it analyzes pasted or uploaded code directly, skips codebase statistics and diff review, and notes the limitation. Findings and scoring still work normally.

## Phase Roadmap

**Phase 1 (current):** Core review engine with 4 sub-skills (security, SOLID, architecture, code smells), orchestrator routing, scoring, templates, and file statistics.

**Phase 2:** 5 additional sub-skills -- error handling, performance, test quality, design patterns, framework best practices.

**Phase 3:** Parallel agent execution, PDF report generation, CI integration, and diff-based reviews.

## License

MIT

## Author

Nishil
