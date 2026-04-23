---
name: codeprobe
description: >
  Code review and audit system with specialized sub-skills covering SOLID
  principles, security, performance, architecture, error handling, testing,
  code smells, design patterns, and framework best practices. Generates
  severity-scored findings with copy-pasteable fix prompts. Strictly read-only — never modifies user code.
  Use when user says "review", "audit", "code review", "check my code",
  "security scan", "code smells", "SOLID check".
user-invokable: true
argument-hint: "[audit|solid|security|smells|architecture|patterns|performance|errors|tests|framework|quick] <path>"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Agent
  - Write
metadata:
  author: Nishil
  version: "2.0.0"
---

# Code Review Orchestrator

## READ-ONLY CONSTRAINT

**THIS SKILL IS STRICTLY READ-ONLY WITH RESPECT TO THE CODEBASE BEING REVIEWED.** NEVER modify, write, edit, or delete any file in the user's source tree. NEVER run commands with side effects on the reviewed project (no `npm install`, no `pip install`, no git commits, no database mutations). If a fix is needed, generate a copy-pasteable fix prompt that the user can run separately.

**One documented exception — report artifact:** after `/codeprobe audit` finishes, the orchestrator writes a single markdown report to `./codeprobe-reports/<timestamp>.md` in the current working directory. This is the skill's own output, not modification of reviewed code. No other writes are permitted anywhere.

Violations of this constraint are NEVER acceptable, regardless of user request.

---

## 1. Command Routing

Parse the user's input to extract a subcommand and target path. The input format is:

```
/codeprobe [subcommand] [path]
```

### Routing Table

| Command | Behavior | Sub-skills Invoked |
|---------|----------|-------------------|
| `/codeprobe audit <path>` | Full audit — visual health dashboard (category scores, codebase stats, hot spots) followed by detailed P0-P3 findings with fix prompts | All available sub-skills + `file_stats.py` |
| `/codeprobe solid <path>` | SOLID principles analysis only | `codeprobe-solid` |
| `/codeprobe security <path>` | Security audit only | `codeprobe-security` |
| `/codeprobe smells <path>` | Code smells detection only | `codeprobe-code-smells` |
| `/codeprobe architecture <path>` | Architecture analysis only | `codeprobe-architecture` |
| `/codeprobe patterns <path>` | Design patterns analysis only | `codeprobe-patterns` |
| `/codeprobe performance <path>` | Performance audit only | `codeprobe-performance` |
| `/codeprobe errors <path>` | Error handling audit only | `codeprobe-error-handling` |
| `/codeprobe tests <path>` | Test quality audit only | `codeprobe-testing` |
| `/codeprobe framework <path>` | Framework best practices only | `codeprobe-framework` |
| `/codeprobe quick <path>` | Top 5 issues — run all sub-skills in scan mode, then generate full detail for top 5 | All available |
| `/codeprobe diff [branch]` | PR-style review on changed files vs branch (default: `main`) | All relevant (Phase 3) |
| `/codeprobe report` | Generate report from last audit | (Phase 3 — TBD) |

### Default Behaviors

- **No subcommand given**: Ask the user what they want. Present the available commands.
- **No path given**: Use the current working directory.
- **Phase 3 stubs**: If the user invokes `diff` or `report`, respond: "This feature is coming in Phase 3. Available now: audit, solid, security, smells, architecture, patterns, performance, errors, tests, framework, quick."

---

## 2. Stack Auto-Detection

Before routing to any sub-skill, detect the technology stack at the target path. This informs which reference guides to load and pass to sub-skills.

### Detection Procedure

1. Use Glob to scan file extensions at the target path (recursive, reasonable depth).
2. Apply the following detection rules — multiple stacks can match simultaneously:

