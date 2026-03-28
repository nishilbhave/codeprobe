---
name: probe-performance
description: >
  Scans code for performance and scalability issues — N+1 queries, missing indexes,
  unbounded queries, memory inefficiencies, caching gaps, algorithmic complexity,
  concurrency bugs, and frontend performance problems. Generates severity-scored
  findings with copy-pasteable fix prompts.
  Trigger phrases: "performance audit", "performance check", "N+1 detection", "query optimization", "slow code", "performance review".
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# Performance & Scalability Auditor

## READ-ONLY CONSTRAINT

**This sub-skill is strictly read-only. Never modify, write, edit, or delete any file in the user's codebase. Report findings only.**

---

## Domain Scope

This sub-skill detects performance and scalability issues across these categories:

1. **N+1 Queries** — Lazy-loading relationships inside loops
2. **Missing Indexes** — WHERE/ORDER BY on non-indexed columns
3. **Unbounded Queries** — Model::all() without pagination/limit
4. **Memory** — Loading entire files into memory, array accumulation in loops
5. **Caching** — Repeated identical queries, missing TTL, stale cache after writes
6. **Algorithmic Efficiency** — O(n^2) in hot paths, nested loops, sorting in loops
7. **Concurrency** — Race conditions, non-idempotent queue jobs, shared mutable state
8. **Frontend Performance** — Unnecessary re-renders, bundle size, missing lazy loading

---

## What It Does NOT Flag

- **Premature optimization in non-hot-path code** — proportional design matters. A utility function called once at startup doesn't need the same optimization as a request handler.
- **Development-only debug queries** — queries in seeders, dev-only commands, or debug endpoints.
- **Batch processing scripts** — scripts intentionally designed to process everything (migrations, data backfills) where unbounded queries may be appropriate.
- **O(n^2) on small bounded collections (<100 items)** — nested loops on small known-size arrays are fine.
- **Frontend SSR/build-time code** — server components and build scripts have different performance profiles than client-side code.

---

## Detection Instructions

### N+1 Queries

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `PERF` | Eloquent relationship access inside loop without eager loading | Search for `foreach`/`for` loops iterating over a collection, then accessing a relationship property (e.g., `$order->items`, `$user->profile`) inside the loop body. Check whether the query that produced the collection includes `with()` or `load()` for that relationship. | Critical |
| `PERF` | Any ORM lazy-loading inside iteration | Look for patterns where a database query is implicitly triggered inside a loop: Django querysets accessed per-iteration, SQLAlchemy lazy loads, Prisma relation access in `.map()`. | Critical |
| `PERF` | Template/view triggering queries | Blade templates, Jinja2 templates, or React components calling relationship properties that trigger queries during rendering. | Major |

### Missing Indexes

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `PERF` | WHERE/ORDER BY on non-indexed columns | Cross-reference query conditions (`where()`, `orderBy()`, `WHERE`, `ORDER BY`) with migration files or schema definitions to check for matching indexes. | Major |
| `PERF` | Foreign keys without indexes | Check migration files for `foreignId()`, `foreign()`, `references()` without corresponding index definitions. Most ORMs add these automatically, but raw migrations may miss them. | Minor |
| `PERF` | Composite queries needing compound indexes | Multiple `where()` conditions on different columns in the same query, or `where() + orderBy()` combinations that would benefit from a compound index. | Minor |

### Unbounded Queries

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `PERF` | `Model::all()` or `SELECT *` without limit | Search for `.all()`, `::all()`, `findAll()`, `SELECT * FROM` without `LIMIT`, `paginate()`, `take()`, or `limit()`. | Major |
| `PERF` | Missing cursor/chunk for large dataset processing | Operations that `get()` or load entire collections when processing large datasets. Should use `cursor()`, `chunk()`, `lazy()`, or equivalent streaming approach. | Major |

### Memory

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `PERF` | Loading entire files into memory | `file_get_contents()` on user uploads or large files, `fs.readFileSync()` on variable-size files, Python `open().read()` without size limits. | Major |
| `PERF` | Array accumulation in loops | Arrays that grow inside loops without bounds or cleanup — collecting results in memory that could be streamed or yielded. | Minor |
| `PERF` | Large collections instead of generators | Returning full arrays/lists where generators (`yield`), lazy collections, or iterators would be more memory-efficient for large datasets. | Minor |

### Caching

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `PERF` | Repeated identical queries in same request | Same query pattern executed multiple times within a single request/function call without caching the result. | Minor |
| `PERF` | Cache without TTL | `Cache::put()`, `cache.set()`, Redis SET without expiration. Data cached forever risks staleness. | Minor |
| `PERF` | Cache not invalidated after writes | Write operations (create/update/delete) that don't clear or update related cache entries. Stale cache served after mutation. | Major |

