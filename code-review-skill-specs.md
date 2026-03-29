# Code Review & Audit Skill System — Specification Document
## `codeprobe-claude`

**Version:** 0.6 (Name Finalized)
**Author:** Nishil + Claude
**Date:** 2026-03-28
**Repo:** `github.com/nishil-patel/codeprobe-claude` *(placeholder — update with actual GitHub username)*
**Status:** Ready to Build — Phase 1

---

## 1. Problem Statement

Automated linters and formatters catch syntax-level issues but miss architectural rot — SOLID violations, missing abstractions, security anti-patterns, performance traps, and framework misuse. Manual code review is inconsistent and depends on the reviewer's experience.

This skill system brings senior-engineer-level code review to Claude Code (full mode) and Claude.ai (degraded mode) as a team of specialized sub-skills, each a domain expert, orchestrated by a central router.

### ⛔ HARD CONSTRAINT: READ-ONLY — NEVER MODIFY USER CODE

This entire skill system is **strictly read-only**. No sub-skill, agent, script, or orchestrator may:

- Write to, edit, rename, move, or delete any file in the user's codebase
- Run `str_replace`, `sed`, `patch`, or any file-modification tool on user files
- Execute commands that have side effects on the project (`npm install`, `composer require`, `git commit`, migrations, etc.)
- Create files inside the user's project directory (reports go to a separate output path)
- Run test suites, build commands, or anything that modifies state

**The skill reads code. It reports findings. It generates fix prompts. The user decides what to change and when.**

This constraint applies even if the user asks the skill to "fix it" — the skill should respond with fix prompts, not apply changes. If the user wants auto-fix, they take the fix prompts and run them separately in Claude Code outside of this skill's scope.

---

## 2. Architecture Overview

Follows the multi-skill orchestrator pattern (ref: `geo-seo-claude`).

```
codeprobe-claude/
├── review/                           # Main orchestrator skill
│   └── SKILL.md                      # Primary skill — command routing & synthesis
│
├── skills/                           # 9 specialized sub-skills (domain experts)
│   ├── codeprobe-solid/             # SOLID principles auditor
│   │   └── SKILL.md
│   ├── codeprobe-patterns/          # Design patterns advisor
│   │   └── SKILL.md
│   ├── codeprobe-security/          # Security vulnerability scanner
│   │   └── SKILL.md
│   ├── codeprobe-performance/       # Performance & scalability auditor
│   │   └── SKILL.md
│   ├── codeprobe-architecture/      # Architecture & structure analyzer
│   │   └── SKILL.md
│   ├── codeprobe-error-handling/    # Error handling & resilience checker
│   │   └── SKILL.md
│   ├── codeprobe-testing/           # Test quality & coverage auditor
│   │   └── SKILL.md
│   ├── codeprobe-code-smells/       # Code smells & anti-pattern detector
│   │   └── SKILL.md
│   └── codeprobe-framework/         # Framework-specific best practices
│       └── SKILL.md
│
├── agents/                           # Parallel subagents for full audit
│   ├── agent-structural.md           # Runs: solid + architecture + patterns
│   ├── agent-safety.md               # Runs: security + error-handling
│   ├── agent-quality.md              # Runs: code-smells + testing
│   └── agent-runtime.md              # Runs: performance + framework
│
├── references/                       # Language/framework-specific rule sets
│   ├── php-laravel.md                # Laravel conventions, Eloquent patterns, etc.
│   ├── javascript-typescript.md      # JS/TS patterns, async pitfalls, etc.
│   ├── python.md                     # Pythonic patterns, Django/FastAPI specifics
│   ├── react-nextjs.md               # React/Next.js component patterns
│   ├── sql-database.md               # Query patterns, N+1, indexing, migrations
│   └── api-design.md                 # REST/GraphQL conventions, versioning
│
├── templates/                        # Report output templates
│   ├── full-audit-report.md          # Comprehensive report template
│   ├── pr-review-comment.md          # GitHub PR comment format
│   └── quick-review-summary.md       # Quick single-file summary
│
├── scripts/                          # Deterministic analysis utilities
│   ├── complexity_scorer.py          # Cyclomatic complexity calculator
│   ├── dependency_mapper.py          # Import/dependency graph generator
│   ├── file_stats.py                 # LOC, class count, method count per file
│   └── generate_report.py            # Markdown/PDF report aggregator
│
├── install.sh
├── uninstall.sh
├── requirements.txt
└── README.md
```

---

## 3. Orchestrator Skill (`codeprobe/SKILL.md`)