| Signal | Stack Detected | Reference to Load |
|--------|---------------|-------------------|
| `.php` files | PHP / Laravel | `references/php-laravel.md` |
| `.js`, `.ts`, `.jsx`, `.tsx` files | JavaScript / TypeScript | `references/javascript-typescript.md` |
| `.py` files | Python | `references/python.md` |
| `.jsx`, `.tsx` files + `next.config.*` present | React / Next.js | `references/react-nextjs.md` |
| `.sql` files or `migrations/` directory | SQL / Database | `references/sql-database.md` |
| `routes/` directory or API route patterns | API Design | `references/api-design.md` |

3. For each detected stack, attempt to load the corresponding reference file using Read. If the file does not exist yet (Phase 2+), skip silently.
4. Collect all loaded references into a context bundle to pass to sub-skills.

### Reference Loading

References are loaded from the `references/` directory within this skill's own directory. Resolve the path relative to this SKILL.md file's location, NOT the user's project. Use Read with:
```
references/{reference-file}.md
```
(This resolves to the `references/` folder next to this SKILL.md file.)

If a reference file does not exist, continue without it. Never fail the review because a reference is missing.

---

## 3. Config Loading

Check for a `.codeprobe-config.json` file in the project root (the target path or its ancestor directories).

### Config Schema

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

### Config Behavior

- **If absent**: All defaults apply. No error.
- **`severity_overrides`**: Pass to sub-skills so they adjust thresholds accordingly.
- **`skip_categories`**: Do not invoke the listed sub-skills, even in `audit` or `quick` mode.
- **`skip_rules`**: Pass to sub-skills so they suppress findings with matching IDs.
- **`framework`**: If set, skip auto-detection for that framework and force-load the corresponding reference. Other auto-detection still proceeds.
- **`extra_references`**: Additional reference file paths to load and pass to sub-skills.
- **`report_format`**: Output format preference (default: `markdown`).

---

## 4. Sub-Skill Execution

### Pre-Loading Phase (runs once before any sub-skill)

Before invoking any sub-skill, the orchestrator MUST pre-load all shared context:

