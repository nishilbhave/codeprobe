---
name: review-architecture
description: >
  Analyzes code architecture and structure — layer violations, circular dependencies,
  god objects, anemic domain models, missing boundaries, directory structure issues,
  and configuration problems. Generates severity-scored findings with fix prompts.
  Trigger phrases: "architecture review", "structure check", "layer analysis", "god class".
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# Architecture & Structure Analyzer

## READ-ONLY CONSTRAINT

**This sub-skill is strictly read-only. Never modify, write, edit, or delete any file in the user's codebase. Report findings only.**

---

## Domain Scope

This sub-skill detects architectural and structural issues across these categories:

1. **Layer Violations** — Business logic in controllers, presentation logic in models, database access in views
2. **Circular Dependencies** — Direct or transitive circular imports between modules
3. **God Objects** — Oversized files and classes that do too much
4. **Anemic Domain Model** — Entity classes with no behavior, all logic in service classes
5. **Missing Boundaries** — No clear module/domain separation, cross-feature coupling
6. **Directory Structure** — Framework convention violations, flat directory anti-patterns
7. **Config/Environment** — Hardcoded environment values, missing config abstraction

---

## What It Does NOT Flag

- **Small projects/scripts** with fewer than 5 files — flat structure is appropriate for small codebases and adding layers would be over-engineering.
- **Microservices** that intentionally have thin layers — a microservice with a single controller, single service, and single repository is fine by design.
- **Framework-standard monolith patterns** that are idiomatic — e.g., Laravel's default structure for small-to-medium apps, Rails convention-over-configuration patterns, Next.js app directory conventions.
- **Prototypes and proof-of-concept code** clearly marked as such.
- **Generated code directories** (e.g., `dist/`, `build/`, `.next/`, `__pycache__/`).

---

## Detection Instructions

### Layer Violations

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `ARCH` | Controllers containing business logic | Scan files in controller directories (`controllers/`, `Controllers/`, `routes/`, `api/`). Flag controllers that contain: database queries (SQL, ORM query builders beyond simple `find()`/`findById()`), complex conditionals with business rules (3+ branches), calculations, data transformations, or validation logic beyond simple field presence checks. Controllers should delegate to services/actions. | Major |
| `ARCH` | Models/entities containing presentation logic | Scan model/entity files. Flag models that contain: HTML generation, string formatting for display (e.g., `toHtml()`, `formatForDisplay()`), view-specific transformations, CSS class computation, or response formatting. Models should contain domain logic, not presentation. | Major |
| `ARCH` | Views/components calling database directly | Scan view files (`.blade.php`, `.vue`, `.jsx`/`.tsx` components, `.ejs`, `.pug`, Jinja templates). Flag views that contain: direct database queries, ORM calls, raw SQL, or repository method calls. Views should receive data from controllers/props, never fetch it themselves. | Critical |

### Circular Dependencies

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `ARCH` | Module A imports B, B imports A (direct or transitive) | Trace import/require/use statements across files. Build a dependency graph for modules/directories. Look for: (1) direct cycles — file A imports file B, file B imports file A, (2) transitive cycles — A imports B, B imports C, C imports A. Focus on module-level (directory-level) cycles which are more architecturally significant than file-level cycles within the same module. Report the specific import chain. | Major |

### God Objects

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `ARCH` | File exceeds 500 LOC | Count total lines in each source file (excluding blank lines and comments). Flag files exceeding 500 LOC. For files exceeding 1000 LOC, escalate to critical. | Major |
| `ARCH` | Class with 20+ methods | Count public, protected, and private methods in each class. Flag classes with 20+ methods. List the method groups to suggest how the class could be split. | Major |
| `ARCH` | Single file handling request-to-response lifecycle | Look for files that handle the full request lifecycle: receiving/parsing the request, validating input, executing business logic, performing persistence, formatting the response, and logging — all in one file or class. Flag when 4+ of these concerns are in a single file. | Major |