### Responsibilities

- Parse user command and determine scope (file, directory, PR, full project)
- Auto-detect language/framework from file extensions and imports
- Route to appropriate sub-skills
- For full audits: spawn parallel subagents
- Aggregate sub-skill outputs into unified report with severity scoring
- Apply the correct `references/*.md` based on detected stack

### Commands

| Command | Description | Sub-skills Invoked |
|---|---|---|
| `/codeprobe audit <path>` | Full audit — spawns all 4 agents in parallel | All 9 sub-skills via agents |
| `/codeprobe solid <path>` | SOLID principles check only | `codeprobe-solid` |
| `/codeprobe security <path>` | Security audit only | `codeprobe-security` |
| `/codeprobe performance <path>` | Performance audit only | `codeprobe-performance` |
| `/codeprobe patterns <path>` | Design pattern analysis only | `codeprobe-patterns` |
| `/codeprobe smells <path>` | Code smells detection only | `codeprobe-code-smells` |
| `/codeprobe architecture <path>` | Architecture & structure analysis | `codeprobe-architecture` |
| `/codeprobe errors <path>` | Error handling audit | `codeprobe-error-handling` |
| `/codeprobe tests <path>` | Test quality assessment | `codeprobe-testing` |
| `/codeprobe framework <path>` | Framework-specific best practices | `codeprobe-framework` |
| `/codeprobe quick <path>` | 60-second top-5 issues summary | Lightweight pass across all |
| `/codeprobe health <path>` | Codebase vitals dashboard — scores, stats, hot spots, no individual findings | All sub-skills (scoring only) + all scripts |
| `/codeprobe diff [branch]` | PR-style review — only changed files vs branch (default: main) | All relevant sub-skills on diff only |
| `/codeprobe report` | Generate full report from last audit | `scripts/generate_report.py` |

### Severity Levels

Every finding gets a severity:

| Level | Label | Meaning |
|---|---|---|
| 🔴 | **Critical** | Will cause bugs, security holes, or data loss in production |
| 🟠 | **Major** | Significant maintainability/scalability problem |
| 🟡 | **Minor** | Code smell or sub-optimal pattern, low risk |
| 🔵 | **Suggestion** | Improvement idea, not a problem |

### Output Contract

Every sub-skill returns findings in this structure. **`fix_prompt` is a required field on every finding from every sub-skill** — it's the user's primary action item.

```json
{
  "skill": "codeprobe-solid",
  "file": "app/Services/OrderService.php",
  "findings": [
    {
      "id": "SRP-001",
      "severity": "major",
      "principle": "Single Responsibility",
      "location": { "file": "OrderService.php", "lines": "45-120" },
      "problem": "OrderService handles order creation, payment processing, email notifications, and inventory updates.",
      "evidence": "4 unrelated concerns in one class (order logic, payment gateway calls, mailer, stock management).",
      "suggestion": "Extract PaymentService, OrderNotifier, InventoryService. OrderService delegates to each.",
      "fix_prompt": "Refactor OrderService: extract payment logic (lines 45-78) into PaymentService, email logic (lines 80-95) into OrderNotifier, and inventory updates (lines 97-120) into InventoryService. OrderService should inject all three via constructor and delegate.",
      "refactored_sketch": "// optional: minimal code showing the fix direction"
    }
  ],
  "summary": {
    "critical": 0,
    "major": 2,
    "minor": 3,
    "suggestion": 1
  }
}
```

### Required Fields Per Finding

| Field | Required | Description |
|---|---|---|
| `id` | ✅ | Unique ID: `{CATEGORY_PREFIX}-{NNN}` (e.g., `SRP-001`, `SEC-003`, `PERF-012`) |
| `severity` | ✅ | `critical`, `major`, `minor`, or `suggestion` |
| `location` | ✅ | File path + line range |
| `problem` | ✅ | What's wrong — one sentence |
| `evidence` | ✅ | Why it's wrong — concrete proof from the code |
| `suggestion` | ✅ | What to do about it — human-readable |
| `fix_prompt` | ✅ | **Copy-pasteable prompt** the user can feed into Claude Code to apply the fix. Must be specific: reference file names, line ranges, method names, and the exact change to make. |
| `refactored_sketch` | ❌ | Optional minimal code snippet showing the fix direction |

### Fix Prompt Examples Per Sub-Skill

Every sub-skill generates fix prompts. Here's what they look like per domain:

| Sub-Skill | Example Fix Prompt |
|---|---|
| `codeprobe-solid` | "Refactor OrderService: extract payment logic (lines 45-78) into a new PaymentService class. Inject via constructor." |
| `codeprobe-patterns` | "Replace the switch statement in NotificationSender (lines 30-65) with a Strategy pattern: create NotificationChannel interface with EmailChannel, SmsChannel, PushChannel implementations." |
| `codeprobe-security` | "In UserController@update (line 34), replace `$request->all()` with `$request->only(['name', 'email'])` to prevent mass assignment on is_admin field." |
| `codeprobe-performance` | "In OrderController@index (line 22), add `->with('items', 'customer')` to the Order query to fix the N+1 — currently loading 2 relations lazily inside the blade loop." |
| `codeprobe-architecture` | "Move the pricing calculation logic from OrderController@store (lines 40-75) into a new PricingService class under app/Services/. Controller should call `$this->pricingService->calculate($order)`." |
| `codeprobe-error-handling` | "Wrap the Stripe API call in PaymentService@charge (line 55) in a try/catch for `\Stripe\Exception\ApiErrorException`. Log the error with context and throw a domain-specific PaymentFailedException." |
| `codeprobe-testing` | "Write a test for OrderService@calculateTotal that covers: empty cart (expect 0), single item, multiple items, and item with discount. Use OrderFactory for test data." |
| `codeprobe-code-smells` | "Extract lines 45-90 of UserService@register into a private method `validateAndNormalizeInput()` — the method is 120 LOC doing 3 unrelated things." |
| `codeprobe-framework` | "Move the validation rules from OrderController@store (lines 15-30) into a new StoreOrderRequest form request class. Use `php artisan make:request StoreOrderRequest`." |

---

## 4. Sub-Skill Specifications

### 4.1 `codeprobe-solid` — SOLID Principles Auditor

**Domain:** SRP, OCP, LSP, ISP, DIP

**What it checks:**

| Principle | Detection Signals |
|---|---|
| **SRP** | Class has 5+ public methods doing unrelated things. Method > 30 LOC doing multiple concerns. Class name is vague ("Manager", "Handler", "Utils"). Constructor takes 5+ dependencies (symptom of too many responsibilities). |
| **OCP** | Switch/if-else chains on type/status that would need modification for new variants. No extension point (interface/abstract class) where variants are likely to grow. |
| **LSP** | Subclass overrides method but changes semantics. Subclass throws exception parent doesn't declare. Subclass ignores/no-ops parent behavior. instanceof/type checks after polymorphic call. |
| **ISP** | Interface has 8+ methods. Class implements interface but leaves methods empty/throwing. Multiple unrelated method groups in one interface. |
| **DIP** | `new ConcreteClass()` inside business logic. High-level module imports from infrastructure layer directly. No constructor injection. Static method calls to concrete dependencies. |

**What it does NOT flag:**
- Simple DTOs/value objects with multiple fields (not an SRP violation)
- Small scripts/CLIs that don't need DI
- Enums used in switches where the enum is stable and closed

---

### 4.2 `codeprobe-patterns` — Design Patterns Advisor

**Domain:** GoF patterns, domain patterns, architectural patterns

**Philosophy:** Never recommend a pattern for the sake of it. Only when a **concrete problem exists** that a pattern solves.

**Detection matrix:**

| Observed Problem | Candidate Pattern | Confidence Threshold |
|---|---|---|
| Complex object construction with 4+ optional params | Builder | High — clear signal |
| Duplicated `new X()` with conditionals scattered across codebase | Factory | High |
| Switch on type to select behavior | Strategy | High |
| Object behavior changes based on state field | State | Medium |
| Multiple listeners need to react to a change | Observer / Event Dispatcher | High |
| Cross-cutting logic (logging, auth, cache) interleaved with business logic | Decorator / Middleware | High |
| God class wrapping a complex subsystem | Facade | Medium |
| Undo/redo or command queue requirements | Command | Medium |
| Data flows through conditional transformation steps | Pipeline / Chain of Responsibility | Medium |
| Multiple similar objects differing by a few fields | Prototype | Low — often overengineering |

**Anti-pattern detection (misapplied patterns):**
- Singleton used for dependency hiding (should be DI)
- Repository pattern wrapping Eloquent but adding zero abstraction (pass-through repository)
- Service class that's just a renamed controller action
- Abstract factory when only one family exists

---

### 4.3 `codeprobe-security` — Security Vulnerability Scanner

**Domain:** OWASP Top 10, language-specific vulnerabilities

**Checks per category:**