1. **Read the shared preamble** from `shared-preamble.md` (in this skill's directory). This contains the output contract, execution modes, and constraints shared by all sub-skills.

2. **Read all source files** at the target path:
   - Use Glob to find all source files (`.ts`, `.tsx`, `.js`, `.jsx`, `.py`, `.php`, `.vue`, `.sql`, `.css`, `.scss` and config files like `next.config.*`, `package.json`, `composer.json`, `requirements.txt`, `.env.example`).
   - Read each file using Read.
   - **Size cap:** If the codebase has more than 50 source files or total LOC exceeds 10,000 lines, do NOT pre-load all files. Instead, pass only the file listing (paths + line counts) and let sub-agents read files they need. Note this in the agent prompt: "Large codebase — file listing provided, use Read for files you need to inspect."
   - Store all file contents as a map: `{filepath: content}`.

3. **Read all applicable reference files** (already loaded during stack detection in Section 2). Store the content.

### Invocation Protocol

For each sub-skill to run, spawn an Agent with a prompt that includes:

1. **The shared preamble** (from `shared-preamble.md`) — output contract, modes, constraints.
2. **The sub-skill name** to invoke (e.g., `codeprobe-security`).
3. **The mode** — one of `full` or `scan`.
4. **Pre-loaded source files** — the full content of every source file, formatted as:
   ```
   === FILE: {filepath} ===
   {content}
   === END FILE ===
   ```
5. **Pre-loaded references** — the content of all applicable reference files.
6. **Config overrides** — severity overrides and skip rules from `.codeprobe-config.json`.
7. **Target path** — so the sub-skill knows the project root for any targeted lookups.
8. **Sub-skill-specific pre-loaded script output (when applicable)**:
   - For `codeprobe-architecture`: before spawning the agent, run `python3 scripts/dependency_mapper.py <target_path>` via Bash and capture the JSON output. Pass it as an additional context block labeled `=== DEPENDENCY_GRAPH === ... === END DEPENDENCY_GRAPH ===`. The sub-skill uses this as the ground truth for cycle detection. If Python 3 is unavailable or the script fails, omit the block — the sub-skill falls back to LLM-based import tracing.
   - For `codeprobe-performance`: if `scripts/complexity_scorer.py` output is available (optional), pass it as `=== COMPLEXITY_SCORES === ... === END COMPLEXITY_SCORES ===`.

The sub-skill's own SKILL.md contains only its domain-specific detection logic. All shared context (output format, modes, source code, references, pre-computed script data) comes from the orchestrator's prompt.

**Collect findings** returned by each sub-skill in the standard output contract format (Section 5).

### Execution Modes

| Mode | Used By | Behavior |
|------|---------|----------|
| `full` | `/codeprobe audit`, `/codeprobe solid`, etc. | Run complete analysis, return all findings |
| `scan` | `/codeprobe quick` | Count violations, identify top issues, return only counts + top 5 candidates |

### Execution Order

- **`/codeprobe audit`**: Run sub-skills sequentially in this order: `codeprobe-security`, `codeprobe-error-handling`, `codeprobe-solid`, `codeprobe-architecture`, `codeprobe-patterns`, `codeprobe-performance`, `codeprobe-code-smells`, `codeprobe-testing`, `codeprobe-framework` — all in `full` mode. Before invoking `codeprobe-architecture`, pre-compute the dependency graph via `scripts/dependency_mapper.py` and pass the JSON to the sub-skill as described in the Invocation Protocol (step 8). Collect all findings. Apply deduplication (Section 7A). Derive category scores from severity counts. Compute hot spots by aggregating findings per file and ranking by distinct-categories-flagged. Also run `scripts/file_stats.py` for codebase stats (skip gracefully if Python 3 unavailable).
- **`/codeprobe quick`**: Run all 9 sub-skills in `scan` mode. Collect candidate issues from all. Rank by severity (critical > major > minor > suggestion), then select top 5. Re-run relevant sub-skills in `full` mode for just those 5 findings to get complete detail.

### Available Sub-Skills

1. `codeprobe-security` — Security vulnerability detection
2. `codeprobe-error-handling` — Error handling & resilience
3. `codeprobe-solid` — SOLID principles analysis
4. `codeprobe-architecture` — Architecture analysis
5. `codeprobe-patterns` — Design patterns advisor
6. `codeprobe-performance` — Performance & scalability
7. `codeprobe-code-smells` — Code smell detection
8. `codeprobe-testing` — Test quality & coverage
9. `codeprobe-framework` — Framework-specific best practices

---

## 5. Output Contract

Every finding from every sub-skill MUST include these fields:

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique identifier in format `{PREFIX}-{NNN}` (e.g., `SRP-001`, `SEC-003`) |
| `severity` | Yes | One of: `critical`, `major`, `minor`, `suggestion` |
| `location` | Yes | File path + line range (e.g., `src/UserService.php:45-67`) |
| `problem` | Yes | One sentence describing the issue |
| `evidence` | Yes | Concrete proof from the code — quote the relevant lines |
| `suggestion` | Yes | What to do to fix it |
| `fix_prompt` | Yes | A copy-pasteable prompt the user can give to Claude Code to apply the fix |
| `refactored_sketch` | No | Optional code snippet showing the improved version |

### Finding Format Example

```
### SRP-001 | Major | `src/UserService.php:45-67`

**Problem:** UserService violates Single Responsibility — handles authentication, email sending, and database queries in one class.

**Evidence:**
> Lines 45-50: `public function authenticate($credentials) { ... }`
> Lines 52-60: `public function sendWelcomeEmail($user) { ... }`
> Lines 62-67: `public function findByUsername($name) { ... }`

**Suggestion:** Extract email logic into a dedicated `UserMailer` service and database queries into a `UserRepository`.

**Fix prompt:**
> Refactor `src/UserService.php` to follow Single Responsibility Principle: extract `sendWelcomeEmail()` into a new `UserMailer` class and `findByUsername()` into a `UserRepository` class. Keep `authenticate()` in `UserService` and inject the new dependencies.
```

---

## 6. Severity Levels

| Level | Priority | Meaning | Examples |
|-------|----------|---------|----------|
| Critical | P0 | **Confirmed bugs, exploitable security vulnerabilities, or data loss/corruption risks** that would cause harm in production | SQL injection with user input, missing auth on data-mutating endpoint, race condition causing data corruption, unhandled crash on a core path, missing DB transaction on multi-step writes |
| Major | P1 | Significant maintainability, reliability, or scalability problem that increases risk but is not an immediate production defect | Missing tests for critical business logic, large classes, code duplication, missing error handling on external calls, N+1 queries, missing input validation |
| Minor | P2 | Code smell, low risk, worth addressing for long-term health | Magic numbers, deep nesting, poor naming, missing edge case tests, verbose error details |
| Suggestion | P3 | Improvement idea, nice to have, no real risk if ignored | Pattern opportunities, style improvements, speculative generality |

### Severity Guardrails

**The following are NEVER Critical — classify as Major at most:**
- Missing tests (even for critical business logic)
- Code duplication or large classes/files
- Code smells of any kind
- Framework convention violations
- Missing documentation, comments, or type annotations

**Critical is reserved exclusively for:**
- Confirmed bugs (code that produces wrong results or crashes)
- Exploitable security vulnerabilities (injection, auth bypass, IDOR with proof)
- Data loss or corruption risks (missing transactions, race conditions on writes)
- Sensitive data exposure (secrets in code, credentials in logs)

**Sub-skills: do NOT escalate findings beyond the severity specified in your detection table.** If your table says "Major," report it as Major even if the specific instance seems severe. The orchestrator's scoring formula accounts for finding counts at each level.

---

## 7. Scoring

After collecting all findings, compute scores per category and an overall score.

### Category Score Formula

Each penalty component is capped to prevent a single severity level from dominating the score:

```
crit_penalty  = min(50, critical_count * 15)
major_penalty = min(30, major_count * 6)
minor_penalty = min(10, minor_count * 2)

category_score = max(0, 100 - crit_penalty - major_penalty - minor_penalty)
```

Suggestions do not affect the score.

**Rationale:** Diminishing returns prevent a single severity from flooring the score. A category with 4 criticals scores 40 (not 0), reflecting problems exist but the code is not completely broken. The maximum total penalty from all three levels combined is 90, so a score of 0 requires extreme findings across all severities.

### Category Weights

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

All 9 categories are active. Weights sum to 100%.

### Overall Score

```
overall = sum(category_score_i * weight_i for each active category)
```

If `skip_categories` in `.codeprobe-config.json` excludes some categories, normalize by dividing by the sum of active weights:

```
overall = sum(category_score_i * weight_i for each active category) / sum(weight_i for each active category)
```

Clamp the result to the range [0, 100].

### Score Interpretation

| Range | Status |
|-------|--------|
| 80-100 | Healthy |
| 60-79 | Needs Attention |
| 0-59 | Critical |

---

## 7A. Cross-Category Deduplication

Before computing scores, deduplicate findings that flag the same issue from multiple categories.

### Deduplication Procedure

1. **Group findings by location.** Normalize each finding's `location` to `{file}:{start_line}`. Two findings overlap if they share the same file AND their line ranges overlap (i.e., start_line_A <= end_line_B AND start_line_B <= end_line_A).

2. **For each group of overlapping findings from different categories:**
   a. **Select a primary finding.** Use this priority order:
      - Security findings (SEC) take priority for anything involving auth, injection, or data exposure
      - Error Handling findings (ERR) take priority for exception/validation issues
      - Performance findings (PERF) take priority for query/caching issues
      - SOLID findings (SRP/OCP/LSP/ISP/DIP) take priority for structural violations
      - Architecture findings (ARCH) take priority for layer/boundary violations
      - If still ambiguous, the category with the higher weight (Section 7) wins
   b. **Mark duplicates.** For each non-primary finding in the group, append to its `problem` field: `[Duplicate of {primary_id} — counted there]` and change its severity to `suggestion` so it does not affect the score of its own category.
   c. **Cross-reference the primary.** Append to the primary finding's `suggestion` field: `Also flagged by: {list of duplicate category:id pairs}`

3. **Recount severity totals per category** after deduplication, then proceed to scoring.

### Examples

- "Refresh bypasses quota" found as SEC-007, ERR-011, FW-001 at same location: keep SEC-007, mark ERR-011 and FW-001 as duplicates (severity → suggestion).
- "God component" found as SRP-001, SMELL-001, ARCH-005 at same file: keep SRP-001 (SOLID priority for structural), mark others as duplicates.
- Same SRP violation found as SRP-001 and SMELL-001: keep SRP-001, mark SMELL-001 as duplicate.

---

## 8. Report Rendering

Render the final output based on the command used.

### `/codeprobe audit` — Full Audit Report

Use the template at `templates/full-audit-report.md` (loaded via Read). The template opens with a **visual health dashboard** (category scores, codebase stats, hot spots) and then uses a **tiered output format** for findings to control token usage. Render order:

1. **Dashboard header**: `Code Health Report — {project}` title line and `Overall Health: {score}/100 [{status_label}]` where `{status_label}` is derived from the thresholds in the "Status thresholds" block below. Do not use emoji; wrap the status label in square brackets (e.g., `[Healthy]`, `[Needs Attention]`, `[Critical]`).
2. **Category score bars**: a 10-character block-character bar proportional to the score for each of the 9 categories (Architecture, Security, Framework, Performance, SOLID, Design Patterns, Code Smells, Test Quality, Error Handling), followed by `{score}/100 [{status_label}]`. No emoji.
3. **Codebase Stats**: output of `scripts/file_stats.py` (total files, LOC, backend/frontend split, largest file, test file ratio, comment ratio). If Python 3 is unavailable, omit this block and note: "Install Python 3 for codebase statistics."
4. **Hot Spots**: top 3 files by distinct-categories-flagged (computed from the same findings that feed the scores).
5. Horizontal rule.
6. **Executive Summary**: 2-3 sentences covering the most important findings.
7. **Critical findings — Full detail**: Each critical finding rendered with evidence, suggestion, and fix prompt. These are the most important and justify the token cost.
8. **Major findings — Summary table**: One row per major finding with ID, file, problem, and fix prompt. No evidence block (saves ~200 tokens per finding).
9. **Minor findings — Counts only**: Aggregated count per category. No individual findings listed.
10. **Suggestions — Counts only**: Aggregated count per category. No individual findings listed.
11. **Prioritized Fix Order**: Ordered list of all critical and major fix prompts, ranked by impact.
12. **Save report to file**: ensure `./codeprobe-reports/` exists in the current working directory (create via Bash `mkdir -p ./codeprobe-reports` if missing). Write the full rendered markdown from steps 1-11 to `./codeprobe-reports/{YYYY-MM-DD-HHMMSS}.md` using the `Write` tool. Use the same markdown that was rendered to the terminal — do NOT re-render. After writing, emit a final terminal line: `--> Report saved to ./codeprobe-reports/{filename}` (no emoji; use the ASCII arrow). If the write fails (read-only filesystem, permission denied, etc.), surface the error as a short inline note but do not block or re-emit the terminal output.

If the template does not exist, render inline following the same structure. Step 12 (save) still applies regardless.

Status thresholds (applied to overall health and each category score):
- 80-100 = "Healthy"
- 60-79 = "Needs Attention"
- 0-59 = "Critical"

**Token budget guidance:** For a codebase with ~100 findings, the tiered findings format (steps 7-10) targets ~8,000-12,000 tokens (vs ~40,000 with full detail for all findings). The dashboard adds a small fixed cost (~400 tokens). The user can drill into specific categories with `/codeprobe security .` etc. for full detail on any category.

### `/codeprobe quick` — Quick Review Summary

Use the template at `templates/quick-review-summary.md` (loaded via Read). If the template does not exist yet, render inline:

1. **Header**: Project name, "Quick Review — Top 5 Issues".
2. **Top 5 Findings**: Full detail for the 5 most impactful issues, each with fix prompt.
3. **Summary Counts**: Total issues found by severity across all categories.
4. **Next Step**: Suggest running `/codeprobe audit` for the complete picture.

## 9. Claude.ai Degraded Mode

Detect whether filesystem access is available. If the user has pasted or uploaded code rather than providing a file path, or if Read/Glob/Grep tools are unavailable:

1. **Switch to degraded mode**: Analyze only the in-context code provided.
2. **Execute sub-skills sequentially** on the pasted code (no parallel agents).
3. **Skip** `file_stats.py`, `dependency_mapper.py`, and all script-dependent steps (sub-skills fall back to LLM-only analysis — architecture loses deterministic cycle detection).
4. **Skip** `/codeprobe diff`, `/codeprobe report`, the Codebase Stats row of the audit dashboard, and the report-save step (no filesystem write). Still render scores, hot spots, and findings to the terminal.
5. **Inform the user**: "Running in Claude.ai mode — some features like codebase statistics, diff review, and multi-file analysis are unavailable. Analyzing the provided code directly."
6. Still produce findings in the standard output contract format.
7. Still compute scores based on findings from available sub-skills.

---

## 10. Phase 3 Stubs

When the user invokes a command that routes to an unbuilt feature, respond with:

> **Not yet available.** This feature is coming in Phase 3. Currently available commands:
>
> - `/codeprobe audit <path>` — Full code audit
> - `/codeprobe solid <path>` — SOLID principles check
> - `/codeprobe security <path>` — Security audit
> - `/codeprobe smells <path>` — Code smells detection
> - `/codeprobe architecture <path>` — Architecture analysis
> - `/codeprobe patterns <path>` — Design patterns analysis
> - `/codeprobe performance <path>` — Performance audit
> - `/codeprobe errors <path>` — Error handling audit
> - `/codeprobe tests <path>` — Test quality audit
> - `/codeprobe framework <path>` — Framework best practices
> - `/codeprobe quick <path>` — Top 5 issues

This applies to: `diff`, `report`.

---

## 11. Execution Flow Summary

When `/codeprobe` is invoked, execute this sequence:

1. **Parse command**: Extract subcommand and target path from user input.
2. **Validate command**: Check routing table. If Phase 3 stub, respond with stub message.
3. **Resolve target path**: Use provided path or default to current working directory.
4. **Load config**: Check for `.codeprobe-config.json` at project root. Apply defaults if absent.
5. **Auto-detect stack**: Scan target path for technology signals. Load matching references.
6. **Apply config overrides**: If `framework` is set in config, adjust detection. Apply `skip_categories` and `skip_rules`.
7. **Execute sub-skills**: Route to appropriate sub-skills based on command and mode.
8. **Collect findings**: Aggregate all findings in the output contract format.
9. **Deduplicate findings**: Apply the cross-category deduplication procedure (Section 7A). Adjust severity of duplicates to `suggestion`. Recount severity totals per category.
10. **Compute scores**: Calculate per-category and overall scores using the post-deduplication severity counts and the formulas in Section 7.
11. **Render report**: Format output using the appropriate template or inline format. Use the tiered output format for `/codeprobe audit`.
12. **Present to user**: Display the final report.

**Remember: This entire process is READ-ONLY. At no point do we modify any user files.**
