# Expected Findings — `evals/fixture`

Defect map for the planted-defect fixture. Every defect below is intentional.
Use this to grade a `/codeprobe audit evals/fixture` run: the audit should find
each planted defect **in the expected severity bucket** (exact IDs and wording
will vary run to run; location + category + severity are what's graded).

Severity buckets follow the guardrails in `skills/codeprobe/SKILL.md` Section 6:
Critical is reserved for confirmed bugs, exploitable vulnerabilities, and data
loss/corruption — several defects below exist specifically to check the audit
does NOT over-escalate.

## Planted defects

| # | Location | Category | Expected severity | Defect |
|---|----------|----------|-------------------|--------|
| 1 | `fixture/app.py` — `search_reports()` | Security | **Critical** | SQL built with an f-string from the `name` request param — injectable as-is |
| 2 | `fixture/app.py` — `STRIPE_SECRET_KEY` | Security | **Critical** | Hardcoded live-style secret in source |
| 3 | `fixture/app.py` — `delete_order()` | Security | **Critical** | Data-mutating endpoint with no authentication |
| 4 | `fixture/app.py` — `login()` | Security | **Critical** | Password written to logs |
| 5 | `fixture/app.py` — `login()` | Security | Major | Plaintext password comparison against `password_hash` (no hashing) — arguably a confirmed auth bug; Critical also acceptable if evidenced |
| 6 | `fixture/orders.py` — `create_order()` | Error Handling | **Critical** | Four sequential writes (order, items, payment, inventory) with no transaction — partial-failure data corruption |
| 7 | `fixture/orders.py` — `notify_warehouse()` | Error Handling | Major | `except Exception: pass` — swallowed exception on an external call (also: no timeout → Major/Minor) |
| 8 | `fixture/orders.py` — `order_summaries()` | Performance | **Major, NOT Critical** | N+1: three queries per order inside the loop. Regression check for the v2.2.0 severity demotion |
| 9 | `fixture/models.py` ↔ `fixture/services.py` | Architecture | Major | Direct circular import (deterministically confirmed by `dependency_mapper.py`) |
| 10 | `fixture/manager.py` — `UserManager` | SOLID (SRP) / Architecture / Code Smells | **Major, NOT Critical** | God class: ~360 lines (323 LOC), 28 methods across auth, email, billing, notifications, profile, reporting, inventory, audit trail. Must survive as ONE primary finding after §7A dedup (SRP priority), with cross-references — regression check for dedup |
| 11 | `fixture/manager.py` — `plan_price()` / `dispatch_notification()` | SOLID (OCP) / Patterns | Major | if/elif chains on plan type and notification kind — growable variants, no extension point (patterns may recommend Strategy) |
| 12 | `fixture/manager.py` — `activity_report()` | Code Smells | Minor | Nesting depth > 3 (for → if → for → if) |
| 13 | `fixture/manager.py` — `activity_report()` | Performance | Minor/Major | Queries inside nested loops; unbounded cache (`report_cache`) with no TTL/invalidation |
| 14 | `fixture/manager.py` — `update_profile()` | Code Smells | Minor | Boolean blindness: 3 boolean params |
| 15 | `fixture/manager.py` — `update_profile()` | Security | Major | Column names interpolated into SQL from `fields` keys (mass-assignment-style vector) |
| 16 | `fixture/manager.py` — `merge_duplicate_accounts()` | Error Handling | **Critical** | Multi-step destructive writes (two UPDATEs + DELETE) without a transaction |
| 17 | `fixture/manager.py` — magic numbers | Code Smells | Minor | `86400`, `0.15`, `5`/`50`, `7` in logic paths without named constants |
| 18 | `fixture/models.py` — `User` | Architecture | Minor | Anemic model: only getters/setters, zero behavior |
| 19 | `fixture/utils.js` — `isSessionFresh()` / `findUser()` | Error Handling / Code Smells | Minor | Loose `==` comparisons; magic number `86400` |
| 20 | `fixture/utils.js` — `findUser()` | Performance | Minor/Major | `users.map().includes()` rebuilt inside a nested loop — O(n³)-ish linear search in loop |
| 21 | `fixture/utils.js` — lodash import | Performance | Minor | `import _ from "lodash"` full-library import for one function |
| 22 | `fixture/tests/test_orders.py` — both tests | Test Quality | **Major (ceiling)** | Tests with zero assertions; hardcoded ID `42`. Regression check: testing sub-skill must never exceed Major |

## Structural assertions (beyond individual findings)

- **Dedup:** the `UserManager` god class will be flagged by SOLID, Code Smells, and
  Architecture. After §7A, exactly one primary remains (SRP has priority for
  structural violations), the others are dropped (not demoted), and the primary
  carries an "Also flagged by:" cross-reference. Hot spots should rank
  `manager.py` first.
- **Severity ceilings:** zero Critical findings from Test Quality, Code Smells,
  Patterns, or Framework categories; no Critical for the file size itself.
- **Scoring:** Security and Error Handling category scores must reflect the
  planted criticals (each has 2+ criticals → `crit_penalty` capped at 50 →
  scores ≤ 50 before major/minor penalties).
- **Report artifact:** a report file appears at
  `./codeprobe-reports/fixture-audit-<timestamp>.md` and the terminal shows the
  dashboard + critical findings, not just the save line.
- **Read-only:** no fixture file is modified by the audit.