| Category | What to Detect |
|---|---|
| **Injection** | Raw SQL with string concatenation/interpolation. `DB::raw()` with user input. Shell command construction with unsanitized input. LDAP/NoSQL injection vectors. |
| **Auth/AuthZ** | Missing auth middleware on routes. Role checks done in blade/view but not backend. Hardcoded secrets/API keys. Weak password policy (no validation rules). JWT without expiration. |
| **XSS** | `{!! !!}` (unescaped) in Laravel Blade with user data. `dangerouslySetInnerHTML` in React. `v-html` in Vue with untrusted data. Missing Content-Security-Policy. |
| **Mass Assignment** | Laravel: model without `$fillable` or `$guarded`. Accepting `$request->all()` into create/update. |
| **CSRF** | Forms without CSRF tokens. API routes without proper auth that modify state. |
| **Insecure Deserialization** | `unserialize()` on user input. `JSON.parse()` without validation on external data used in eval. |
| **Sensitive Data Exposure** | Passwords/tokens in logs. `.env` committed to git. Secrets in config files vs environment. Error messages leaking stack traces in production. |
| **Broken Access Control** | IDOR — using user-supplied ID without ownership check. Missing policy/gate checks on resource access. |
| **Misconfiguration** | `APP_DEBUG=true` in production configs. Permissive CORS (`*`). Default credentials. |

**Does NOT flag:**
- Internal admin tools with IP-restricted access (context-dependent)
- Test files using hardcoded values

---

### 4.4 `codeprobe-performance` — Performance & Scalability Auditor

**Domain:** Query performance, memory, caching, concurrency, algorithmic efficiency

**Checks:**

| Area | What to Detect |
|---|---|
| **N+1 Queries** | Eloquent: loop accessing relationship without `with()`. Any ORM: lazy-loading inside iteration. |
| **Missing Indexes** | `WHERE` / `ORDER BY` on non-indexed columns (cross-ref with migration files). Composite queries needing compound indexes. |
| **Unbounded Queries** | `Model::all()` or `SELECT *` without pagination/limit. Missing cursor/chunk for large dataset processing. |
| **Memory** | Loading entire file into memory (`file_get_contents` on user uploads). Array accumulation in loops without cleanup. Large collection transformations that could be generators/lazy collections. |
| **Caching** | Repeated identical queries without cache. Cache keys without TTL. Cache invalidation missing after writes. Over-caching (caching volatile data). |
| **Algorithmic** | O(n²) or worse in hot paths. Nested loops where a hashmap lookup would work. Sorting inside loops. |
| **Concurrency** | Race conditions in read-modify-write without locks. Queue jobs without idempotency. Shared mutable state in async/parallel contexts. |
| **Frontend** | Unnecessary re-renders (missing `useMemo`, `useCallback`). Bundle size (importing entire lodash). No lazy loading for routes/heavy components. |

---

### 4.5 `codeprobe-architecture` — Architecture & Structure Analyzer

**Domain:** Layering, coupling, cohesion, module boundaries, dependency direction

**Checks:**

| Area | What to Detect |
|---|---|
| **Layer Violations** | Controllers containing business logic. Models containing presentation logic. Views/components calling database directly. |
| **Circular Dependencies** | Module A imports B, B imports A. Runs `scripts/dependency_mapper.py` to generate graph. |
| **God Objects** | File > 500 LOC. Class with 20+ methods. Single file handling request→validate→process→respond→log. |
| **Anemic Domain Model** | Entity classes with only getters/setters. All logic in "Service" classes operating on dumb data bags. |
| **Missing Boundaries** | No clear module/domain separation. Shared database tables across unrelated features. Cross-feature direct imports instead of events/interfaces. |
| **Directory Structure** | Framework conventions violated (Laravel: logic in `app/Http/Controllers` that should be in `app/Services`). Feature folders vs layer folders assessment. |
| **Config/Environment** | Hardcoded environment-specific values. Missing environment abstraction. |

---

### 4.6 `codeprobe-error-handling` — Error Handling & Resilience Checker

**Domain:** Exception handling, logging, graceful degradation, retry logic

**Checks:**

