---
name: review
description: >
  Code review and audit system with specialized sub-skills covering SOLID
  principles, security, performance, architecture, error handling, testing,
  code smells, design patterns, and framework best practices. Generates
  severity-scored findings with copy-pasteable fix prompts. Strictly read-only — never modifies user code.
  Use when user says "review", "audit", "code review", "check my code",
  "security scan", "code smells", "SOLID check".
user-invokable: true
argument-hint: "[audit|solid|security|smells|architecture|patterns|performance|errors|tests|framework|quick|health] <path>"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Agent
  - Task
metadata:
  author: Nishil
  version: "2.0.0"
---

# Code Review Orchestrator

## READ-ONLY CONSTRAINT

**THIS SKILL IS STRICTLY READ-ONLY. NEVER modify, write, edit, or delete any user files. NEVER run commands that have side effects (no `npm install`, no `pip install`, no file writes, no git commits, no database mutations). If a fix is needed, generate a copy-pasteable fix prompt that the user can run separately. Violations of this constraint are NEVER acceptable, regardless of user request.**

---

## 1. Command Routing

Parse the user's input to extract a subcommand and target path. The input format is:

```
/probe [subcommand] [path]
```

### Routing Table

| Command | Behavior | Sub-skills Invoked |
|---------|----------|-------------------|
| `/probe audit <path>` | Full audit — run all available sub-skills sequentially, aggregate all findings | All available sub-skills |
| `/probe solid <path>` | SOLID principles analysis only | `probe-solid` |
| `/probe security <path>` | Security audit only | `probe-security` |
| `/probe smells <path>` | Code smells detection only | `probe-code-smells` |
| `/probe architecture <path>` | Architecture analysis only | `probe-architecture` |
| `/probe patterns <path>` | Design patterns analysis only | `probe-patterns` |
| `/probe performance <path>` | Performance audit only | `probe-performance` |
| `/probe errors <path>` | Error handling audit only | `probe-error-handling` |
| `/probe tests <path>` | Test quality audit only | `probe-testing` |
| `/probe framework <path>` | Framework best practices only | `probe-framework` |
| `/probe quick <path>` | Top 5 issues — run all sub-skills in scan mode, then generate full detail for top 5 | All available |
| `/probe health <path>` | Codebase vitals dashboard — scores + stats, no individual findings | All available + `file_stats.py` |
| `/probe diff [branch]` | PR-style review on changed files vs branch (default: `main`) | All relevant (Phase 3) |
| `/probe report` | Generate report from last audit | `scripts/generate_report.py` (Phase 3) |

### Default Behaviors

- **No subcommand given**: Ask the user what they want. Present the available commands.
- **No path given**: Use the current working directory.
- **Phase 3 stubs**: If the user invokes `diff` or `report`, respond: "This feature is coming in Phase 3. Available now: audit, solid, security, smells, architecture, patterns, performance, errors, tests, framework, quick, health."

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

Check for a `.probe-config.json` file in the project root (the target path or its ancestor directories).

### Config Schema

```json
{
  "severity_overrides": {
    "long_method_loc": 50,
    "large_class_loc": 500,
    "deep_nesting_max": 4,
    "max_constructor_deps": 6
  },
  "skip_categories": ["probe-testing"],
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

### Invocation Protocol

For each sub-skill to run:

1. **Invoke the sub-skill by name** (e.g., `probe-solid`, `probe-security`).
2. **Pass the following context** to each sub-skill:
   - `target_path`: The path to review.
   - `detected_stack`: List of detected technology stacks.
   - `references`: Content of all loaded reference files.
   - `config_overrides`: Severity overrides and skip rules from config.
   - `mode`: One of `full`, `scan`, or `score-only` (see below).
3. **Collect findings** returned by each sub-skill in the standard output contract format (Section 5).

### Execution Modes

| Mode | Used By | Behavior |
|------|---------|----------|
| `full` | `/probe audit`, `/probe solid`, etc. | Run complete analysis, return all findings |
| `scan` | `/probe quick` | Count violations, identify top issues, return only counts + top 5 candidates |
| `score-only` | `/probe health` | Return only category score, no individual findings |

### Execution Order

- **`/probe audit`**: Run sub-skills sequentially in this order: `probe-security`, `probe-error-handling`, `probe-solid`, `probe-architecture`, `probe-patterns`, `probe-performance`, `probe-code-smells`, `probe-testing`, `probe-framework`. Collect all findings.
- **`/probe quick`**: Run all 9 sub-skills in `scan` mode. Collect candidate issues from all. Rank by severity (critical > major > minor > suggestion), then select top 5. Re-run relevant sub-skills in `full` mode for just those 5 findings to get complete detail.
- **`/probe health`**: Run all 9 sub-skills in `score-only` mode. Also run `file_stats.py` if Python 3 is available. Render the health dashboard.

### Available Sub-Skills

1. `probe-security` — Security vulnerability detection
2. `probe-error-handling` — Error handling & resilience
3. `probe-solid` — SOLID principles analysis
4. `probe-architecture` — Architecture analysis
5. `probe-patterns` — Design patterns advisor
6. `probe-performance` — Performance & scalability
7. `probe-code-smells` — Code smell detection
8. `probe-testing` — Test quality & coverage
9. `probe-framework` — Framework-specific best practices

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

| Level | Label | Emoji | Meaning |
|-------|-------|-------|---------|
| Critical | Critical | 🔴 | Bugs, security holes, data loss risks in production |
| Major | Major | 🟠 | Significant maintainability or scalability problem |
| Minor | Minor | 🟡 | Code smell, low risk, worth addressing |
| Suggestion | Suggestion | 🔵 | Improvement idea, nice to have |

---

## 7. Scoring

After collecting all findings, compute scores per category and an overall score.

### Category Score Formula

```
category_score = max(0, 100 - (critical_count * 25) - (major_count * 10) - (minor_count * 3))
```

Suggestions do not affect the score.

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

If `skip_categories` in `.probe-config.json` excludes some categories, normalize by dividing by the sum of active weights:

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

## 8. Report Rendering

Render the final output based on the command used.

### `/probe audit` — Full Audit Report

Use the template at `templates/full-audit-report.md` (loaded via Read). If the template does not exist yet, render the report inline with this structure:

1. **Header**: Project name, date, overall score, score breakdown by category.
2. **Executive Summary**: 2-3 sentences covering the most important findings.
3. **Findings by Category**: Group findings by sub-skill, sorted by severity (critical first).
4. **Score Card**: Table of category scores with bar visualization.
5. **Recommended Fix Order**: List the top findings to address first, ordered by impact.

### `/probe quick` — Quick Review Summary

Use the template at `templates/quick-review-summary.md` (loaded via Read). If the template does not exist yet, render inline:

1. **Header**: Project name, "Quick Review — Top 5 Issues".
2. **Top 5 Findings**: Full detail for the 5 most impactful issues, each with fix prompt.
3. **Summary Counts**: Total issues found by severity across all categories.
4. **Next Step**: Suggest running `/probe audit` for the complete picture.

### `/probe health` — Health Dashboard

Render the dashboard inline in this format:

```
Code Health Report — {project_name}