### Algorithmic Efficiency

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `PERF` | O(n^2) or worse in hot paths | Nested loops iterating over the same or related collections. `array_search`/`in_array`/`includes()` inside loops (linear search in a loop = O(n^2)). | Major |
| `PERF` | Sorting inside loops | `sort()`, `usort()`, `array_sort()`, `.sort()` called inside a loop body. | Major |
| `PERF` | Hashmap-replaceable linear search | `in_array()`, `.includes()`, `.indexOf()`, `list.index()` used repeatedly on the same array where building a Set/dict/hashmap first would be O(1) per lookup. | Minor |

### Concurrency

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `PERF` | Race conditions in read-modify-write | Patterns that read a value, modify it, and write back without locking: incrementing counters, updating balances, toggling flags in concurrent contexts. | Critical |
| `PERF` | Queue jobs without idempotency | Queue/job handlers that don't check for duplicate execution. Jobs that create resources without checking if already created. Missing unique constraints on job-created data. | Major |
| `PERF` | Shared mutable state in async contexts | Global/module-level mutable variables accessed in async handlers, request-scoped data stored in module scope. | Major |

### Frontend Performance

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `PERF` | Unnecessary re-renders | Missing `React.memo`, `useMemo`, `useCallback` on expensive computations or components receiving new object/array references on every render. Objects/arrays created inline in JSX props. | Minor |
| `PERF` | Large bundle imports | `import _ from 'lodash'` (imports entire library), `import moment from 'moment'` (large library where `date-fns` or `dayjs` suffice), `import * as icons from 'icon-library'`. | Minor |
| `PERF` | Missing lazy loading | No `React.lazy()` / dynamic `import()` for route-level code splitting. Heavy components loaded eagerly on initial page load. | Minor |

---

## Reference Loading

If the project uses a specific framework or language, load the relevant reference file from `../probe/references/{file}.md` using Read. Available references include:

- `sql-database.md` for N+1, index, and query optimization patterns
- `php-laravel.md` for Eloquent eager loading, caching, queue patterns
- `javascript-typescript.md` for async patterns, bundle optimization
- `react-nextjs.md` for component re-render optimization, SSR/SSG patterns

If the reference file is unavailable, continue the analysis without it.

### Optional Script Integration

When `scripts/complexity_scorer.py` output is available (run by the orchestrator during `/probe health` or `/probe audit`), use it to identify high-complexity functions as performance hot-spot candidates. Functions rated "high" or "very_high" that also appear in hot paths (request handlers, loop bodies, frequently-called utilities) are strong signals for algorithmic efficiency findings.

---

## Output Contract

Every finding MUST include ALL of the following fields:

```json
{
  "id": "PERF-{NNN}",
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

All findings use the `PERF-` prefix, numbered sequentially: `PERF-001`, `PERF-002`, `PERF-003`, etc.

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

- "In `OrderController@index` (line 22), add `->with('items', 'customer')` to the `Order::query()` call to fix the N+1 problem — currently loading 2 relations lazily inside the Blade loop at `orders/index.blade.php:15`."
- "Replace `Product::all()` at line 30 of `CatalogService.php` with `Product::query()->paginate(25)` or `Product::cursor()` if processing all records. The current query loads all products into memory."
- "In `ReportGenerator@aggregate` (lines 45-60), the nested loop iterating `$orders` inside `$customers` is O(n*m). Build a lookup hashmap before the outer loop: `$ordersByCustomerId = collect($orders)->groupBy('customer_id')`."
- "Replace `import _ from 'lodash'` at line 3 of `src/utils/helpers.ts` with specific imports: `import debounce from 'lodash/debounce'` to reduce bundle size."

---

## Execution Modes

This sub-skill supports three modes, set by the orchestrator:

### `full` Mode
Analyze the target path thoroughly. Scan every source file for all performance and scalability categories. Produce detailed findings for every detected issue with all required fields (id, severity, location, problem, evidence, suggestion, fix_prompt). Include refactored_sketch for critical findings. Trace query patterns, loop structures, and data flow where possible.

### `scan` Mode
Quick count of issues by severity. Identify the worst offenders (files with the most performance problems). Skip the `evidence` and `fix_prompt` fields. Return:
- Count of issues per category (N+1 Queries, Missing Indexes, Unbounded Queries, Memory, Caching, Algorithmic Efficiency, Concurrency, Frontend Performance)
- Count by severity (critical, major, minor, suggestion)
- Top 3 most problematic files with brief descriptions

### `score-only` Mode
Count issues by severity per category. Return only the summary counts — no individual findings, no evidence, no fix prompts. Output the summary object only.

---

## Summary Output

At the end of every execution (regardless of mode), provide a summary:

```json
{
  "skill": "probe-performance",
  "summary": { "critical": 0, "major": 0, "minor": 0, "suggestion": 0 }
}
```

Replace the zeros with actual counts from the analysis.