| Area | What to Detect |
|---|---|
| **Swallowed Exceptions** | Empty `catch` blocks. `catch` that only logs but doesn't rethrow/handle. Bare `except:` (Python) / `catch (\Exception)` catching too broadly. |
| **Missing Error Handling** | No try/catch around external API calls, file I/O, DB transactions. Unhandled promise rejections (`async` without `.catch`). |
| **Error Information** | Returning generic "Something went wrong" without actionable detail. Leaking internal errors to API consumers. Missing structured error responses (error codes, messages). |
| **Retry & Circuit Breaker** | External service calls without timeout. No retry logic for transient failures. No circuit breaker for cascading failure prevention. |
| **Validation** | Missing input validation before processing. Implicit null assumptions without null checks. Type coercion bugs (PHP `==` vs `===`). |
| **Transaction Safety** | Multi-step DB operations without transactions. Transaction without proper rollback on failure. |
| **Logging** | No logging on critical failure paths. Logging sensitive data (passwords, tokens, PII). Missing correlation IDs for request tracing. |

---

### 4.7 `codeprobe-testing` — Test Quality & Coverage Auditor

**Domain:** Unit tests, integration tests, test design, assertions

**Checks:**

| Area | What to Detect |
|---|---|
| **Missing Tests** | Public methods with no corresponding test. Critical business logic untested. Edge cases unaddressed (null, empty, boundary values). |
| **Test Smells** | Tests with no assertions ("happy path only"). Tests that test implementation details (mocking every dependency). Brittle tests coupled to database/file system without isolation. Tests that depend on execution order. |
| **Test Structure** | Missing Arrange-Act-Assert separation. Test method names that don't describe the scenario. Single test method testing 5+ unrelated things. |
| **Mock Abuse** | Mocking the SUT (system under test). Mocking value objects. Mock returning mocks. Over-mocking making tests pass regardless of logic. |
| **Coverage Gaps** | No tests for error/exception paths. No tests for authorization/permission logic. No edge case tests (empty arrays, zero values, unicode, large inputs). |
| **Test Data** | Hardcoded IDs that may collide. Factory/fixture setup that's fragile. Tests relying on specific database state. |

---

### 4.8 `codeprobe-code-smells` — Code Smells & Anti-Pattern Detector

**Domain:** Martin Fowler's refactoring catalog, general anti-patterns

**Detection checklist:**

| Smell | Signal | Severity |
|---|---|---|
| Long Method | Function > 30 LOC | Minor |
| Large Class | Class > 300 LOC | Major |
| Feature Envy | Method accesses another object's data 3x+ more than its own | Minor |
| Data Clumps | Same 3+ params passed together in 3+ places | Minor |
| Primitive Obsession | String/int used where a value object is warranted (email, money, status) | Minor |
| Shotgun Surgery | Changing one concept requires edits in 5+ files | Major |
| Divergent Change | One class modified for 3+ unrelated reasons in commit history | Major |
| Dead Code | Unreachable branches, unused imports, commented-out blocks | Minor |
| Magic Numbers | Hardcoded literals without named constants | Minor |
| Boolean Blindness | Method with 2+ boolean params: `process(true, false, true)` | Minor |
| Deep Nesting | > 3 indentation levels | Minor |
| Inappropriate Intimacy | Class accessing another's private/protected internals | Major |
| Speculative Generality | Abstractions/interfaces with only one implementation and no foreseeable second | Suggestion |
| Middle Man | Class that only delegates to another class | Minor |
| Refused Bequest | Subclass inherits but doesn't use parent's methods | Minor |
| Temporal Coupling | Methods must be called in specific order but nothing enforces it | Major |

---

### 4.9 `codeprobe-framework` — Framework-Specific Best Practices

**Domain:** Laravel, Next.js, React, FastAPI, Supabase, etc.

**Approach:** Loads the relevant `references/*.md` file based on detected framework.

**Detection varies by framework. Examples for Laravel:**

| Area | What to Detect |
|---|---|
| **Eloquent** | Raw queries where Eloquent builder works. Missing `$casts`. Using `$attributes` instead of accessors. Not using scopes for repeated query conditions. |
| **Routing** | Logic in route closures instead of controllers. Missing route model binding. No API resource/versioning. |
| **Validation** | Validation in controller instead of Form Request. Missing custom validation rules for business logic. |
| **Queues** | Long-running tasks in request cycle (should be queued). Queue jobs without `$tries`, `$timeout`, `$backoff`. |
| **Events** | Tight coupling where events would decouple. Observer doing too much (should be listeners). |
| **Config** | Calling `env()` outside of config files. Missing config caching consideration. |

**Examples for React/Next.js:**

| Area | What to Detect |
|---|---|
| **Components** | Components > 200 LOC (needs decomposition). Prop drilling > 3 levels (needs context/state management). |
| **Hooks** | `useEffect` with missing/wrong dependency array. State updates inside render. Custom hooks doing too much. |
| **Data Fetching** | Client-side fetch where SSR/SSG is appropriate. No error/loading states. Missing revalidation strategy. |
| **Type Safety** | `any` type usage in TypeScript. Missing return types on exported functions. Props without interface definition. |