Overall Health: {score}/100 {status_emoji}

Category Scores:
  Security        {bar}  {score}/100  {status}
  SOLID           {bar}  {score}/100  {status}
  Architecture    {bar}  {score}/100  {status}
  Error Handling  {bar}  {score}/100  {status}
  Performance     {bar}  {score}/100  {status}
  Test Quality    {bar}  {score}/100  {status}
  Code Smells     {bar}  {score}/100  {status}
  Design Patterns {bar}  {score}/100  {status}
  Framework       {bar}  {score}/100  {status}

Codebase Stats: (from file_stats.py)
  Files: {n}  |  Total LOC: {n}
  Largest file: {file} ({loc} LOC)
  Test files: {n} / {total} ({pct}%)
  Comment ratio: {pct}%
  Avg method length: {n} LOC

Hot Spots (files needing most attention):
  1. {file} — {n} categories flagged
  2. {file} — {n} categories flagged
  3. {file} — {n} categories flagged

Run `/probe audit` for detailed findings and fix prompts.
```

The bar is a visual indicator using block characters, proportional to the score (e.g., 10 characters wide).

Status thresholds:
- 80-100 = "Healthy"
- 60-79 = "Needs Attention"
- 0-59 = "Critical"

If `file_stats.py` is unavailable or Python 3 is not installed, omit the "Codebase Stats" section and note: "Install Python 3 for codebase statistics."

---

## 9. Claude.ai Degraded Mode

Detect whether filesystem access is available. If the user has pasted or uploaded code rather than providing a file path, or if Read/Glob/Grep tools are unavailable:

1. **Switch to degraded mode**: Analyze only the in-context code provided.
2. **Execute sub-skills sequentially** on the pasted code (no parallel agents).
3. **Skip** `file_stats.py` and all script-dependent steps.
4. **Skip** `/probe diff`, `/probe health` stats section, and `/probe report`.
5. **Inform the user**: "Running in Claude.ai mode — some features like codebase statistics, diff review, and multi-file analysis are unavailable. Analyzing the provided code directly."
6. Still produce findings in the standard output contract format.
7. Still compute scores based on findings from available sub-skills.

---

## 10. Phase 3 Stubs

When the user invokes a command that routes to an unbuilt feature, respond with:

> **Not yet available.** This feature is coming in Phase 3. Currently available commands:
>
> - `/probe audit <path>` — Full code audit
> - `/probe solid <path>` — SOLID principles check
> - `/probe security <path>` — Security audit
> - `/probe smells <path>` — Code smells detection
> - `/probe architecture <path>` — Architecture analysis
> - `/probe patterns <path>` — Design patterns analysis
> - `/probe performance <path>` — Performance audit
> - `/probe errors <path>` — Error handling audit
> - `/probe tests <path>` — Test quality audit
> - `/probe framework <path>` — Framework best practices
> - `/probe quick <path>` — Top 5 issues
> - `/probe health <path>` — Codebase vitals dashboard

This applies to: `diff`, `report`.

---

## 11. Execution Flow Summary

When `/review` is invoked, execute this sequence:

1. **Parse command**: Extract subcommand and target path from user input.
2. **Validate command**: Check routing table. If Phase 3 stub, respond with stub message.
3. **Resolve target path**: Use provided path or default to current working directory.
4. **Load config**: Check for `.probe-config.json` at project root. Apply defaults if absent.
5. **Auto-detect stack**: Scan target path for technology signals. Load matching references.
6. **Apply config overrides**: If `framework` is set in config, adjust detection. Apply `skip_categories` and `skip_rules`.
7. **Execute sub-skills**: Route to appropriate sub-skills based on command and mode.
8. **Collect findings**: Aggregate all findings in the output contract format.
9. **Compute scores**: Calculate per-category and overall scores using the formulas above.
10. **Render report**: Format output using the appropriate template or inline format.
11. **Present to user**: Display the final report.

**Remember: This entire process is READ-ONLY. At no point do we modify any user files.**
