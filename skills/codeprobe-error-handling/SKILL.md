---
name: codeprobe-error-handling
description: >
  Scans code for error handling and resilience issues — swallowed exceptions, missing
  try/catch on external calls, unhandled promise rejections, missing transactions,
  validation gaps, retry/timeout omissions, and logging blind spots. Generates
  severity-scored findings with copy-pasteable fix prompts.
  Trigger phrases: "error handling check", "exception audit", "resilience check", "try/catch review", "error handling audit".
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

## Standalone Mode

If invoked directly (not via the orchestrator), you must first:
1. Read `../codeprobe/shared-preamble.md` (resolve relative to this SKILL.md's location — the sibling `codeprobe` skill directory — not the user's project) for the output contract, execution modes, and constraints.
2. Load applicable reference files from `../codeprobe/references/` (same resolution) based on the project's tech stack.
3. Default to `full` mode unless the user specifies otherwise.

# Error Handling & Resilience Checker

## Domain Scope

This sub-skill detects error handling and resilience issues across these categories:

1. **Swallowed Exceptions** — Empty catch blocks, catch-and-log-only without rethrow/handle
2. **Missing Error Handling** — External API calls without try/catch, unhandled promise rejections
3. **Error Information** — Generic error messages, leaking internals, missing structured responses
4. **Retry & Circuit Breaker** — No timeout on external calls, no retry for transient failures
5. **Validation** — Missing input validation, implicit null assumptions, type coercion bugs
6. **Transaction Safety** — Multi-step DB operations without transactions, missing rollback
7. **Logging** — No logging on critical paths, missing correlation IDs

---

## What It Does NOT Flag

- **Sensitive data in logs** — covered by `codeprobe-security` (`SEC` prefix). This sub-skill flags *missing* logging and *structural* issues like no correlation IDs, not data leakage.
- **Test files** — test exception handling follows different patterns and is expected to be simpler.
- **Framework-generated exception handlers** (e.g., Laravel's `Handler.php`, Next.js error boundaries that are intentionally minimal) — these are scaffolded defaults, not developer oversights.
- **CLI scripts with intentionally simple error handling** (print + exit) — command-line tools often use a valid pattern of printing an error and exiting with a non-zero code.
- **Catch blocks that deliberately swallow specific known-harmless exceptions** with a comment explaining why — if the developer documented the rationale, respect the decision.
- **Issues that are primarily security vulnerabilities** (e.g., authentication bypasses, injection, data exposure) even if they also have error handling implications — these are covered by `codeprobe-security`. If both sub-skills flag the same location, the orchestrator will deduplicate and keep the security finding as primary.

---

## Detection Instructions

### Swallowed Exceptions

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `ERR` | Empty catch blocks | Search for `catch` blocks with empty body, only `pass`, only `// ignored`, or only a comment. In JS/TS: `catch (e) {}`. In PHP: `catch (\Exception $e) {}`. In Python: `except: pass` or `except Exception: pass`. | Major |
| `ERR` | Catch-log-only without handling | Find catch blocks that only contain a log/print statement but don't rethrow, return an error, or take any recovery action. The exception is swallowed after logging. | Minor |
| `ERR` | Overly broad exception catching | `catch (\Exception $e)`, `catch (Exception e)`, bare `except:` in Python, `catch (e)` catching all errors. Flag when a more specific exception type should be caught. | Major |

### Missing Error Handling

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `ERR` | External API calls without try/catch | Search for HTTP client calls (Guzzle, axios, fetch, requests, HttpClient), payment SDK calls (Stripe, PayPal), AWS SDK calls, and other external service integrations. Flag when these calls are NOT wrapped in try/catch or .catch(). | Major |
| `ERR` | Unhandled promise rejections | Search for async functions or promise chains without `.catch()` or surrounding try/catch. Look for floating promises (async call without await). In Node.js, check for missing `unhandledRejection` handler. | Major |
| `ERR` | File I/O without error handling | `file_get_contents`, `fopen`, `fs.readFile`, `open()` (Python) without try/catch for IOError/FileNotFoundError. | Minor |

### Error Information

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `ERR` | Generic error messages | API responses returning only "Something went wrong", "Internal server error", or similar without error codes or actionable detail for the client. | Minor |
| `ERR` | Leaking internal errors to API consumers | Exception messages, stack traces, SQL errors, or file paths exposed in API JSON/HTML responses. Check error handling middleware configuration. | Major |
| `ERR` | Missing structured error responses | API endpoints returning errors without consistent structure (no error code field, no message field, inconsistent formats across endpoints). | Minor |

### Retry & Circuit Breaker

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `ERR` | External service calls without timeout | HTTP client calls without timeout configuration. Guzzle without `timeout` option, axios without `timeout`, requests without `timeout` param, fetch without AbortController. | Major |
| `ERR` | No retry for transient failures | External API calls that could fail transiently (HTTP 429, 503, network errors) with no retry mechanism. | Minor |
| `ERR` | No circuit breaker for cascading failures | Service-to-service calls in microservice architectures with no circuit breaker or fallback pattern. | Suggestion |

### Validation

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `ERR` | Missing input validation before processing | Functions that accept external input (request params, file contents, API payloads) and use them directly without validation. | Major |
| `ERR` | Implicit null assumptions | Accessing properties or calling methods on values that could be null/undefined without null checks. Chaining `.` access on possibly-null return values. | Minor |
| `ERR` | Type coercion bugs | PHP `==` instead of `===` for security-sensitive comparisons. JS `==` instead of `===`. Implicit type conversions that could produce unexpected results. | Minor |

### Transaction Safety

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `ERR` | Multi-step DB ops without transactions | Multiple `INSERT`/`UPDATE`/`DELETE` queries in sequence (same method) without `DB::transaction()`, `atomic()`, `BEGIN`/`COMMIT`, or equivalent. If any step fails, data is left in an inconsistent state. | Critical |
| `ERR` | Transaction without proper rollback | Transaction blocks that catch exceptions but don't rollback, or that have code after the transaction that assumes success without checking. | Major |

### Logging

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `ERR` | No logging on critical failure paths | Catch blocks in critical business logic (payment, auth, order processing) that don't include any logging. Failures happen silently. | Major |
| `ERR` | Missing correlation/request IDs | Log statements in request-handling code without correlation ID, request ID, or trace ID. Makes debugging distributed issues impossible. | Minor |

---

## ID Prefix & Fix Prompt Examples

All findings use the `ERR-` prefix, numbered sequentially: `ERR-001`, `ERR-002`, etc.

### Fix Prompt Examples

- "Wrap the Stripe API call in `PaymentService@charge` (line 55) in a try/catch for `\Stripe\Exception\ApiErrorException`. Log the error with context (`$orderId`, `$amount`) and throw a domain-specific `PaymentFailedException` with a user-friendly message."
- "Add `DB::transaction()` around the order creation flow in `OrderService@create` (lines 40-65) which currently creates an Order, OrderItems, and Payment record in three separate queries. If any step fails, all should roll back."
- "Replace the empty catch block at `app/Services/NotificationService.php:88` with proper error handling: log the exception with notification context, then decide whether to rethrow (critical notification) or swallow with a metric (non-critical)."
- "Add timeout and retry configuration to the HTTP client call at `ExternalApiClient.php:30`. Use `->timeout(10)->retry(3, 100)` for the Guzzle request to handle transient network failures."