---

## 5. Agents (Parallel Execution)

For `/codeprobe audit`, the orchestrator spawns 4 agents simultaneously:

### `agent-structural.md`
- Runs: `codeprobe-solid`, `codeprobe-architecture`, `codeprobe-patterns`
- Focus: Is the code well-structured and maintainable?
- Scope: Analyzes class hierarchy, module boundaries, dependency graph

### `agent-safety.md`
- Runs: `codeprobe-security`, `codeprobe-error-handling`
- Focus: Is the code safe for production?
- Scope: Vulnerability scan, exception handling, input validation

### `agent-quality.md`
- Runs: `codeprobe-code-smells`, `codeprobe-testing`
- Focus: Is the code clean and well-tested?
- Scope: Smell detection, test coverage gaps, test quality

### `agent-runtime.md`
- Runs: `codeprobe-performance`, `codeprobe-framework`
- Focus: Does the code run efficiently and follow framework conventions?
- Scope: Query optimization, caching, framework-specific anti-patterns

---

## 6. Scripts (Deterministic Analysis)

Python utilities for things that shouldn't rely on LLM judgment. **All scripts are read-only** — they read source files and output JSON to stdout. No script writes to the user's project directory. Report output goes to a separate output path.

| Script | Purpose | Output |
|---|---|---|
| `complexity_scorer.py` | Cyclomatic complexity per function/method | JSON: `{file, function, complexity, rating}` |
| `dependency_mapper.py` | Build import/dependency graph, detect circular deps | JSON adjacency list + circular dep list |
| `file_stats.py` | LOC, class count, method count, comment ratio per file | JSON stats per file |
| `generate_report.py` | Aggregate all sub-skill outputs into final markdown/PDF report | Markdown or PDF file (written to output path, never project dir) |

---

## 7. Reference Files

Language-specific rule sets loaded on-demand by sub-skills:

| File | Covers |
|---|---|
| `php-laravel.md` | Laravel conventions, Eloquent patterns, service container, facades vs DI, PHP 8.x features |
| `javascript-typescript.md` | ES6+ patterns, TypeScript strict mode, async/await pitfalls, module systems |
| `python.md` | PEP 8, Pythonic patterns, Django/FastAPI conventions, type hints |
| `react-nextjs.md` | Component patterns, hooks rules, server components, rendering strategies |
| `sql-database.md` | Query optimization, indexing strategy, migration patterns, N+1 detection |
| `api-design.md` | REST conventions, status codes, error format, versioning, rate limiting, pagination |

---

## 8. Report Output Format

### Full Audit Report Structure

```
# Code Review Audit Report
## Project: {name}
## Date: {date}
## Stack: {detected stack}

### Overall Score: {0-100} / 100

### Score Breakdown
| Category          | Score | Critical | Major | Minor |
|-------------------|-------|----------|-------|-------|
| SOLID Compliance  | 72    | 0        | 2     | 3     |
| Design Patterns   | 85    | 0        | 1     | 1     |
| Security          | 58    | 2        | 1     | 0     |
| Performance       | 70    | 0        | 3     | 2     |
| Architecture      | 65    | 0        | 2     | 4     |
| Error Handling    | 45    | 1        | 3     | 2     |
| Test Quality      | 50    | 0        | 4     | 1     |
| Code Smells       | 75    | 0        | 1     | 5     |
| Framework Usage   | 80    | 0        | 1     | 2     |

### 🔴 Critical Issues (Fix Immediately)
{findings with severity=critical}

### 🟠 Major Issues (Fix This Sprint)
{findings with severity=major}

### 🟡 Minor Issues (Tech Debt Backlog)
{findings with severity=minor}

### 🔵 Suggestions
{findings with severity=suggestion}

### Top 5 Quick Wins
{highest impact, lowest effort fixes}

### Refactoring Roadmap
{ordered sequence of changes, considering dependencies between fixes}

### Fix Prompts (Copy into Claude Code)
{numbered list of copy-pasteable prompts to fix each finding, ordered by severity}
{example:}
{1. "Refactor OrderService to extract PaymentService — move lines 45-78 into a new class with processPayment() method"}
{2. "Add $fillable to User model — restrict to: name, email, password"}
{3. "Replace N+1 in OrderController@index — add ->with('items', 'customer') to the query"}
```