### Anemic Domain Model

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `ARCH` | Entity/model classes with only getters/setters, zero behavior | Scan model/entity classes. If a class has only property declarations, getters, setters, and constructor assignment — with no business logic methods (no validation, no calculations, no state transitions, no domain rules) — it is an anemic entity. | Minor |
| `ARCH` | All logic in "Service" classes operating on dumb data bags | Check if the codebase has a pattern where entity classes are pure data containers and all behavior (validation, calculation, state transitions) lives in separate `*Service` classes that manipulate the entity externally. Flag when this pattern is pervasive (3+ services operating on the same entity). | Minor |

### Missing Boundaries

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `ARCH` | No clear module/domain separation in medium+ projects | For projects with 20+ source files, check whether the code is organized into modules, domains, or bounded contexts. If all source files live in a single flat directory or are only separated by technical layer (controllers/, models/, services/) with no domain grouping, flag it. | Major |
| `ARCH` | Shared database tables accessed directly across unrelated features | Search for the same database table name, model, or entity being imported/queried from multiple unrelated modules or feature directories. If `users` table is accessed from `billing/`, `notifications/`, `reports/`, and `admin/` without going through a shared `user` module, flag it. | Major |
| `ARCH` | Cross-feature direct imports instead of events/interfaces | Check whether feature modules import directly from other feature modules' internal files. For example, `billing/InvoiceService` importing `shipping/ShippingCalculator` directly instead of through an interface or event system. Flag tight inter-feature coupling. | Minor |

### Directory Structure

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `ARCH` | Framework conventions violated | Check whether the project follows its framework's expected directory structure. Examples: business logic classes in a `Controllers/` directory, SQL queries in view templates, route definitions scattered across non-route files, test files mixed with source files without naming convention. | Minor |
| `ARCH` | No separation between layers for 20+ files | For projects with 20+ source files, check whether there is any directory-based separation between layers (controllers, services, models, views) or domains. If everything lives in one flat directory, flag it. | Major |

### Config/Environment

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `ARCH` | Hardcoded environment-specific values in source code | Search for hardcoded URLs (`http://localhost`, `https://api.example.com`), port numbers (`:3000`, `:8080`, `:5432`), hostnames, IP addresses, and file system paths in source code files (not config files). These should come from environment variables or config. | Major |
| `ARCH` | Missing environment abstraction | Check whether the project has an environment abstraction layer (`.env` file + config loader, environment variables, config service). If source files read `process.env.X` or `os.environ['X']` directly in 5+ places without a centralized config module, or if there is no `.env`/config layer at all, flag it. | Minor |

---

## Using `file_stats.py`

When available, run the file_stats.py script via Bash to get LOC, class count, and method count per file. The script is located in the `review` skill's `scripts/` directory (resolve relative to the skill installation, not the user's project):

```bash
python3 scripts/file_stats.py <target_path>
```

Note: The orchestrator typically runs this script and passes results. If invoked standalone, locate the script in the sibling `review/scripts/` directory.

Use this data to:
- Identify god objects (files > 500 LOC, classes with 20+ methods)
- Find the largest files in the project
- Get accurate LOC counts for the summary

If Python 3 or the `file_stats.py` script is unavailable, estimate from reading files directly using Read. Do not fail the analysis — proceed with manual counting.

---

## Reference Loading

If the project uses a specific framework or language, load the relevant reference file from `../review/references/{file}.md` using Read. Available references include:

- `php-laravel.md` for PHP/Laravel projects (directory conventions, service layer patterns)
- `javascript-typescript.md` for JS/TS projects (module patterns, barrel files)
- `python.md` for Python projects (package structure, Django/FastAPI conventions)
- `react-nextjs.md` for React/Next.js projects (app directory, component architecture)

If the reference file is unavailable, continue the analysis without it.

---

## Output Contract

