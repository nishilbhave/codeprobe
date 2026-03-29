---
name: probe-framework
description: >
  Detects framework-specific anti-patterns, convention violations, and idiom misuse
  across PHP/Laravel, React/Next.js, and Python/Django/FastAPI codebases. Loads
  framework-specific reference guides and checks against framework conventions.
  Generates severity-scored findings with copy-pasteable fix prompts.
  Trigger phrases: "framework review", "framework check", "laravel best practices", "react best practices", "framework audit", "framework-specific review".
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# Framework-Specific Best Practices

## READ-ONLY CONSTRAINT

**This sub-skill is strictly read-only. Never modify, write, edit, or delete any file in the user's codebase. Report findings only.**

---

## Domain Scope

This sub-skill detects framework-specific anti-patterns and convention violations. Unlike other sub-skills that apply universal principles, this one loads framework-specific reference guides and checks against framework idioms.

**Supported frameworks:**

1. **PHP / Laravel** — Eloquent ORM, routing, validation, queues, events, configuration
2. **React / Next.js** — Component design, hooks, data fetching, type safety
3. **Python / Django / FastAPI** — PEP conventions, ORM patterns, async handling

**Important:** If no supported framework is detected at the target path, emit zero findings and return an empty summary with a note: "No supported framework detected — skipping framework-specific checks."

**Version Awareness:** When checking framework conventions, attempt to determine the framework version:

- **Laravel:** check `composer.json` for `laravel/framework` version. Laravel 9+ uses attribute-based accessors instead of `getXAttribute()`.
- **Next.js:** check `next.config.*` and `package.json` for Next.js version. 13+ uses App Router with `app/` directory.
- **Django:** check `requirements.txt` or `setup.py` for Django version.

---

## What It Does NOT Flag

- **Issues already covered by other sub-skills** even if they appear in framework code. Specifically:
  - Security issues in framework code → covered by `probe-security` (SEC)
  - SOLID violations in framework classes → covered by `probe-solid` (SRP/OCP/etc.)
  - Performance issues like N+1 queries → covered by `probe-performance` (PERF)
  - Error handling in framework middleware → covered by `probe-error-handling` (ERR)
- This sub-skill focuses exclusively on **framework idiom violations** — using the framework incorrectly or ignoring its conventions.
- **Framework-generated boilerplate files** (migration stubs, config defaults, scaffolded controllers).
- **Intentional deviations** from framework conventions with clear comments explaining the reason.
- **Test files** — test-specific framework usage has different conventions.

---

## Detection Instructions

### PHP / Laravel

| ID Prefix | Area | What to Detect | How to Detect | Severity |
|-----------|------|----------------|---------------|----------|
| `FWK` | Eloquent | Raw queries where Eloquent query builder works | Search for `DB::select()`, `DB::statement()`, raw SQL strings in model/service code where Eloquent's query builder (`where()`, `join()`, `whereHas()`) would be cleaner and safer. Exclude complex reporting queries that genuinely need raw SQL. | Minor |
| `FWK` | Eloquent | Missing `$casts` on model | Model attributes that should be cast (dates, booleans, arrays, JSON) accessed without `$casts` definition. Look for manual casting in accessors or repeated `(bool)`, `(int)`, `json_decode()` on model attributes. | Minor |
| `FWK` | Eloquent | Repeated WHERE conditions without scopes | Same `where()` condition chain used in 3+ locations on the same model. Should be extracted into a named scope (`scopeActive()`, `scopePublished()`). | Minor |
| `FWK` | Routing | Logic in route closures instead of controllers | Route definitions in `routes/web.php` or `routes/api.php` with closure handlers exceeding 3 lines. Should be moved to controller methods. | Minor |
| `FWK` | Routing | Missing route model binding | Routes that accept an ID parameter and manually call `Model::find($id)` or `Model::findOrFail($id)` instead of using route model binding in the method signature. | Minor |
| `FWK` | Validation | Validation in controller instead of Form Request | Controller methods with inline validation rules (`$request->validate([...])` exceeding 5 rules). Should use a dedicated Form Request class. | Minor |
| `FWK` | Queues | Long-running tasks in request cycle | Operations likely to take > 5 seconds (sending emails, generating PDFs, calling external APIs, processing uploads) executed synchronously in a controller/request handler. Should be dispatched to a queue. | Major |
| `FWK` | Queues | Queue jobs without retry configuration | Job classes missing `$tries`, `$timeout`, or `$backoff` properties. Jobs will retry indefinitely on failure without these. | Minor |
| `FWK` | Events | Tight coupling where events would decouple | After a state change (create, update, delete), a method directly calls 3+ other services. Should dispatch an event and let listeners handle side effects. | Minor |
| `FWK` | Config | `env()` called outside config files | Using `env()` helper directly in service classes, controllers, or blade templates. `env()` returns `null` when config is cached. Must be wrapped in a `config/` file. | Major |

### React / Next.js