### Health Dashboard Output (`/codeprobe health`)

Different from audit. Health answers **"how healthy is this codebase?"** — not "what's wrong with it."

| Aspect | `/codeprobe audit` | `/codeprobe health` |
|---|---|---|
| Analogy | Full medical exam | Vitals dashboard |
| Individual findings | ✅ Yes, with evidence + fix prompts | ❌ No — scores and stats only |
| Fix prompts | ✅ Yes | ❌ No — points to audit |
| Scripts used | Optional (enrich findings) | **Required** (core of output) |
| Time | Heavy | Medium |
| Use case | "Fix my code" | "Should I be worried?" |

**Execution flow:**

1. Run `scripts/file_stats.py` → LOC, file count, class count, method count, comment ratio
2. Run `scripts/complexity_scorer.py` → cyclomatic complexity per function
3. Run `scripts/dependency_mapper.py` → import graph, circular dependency detection
4. Run each sub-skill in **scoring-only mode** — count violations by severity per category, skip evidence/fix-prompt generation
5. Identify **hot spots** — files flagged by 2+ categories
6. Render dashboard

**Output template:**

```
📊 Code Health Report — {project_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Overall Health: {score}/100 {emoji}

Category Scores:
  Security        {bar}  {score}  {status}
  SOLID           {bar}  {score}  {status}
  Architecture    {bar}  {score}  {status}
  Error Handling  {bar}  {score}  {status}
  Performance     {bar}  {score}  {status}
  Test Quality    {bar}  {score}  {status}
  Code Smells     {bar}  {score}  {status}
  Patterns        {bar}  {score}  {status}
  Framework       {bar}  {score}  {status}

Codebase Stats:
  Files: {n}  |  Total LOC: {n}  |  Avg complexity: {n}
  Largest file: {file} ({loc} LOC) {flag_if_over_500}
  Most complex: {class}@{method} (complexity: {n}) {flag_if_over_15}
  Circular deps: {n} detected
  Test files: {n} / {total} ({pct}% coverage by file count)
  Comment ratio: {pct}%
  Avg method length: {n} LOC

Hot Spots (files needing most attention):
  1. {file} — {n} categories flagged
  2. {file} — {n} categories flagged
  3. {file} — {n} categories flagged

Run `/codeprobe audit` for detailed findings and fix prompts.
```

**Status thresholds (configurable via `.codeprobe-config.json`):**

| Score Range | Status | Emoji |
|---|---|---|
| 80–100 | Healthy | ✅ |
| 60–79 | Needs Attention | ⚠️ |
| 0–59 | Critical | 🔴 |

**Claude.ai degraded mode:**
- Scripts unavailable → Codebase Stats section is skipped entirely
- Hot Spots derived from sub-skill scoring only (no file-level stats)
- Category scores still work (based on in-context code analysis)
- Dashboard still renders, just without the metrics section

---

## 9. Scoring Methodology

| Category | Weight |
|---|---|
| Security | 20% |
| SOLID Compliance | 15% |
| Architecture | 15% |
| Error Handling | 12% |
| Performance | 12% |
| Test Quality | 10% |
| Code Smells | 8% |
| Design Patterns | 4% |
| Framework Usage | 4% |

Security weighted highest because vulnerabilities have outsized production impact. Design patterns weighted lowest because over-application causes more harm than missing them.

Scoring formula per category:
```
category_score = 100 - (critical * 25) - (major * 10) - (minor * 3) - (suggestion * 0)
overall_score = Σ (category_score * weight)
```

Clamped to [0, 100].

### Configuration (`.codeprobe-config.json`)

Optional project-level config to customize behavior:

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

If absent, all defaults apply. Orchestrator reads this from project root before routing.

---

## 10. Decisions (Finalized)

| # | Question | Decision |
|---|---|---|
| 1 | Target runtime | **Both** — Claude Code (full) + Claude.ai (degraded). See §10.1 below. |
| 2 | Language priority for v1 | **All 6 references ship in v1.** Target all major stacks from day one. |
| 3 | Git integration | **Both modes.** `audit` for full project scan. `/codeprobe diff` for PR-style git diff. |
| 4 | CI integration | **Markdown first.** SARIF/JSON for GitHub Actions in a later phase. |
| 5 | Severity calibration | **Configurable** via `.codeprobe-config.json` — teams set their own thresholds. |
| 6 | Auto-fix | **No auto-fix.** Instead, generate a **"Fix Prompts"** section — copy-pasteable prompts the user can feed back into Claude Code to apply each fix. |
| 7 | Incremental reviews | **Full scan for v1.** Incremental (changed-files-only) in a later phase. |
| 8 | Test execution | **Static analysis only.** Never run `php artisan test`, `npm test`, etc. — side effects. |