Every finding MUST include ALL of the following fields:

```json
{
  "id": "ARCH-{NNN}",
  "severity": "critical|major|minor|suggestion",
  "location": { "file": "path/to/file.ext", "lines": "45-120" },
  "problem": "One sentence describing what's wrong",
  "evidence": "Concrete proof from the code — quote specific patterns, counts, names",
  "suggestion": "Human-readable recommendation",
  "fix_prompt": "Copy-pasteable prompt for Claude Code to apply the fix. Must reference specific file names, line ranges, method names, and the exact change to make.",
  "refactored_sketch": "// optional: minimal code showing the fix direction"
}
```

### ID Prefix

All findings use the `ARCH-` prefix, numbered sequentially: `ARCH-001`, `ARCH-002`, `ARCH-003`, etc.

### Rendered Finding Format

```
### {ID} | {Severity} | `{file}:{lines}`

**Problem:** {problem description}

**Evidence:**
> {quoted code patterns, LOC counts, import chains, method lists, directory structure observations}

**Suggestion:** {what to do to fix it}

**Fix prompt:**
> {copy-pasteable prompt for Claude Code}

**Refactored sketch:** (optional)
```

### Fix Prompt Examples

- "Move the pricing calculation logic from `OrderController@store` (lines 40-75) into a new `PricingService` class under `app/Services/`. The controller should inject `PricingService` and call `$this->pricingService->calculate($order)`. The controller should only handle request parsing, service delegation, and response formatting."
- "Break `UserManager` (850 LOC) into focused services: extract authentication methods (lines 50-200) into `UserAuthService`, profile management (lines 201-450) into `UserProfileService`, and notification methods (lines 451-700) into `UserNotificationService`. `UserManager` becomes a thin facade that delegates to these three services."
- "Resolve the circular dependency between `billing/InvoiceService` and `shipping/ShippingCalculator`: extract the shared interface `ShippingCostProvider` into a `shared/contracts/` directory. Have `ShippingCalculator` implement `ShippingCostProvider`, and have `InvoiceService` depend on the interface instead of the concrete class."
- "Replace the hardcoded URL `http://localhost:3000/api` at line 23 of `src/services/ApiClient.ts` with an environment variable: use `process.env.API_BASE_URL` loaded through the config module. Add `API_BASE_URL=http://localhost:3000/api` to `.env.example`."
- "Create a domain-based directory structure: move `UserController`, `UserService`, `UserRepository`, and `UserPolicy` into a `app/Domains/User/` directory. Repeat for `Order`, `Payment`, and `Notification` domains. Each domain directory should contain its own controllers, services, models, and policies."

---

## Execution Modes

This sub-skill supports three modes, set by the orchestrator:

### `full` Mode
Analyze the target path thoroughly. Map the project structure, trace import graphs, measure file sizes, and check all architectural categories. Produce detailed findings for every detected issue with all required fields (id, severity, location, problem, evidence, suggestion, fix_prompt). Include refactored_sketch for major and critical findings showing the target architecture. Run `file_stats.py` if available.

### `scan` Mode
Quick count of architectural issues by severity. Identify the worst offenders (largest files, most coupled modules). Skip the `evidence` and `fix_prompt` fields. Return:
- Count of issues per category (Layer Violations, Circular Dependencies, God Objects, Anemic Domain, Missing Boundaries, Directory Structure, Config/Environment)
- Count by severity (critical, major, minor, suggestion)
- Top 3 architecturally problematic files/modules with brief descriptions

### `score-only` Mode
Count issues by severity per category. Return only the summary counts — no individual findings, no evidence, no fix prompts. Output the summary object only.

---

## Summary Output

At the end of every execution (regardless of mode), provide a summary:

```json
{
  "skill": "review-architecture",
  "summary": { "critical": 0, "major": 0, "minor": 0, "suggestion": 0 }
}
```

Replace the zeros with actual counts from the analysis.