| ID Prefix | Area | What to Detect | How to Detect | Severity |
|-----------|------|----------------|---------------|----------|
| `FWK` | Components | Components exceeding 200 LOC | Single component files with more than 200 lines of code. Should be decomposed into smaller, focused components. | Minor |
| `FWK` | Components | Prop drilling more than 3 levels deep | Props passed through 3+ intermediate components that don't use them. Should use Context, state management, or composition. Trace prop names through component hierarchy. | Minor |
| `FWK` | Hooks | `useEffect` with missing or incorrect dependency array | `useEffect` hooks where variables used inside the effect are not listed in the dependency array. Also flag `useEffect` with empty `[]` that references props/state that can change. | Major |
| `FWK` | Hooks | State updates inside render | Calling `setState`/state setter outside of event handlers or effects — directly in the component body during render, causing infinite re-render loops. | Major |
| `FWK` | Hooks | Custom hooks exceeding 50 LOC | Custom hooks that do too much. Should be composed from smaller hooks. | Minor |
| `FWK` | Data Fetching | Client-side fetch where SSR/SSG is appropriate | `useEffect` + `fetch()` for data that is available at build time or request time. In Next.js, should use `getServerSideProps`, `getStaticProps`, or server components. | Minor |
| `FWK` | Data Fetching | Missing error and loading states | Data fetching without corresponding loading indicator and error handling in the UI. | Minor |
| `FWK` | Type Safety | `any` type usage in TypeScript | Explicit `any` type annotations in `.tsx`/`.ts` files. Should use proper types, `unknown`, or generics. | Minor |
| `FWK` | Type Safety | Missing return types on exported functions | Exported functions without explicit return type annotations. Rely on inference for internal, but exported API surfaces should be explicitly typed. | Minor |

### Python / Django / FastAPI

| ID Prefix | Area | What to Detect | How to Detect | Severity |
|-----------|------|----------------|---------------|----------|
| `FWK` | Django | `views.py` exceeding 500 LOC | Single view module with too many views. Should be split into separate view modules or use ViewSets. | Minor |
| `FWK` | Django | Missing model `Meta` class | Django models without `Meta` class for ordering, verbose names, or constraints. | Minor |
| `FWK` | Django | N+1 in templates | Template tags accessing related objects without `select_related()`/`prefetch_related()` in the view. | Major |
| `FWK` | FastAPI | Sync database calls in async views | Using synchronous ORM calls (Django ORM, SQLAlchemy sync) inside `async def` view functions. Blocks the event loop. | Major |
| `FWK` | Python | Non-PEP 8 naming | `camelCase` for functions/variables (should be `snake_case`), `snake_case` for classes (should be `PascalCase`). | Minor |

---

## Reference Loading

This sub-skill relies heavily on reference files. Load the detected framework's reference from `../probe/references/{file}.md` using Read. Available references include:

- `php-laravel.md` for Laravel projects — Eloquent patterns, service container, facades
- `react-nextjs.md` for React/Next.js projects — component patterns, hooks rules, rendering strategies
- `javascript-typescript.md` for general JS/TS projects — module patterns, async pitfalls
- `python.md` for Python/Django/FastAPI projects — PEP standards, ORM patterns

**If no reference file is available for the detected framework, continue with the detection rules above only.** The reference files enrich but are not required.

---

## Output Contract

Every finding MUST include ALL of the following fields:

```json
{
  "id": "FWK-{NNN}",
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

All findings use the `FWK-` prefix, numbered sequentially: `FWK-001`, `FWK-002`, `FWK-003`, etc.

### Rendered Finding Format

```
### {ID} | {Severity} | `{file}:{lines}`

**Problem:** {problem description}

**Evidence:**
> {quoted code patterns, specific variable names, line references, data flow description}

**Suggestion:** {what to do to fix it}

**Fix prompt:**
> {copy-pasteable prompt for Claude Code}

**Refactored sketch:** (optional)
```

### Fix Prompt Examples

- "Move the validation rules from `OrderController@store` (lines 15-30) into a new `StoreOrderRequest` form request class: run `php artisan make:request StoreOrderRequest`, move the validation array, and type-hint `StoreOrderRequest` in the controller method signature."
- "Replace the `env('MAIL_HOST')` call at line 12 of `app/Services/MailService.php` with `config('mail.mailers.smtp.host')`. The `env()` function returns `null` when the config is cached. Move the env lookup to `config/mail.php` where it belongs."
- "The `ProductList` component at `src/components/ProductList.tsx` (220 LOC) should be decomposed: extract `ProductCard` (lines 50-90), `ProductFilters` (lines 100-140), and `ProductPagination` (lines 160-200) into separate components in the same directory."
- "Add missing dependency `userId` to the `useEffect` dependency array at `src/hooks/useProfile.ts:15`. The current empty array `[]` means the effect runs once with the initial `userId` and never refetches when it changes."

---

## Execution Modes

This sub-skill supports three modes, set by the orchestrator:

### `full` Mode
Analyze the target path thoroughly. Scan every source file for all framework-specific convention violations. Produce detailed findings for every detected issue with all required fields (id, severity, location, problem, evidence, suggestion, fix_prompt). Include refactored_sketch for major findings. Load framework reference files and cross-check against documented idioms.

### `scan` Mode
Quick count of violations by severity. Identify the worst offenders (files with the most framework anti-patterns). Skip the `evidence` and `fix_prompt` fields. Return:
- Count of violations per framework section (PHP/Laravel, React/Next.js, Python/Django/FastAPI)
- Count by severity (critical, major, minor, suggestion)
- Top 3 most problematic files with brief descriptions

### `score-only` Mode
Count violations by severity per framework section. Return only the summary counts — no individual findings, no evidence, no fix prompts. Output the summary object only.

---

## Summary Output

At the end of every execution (regardless of mode), provide a summary:

```json
{
  "skill": "probe-framework",
  "summary": { "critical": 0, "major": 0, "minor": 0, "suggestion": 0 }
}
```

Replace the zeros with actual counts from the analysis.