### 10.1 Claude.ai Runtime — Degraded Mode

Claude.ai has **no filesystem access** to the user's project. Code enters context via:

1. **Pasted code** — user copies code into chat
2. **Uploaded files** — individual `.php`, `.js`, `.py` files (land in `/mnt/user-data/uploads/`)
3. **Uploaded archive** — `.zip` or `.tar.gz` of the project (extractable via computer tools)

**What works in Claude.ai:**
- All 9 sub-skills operate on whatever code is in context (pasted or uploaded)
- Severity scoring and structured findings output
- Fix Prompts generation
- Quick review and single-file review
- Report generation (from in-context analysis)

**What does NOT work in Claude.ai:**
- `/codeprobe audit <path>` (no filesystem path to scan)
- Parallel agents (no subagent spawning)
- `scripts/dependency_mapper.py`, `complexity_scorer.py`, `file_stats.py` (no project filesystem)
- `/codeprobe diff` (no git repo access)
- Incremental reviews (no state between sessions)

**Orchestrator behavior in Claude.ai:**
- Auto-detects Claude.ai environment (no `claude` CLI, no subagent capability)
- Switches to sequential single-skill execution
- Skips script-dependent analysis steps
- Informs user of unavailable features without being verbose about it

**Practical usage in Claude.ai:**
```
User: "Review this code" + pastes 200-line file
→ Orchestrator detects language, runs relevant sub-skills sequentially
→ Outputs findings + fix prompts in chat

User: uploads 3 files
→ Orchestrator reads from /mnt/user-data/uploads/
→ Runs sub-skills across all uploaded files
→ Outputs consolidated findings
```

---

## 11. Implementation Phases

### Phase 1 — Core (MVP)
- Orchestrator skill (`codeprobe/SKILL.md`) with Claude.ai degraded-mode detection
- 4 sub-skills: `codeprobe-solid`, `codeprobe-security`, `codeprobe-code-smells`, `codeprobe-architecture`
- **All 6 reference files** (full stack coverage from day one)
- 1 script: `file_stats.py`
- Quick review + full audit report templates
- Fix Prompts generation in all output
- Sequential execution (no agents yet)
- `.codeprobe-config.json` schema for severity customization

### Phase 2 — Full Coverage
- Remaining 5 sub-skills: `codeprobe-patterns`, `codeprobe-performance`, `codeprobe-error-handling`, `codeprobe-testing`, `codeprobe-framework`
- All 4 scripts (`complexity_scorer.py`, `dependency_mapper.py`, `file_stats.py`, `generate_report.py`)
- PR review comment template

### Phase 3 — Parallel & Polish
- 4 parallel agents for `/codeprobe audit`
- `generate_report.py` for PDF output
- `/codeprobe diff` for git-based PR review
- SARIF/JSON output for CI integration
- Install/uninstall scripts
- README + docs

---

## 12. Non-Goals (Explicitly Out of Scope)

- **⛔ Modifying user code** — This skill is READ-ONLY. No writes, no edits, no side effects on the user's codebase. Ever. See §1 hard constraint.
- **Linting/formatting** — Use ESLint, PHP CS Fixer, Prettier for that. This skill operates above syntax.
- **Type checking** — Use TypeScript compiler, PHPStan, mypy. This skill assumes types are already checked.
- **Running tests** — This skill audits test quality, doesn't execute them.
- **Auto-fixing code** — This skill generates fix prompts, not rewrites. User decides when/how to apply.
- **Language-specific parsers** — No AST parsing. Sub-skills work via pattern recognition on source text.
- **Running build/install commands** — No `npm install`, `composer install`, `pip install`, `docker build`, etc.

---

## Next Steps

1. ✅ Spec reviewed — all open questions resolved
2. ✅ Name finalized — `codeprobe-claude`
3. Create GitHub repo `codeprobe-claude`
4. Build orchestrator (`codeprobe/SKILL.md`) with Claude.ai detection
5. Build first 4 sub-skills (solid, security, code-smells, architecture)
6. Write all 6 reference files
7. Test on StatusLink or YaariXI codebase
8. Write launch blog post on maketocreate.com targeting "claude code review skill" keyword
9. Iterate based on real findings
10. Build remaining 5 sub-skills (Phase 2)
11. Add parallel agents + reporting (Phase 3)
