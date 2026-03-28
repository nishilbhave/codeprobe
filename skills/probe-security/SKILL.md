---
name: probe-security
description: >
  Scans code for security vulnerabilities — injection flaws, authentication gaps,
  XSS vectors, mass assignment, CSRF, insecure deserialization, sensitive data exposure,
  broken access control, and misconfigurations. Generates severity-scored findings
  with copy-pasteable fix prompts.
  Trigger phrases: "security scan", "security audit", "vulnerability check", "find security issues".
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# Security Vulnerability Scanner

## READ-ONLY CONSTRAINT

**This sub-skill is strictly read-only. Never modify, write, edit, or delete any file in the user's codebase. Report findings only.**

---

## Domain Scope

This sub-skill detects security vulnerabilities across these categories:

1. **Injection** — SQL injection, command injection, LDAP/NoSQL injection
2. **Authentication & Authorization** — Missing auth, weak credentials, hardcoded secrets, JWT issues
3. **Cross-Site Scripting (XSS)** — Unescaped output, dangerous HTML rendering
4. **Mass Assignment** — Unprotected model attribute assignment
5. **Cross-Site Request Forgery (CSRF)** — Missing tokens, unprotected state-changing routes
6. **Insecure Deserialization** — Unsafe deserialization of untrusted data
7. **Sensitive Data Exposure** — Secrets in logs, committed .env files, leaked stack traces
8. **Broken Access Control** — IDOR, missing policy/gate checks
9. **Security Misconfiguration** — Debug mode in production, permissive CORS, default credentials

---

## What It Does NOT Flag

- **Internal admin tools** with IP-restricted access — these have a different threat model and the restriction may be intentional.
- **Test files** using hardcoded values — test fixtures with fake credentials, tokens, and API keys are expected and appropriate.
- **Development-only configuration files** clearly marked as such (e.g., `.env.example`, `docker-compose.dev.yml`, files in `tests/fixtures/`).
- **Dependencies with known CVEs** — this sub-skill analyzes source code, not dependency manifests. Use dedicated tools (e.g., `npm audit`, `composer audit`) for dependency scanning.

---

## Detection Instructions

### Injection

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `SEC` | Raw SQL with string concatenation/interpolation | Search for SQL keywords (`SELECT`, `INSERT`, `UPDATE`, `DELETE`, `WHERE`) combined with string concatenation (`.`, `+`, `f"`, `${}`, `"${`), template literals, or variable interpolation. Check that user input flows into the query string without parameterization. | Critical |
| `SEC` | `DB::raw()` / raw queries with user input | Search for `DB::raw()`, `DB::select(DB::raw(`, `knex.raw()`, `sequelize.literal()`, `cursor.execute(f"` and similar raw query methods. Flag when the argument contains variables that could originate from user input (request params, form data, query strings). | Critical |
| `SEC` | Shell command construction with unsanitized input | Search for `exec()`, `system()`, `shell_exec()`, `popen()`, `subprocess.call()`, `subprocess.run()`, `child_process.exec()`, backtick operators. Flag when the command string includes variables from user input without escaping or allowlist validation. | Critical |
| `SEC` | LDAP/NoSQL injection vectors | Search for LDAP filter construction with string concatenation, MongoDB query construction with user input in `$where`, `$regex`, or other operators that accept arbitrary expressions. | Critical |

### Authentication & Authorization

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `SEC` | Missing auth middleware on routes that modify data | Scan route definitions (e.g., `Route::post()`, `router.post()`, `@app.post()`) for POST/PUT/PATCH/DELETE endpoints. Check whether auth middleware is applied. Flag routes that modify data without any authentication layer. | Critical |
| `SEC` | Role checks done in view/frontend but not backend | Search for role/permission checks in frontend templates or JavaScript (e.g., `v-if="user.isAdmin"`, `{user.role === 'admin' && ...}`) and verify that the corresponding backend endpoint also enforces the check. If backend lacks it, flag. | Major |
| `SEC` | Hardcoded secrets/API keys in source code | Search for patterns: `api_key = "..."`, `secret = '...'`, `password = "..."`, `token = '...'`, `AWS_SECRET`, `STRIPE_KEY`, bearer tokens, and similar. Exclude `.env.example` files and test fixtures. Check for high-entropy strings assigned to variables with secret-like names. | Critical |
| `SEC` | Weak password policy | Look for user registration/password-change logic. Check whether password validation enforces minimum length (8+ chars), complexity, or uses a validation library. Flag if passwords are accepted without any validation rules. | Major |
| `SEC` | JWT without expiration | Search for JWT creation/signing code. Check whether the payload includes an `exp` (expiration) claim. Flag JWTs created without expiration or with excessively long expiration (> 24 hours for access tokens). | Major |

### Cross-Site Scripting (XSS)

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `SEC` | `{!! !!}` (unescaped output) in Laravel Blade with user data | Search for `{!! ... !!}` in `.blade.php` files. Check whether the content inside originates from user input, database fields that store user-provided HTML, or request data. Exclude static content and trusted admin-only fields. | Major |
| `SEC` | `dangerouslySetInnerHTML` in React with untrusted data | Search for `dangerouslySetInnerHTML` in `.jsx`/`.tsx` files. Check whether the `__html` value comes from user input, API responses without sanitization, or any source not explicitly sanitized with DOMPurify or equivalent. | Major |
| `SEC` | `v-html` in Vue with untrusted data | Search for `v-html` directives in `.vue` files. Same analysis as above — flag when the bound value could contain unsanitized user input. | Major |
| `SEC` | Missing Content-Security-Policy | Check for CSP headers in middleware, web server config, or meta tags. If no CSP is configured anywhere in the project, flag as a defense-in-depth gap. | Minor |

### Mass Assignment

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `SEC` | Laravel model without `$fillable` or `$guarded` | Search for Eloquent model classes (extending `Model`). Check whether each model defines either `$fillable` (allowlist) or `$guarded` (blocklist) property. Flag models that define neither. | Major |
| `SEC` | Accepting `$request->all()` into create/update | Search for `$request->all()`, `request.body` (without destructuring), `**request.data` passed directly into `Model::create()`, `Model::update()`, `Model::fill()`, or ORM create/update methods. Flag as mass assignment vector. | Critical |

### Cross-Site Request Forgery (CSRF)

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `SEC` | Forms without CSRF tokens | Search for `<form` tags with `method="POST"` (or PUT/PATCH/DELETE). Check whether the form includes a CSRF token field (`@csrf`, `csrf_token()`, `csrfmiddlewaretoken`, `_token`). Flag forms missing tokens. | Major |
| `SEC` | API routes without proper auth that modify state | Check API routes (POST/PUT/PATCH/DELETE) that lack both CSRF protection AND authentication middleware. Stateless APIs with token auth are fine; session-based APIs without CSRF tokens are not. | Major |

### Insecure Deserialization

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `SEC` | `unserialize()` on user input | Search for `unserialize()` (PHP), `pickle.loads()` (Python), `ObjectInputStream` (Java), `Marshal.load` (Ruby). Flag when the input source is user-controlled (request body, cookies, query params, uploaded files). | Critical |
| `SEC` | `JSON.parse()` without validation used in eval-like context | Search for `JSON.parse()` of external data where the parsed result is passed to `eval()`, `Function()`, `setTimeout(string)`, or used to construct code dynamically. Flag the eval-like usage, not JSON.parse itself. | Major |

### Sensitive Data Exposure

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `SEC` | Passwords/tokens in log statements | Search for logging calls (`Log::`, `logger.`, `console.log`, `print`, `logging.`) that include variables named `password`, `token`, `secret`, `key`, `credential`, `auth`, or similar. Flag when sensitive data is written to logs. | Critical |
| `SEC` | `.env` committed to git | Check whether `.gitignore` includes `.env`. If `.env` exists in the repository and is not gitignored, flag as critical. Also check for `.env.production`, `.env.staging` committed. | Critical |
| `SEC` | Secrets in config files vs environment variables | Search config files for hardcoded credentials, API keys, database passwords. Flag values that should come from environment variables but are instead hardcoded in tracked config files. | Major |
| `SEC` | Error messages leaking stack traces in production config | Check error/exception handling configuration. Look for `APP_DEBUG=true`, `DEBUG=True`, `display_errors=On`, or custom error handlers that expose stack traces, file paths, or SQL queries in responses. Flag when this is in production config. | Major |

### Broken Access Control

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `SEC` | IDOR — using user-supplied ID without ownership check | Search for route parameters or request params (e.g., `$request->id`, `params.id`, `request.args.get('id')`) used to fetch resources without verifying the authenticated user owns the resource. Look for `Model::find($id)` without a `where('user_id', auth()->id())` or policy check. | Critical |
| `SEC` | Missing policy/gate checks on resource access | In frameworks with authorization systems (Laravel policies, Django permissions, Express middleware), check whether CRUD operations on user-owned resources include authorization checks. Flag controller actions that read/modify resources without policy or permission verification. | Major |

### Security Misconfiguration

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|---------------|---------------|----------|
| `SEC` | `APP_DEBUG=true` in production configs | Search for `APP_DEBUG=true`, `DEBUG=True`, `debug: true` in configuration files that appear to be production configs (not `.env.example` or `.env.local`). | Major |
| `SEC` | Permissive CORS | Search for CORS configuration. Flag `Access-Control-Allow-Origin: *` or `allowed_origins: ['*']` in non-public-API contexts. Also flag `Access-Control-Allow-Credentials: true` combined with wildcard origins. | Major |
| `SEC` | Default credentials in configuration | Search for usernames like `admin`, `root`, `test` paired with passwords like `password`, `123456`, `admin`, `secret`, `changeme` in config files, seeders, or initialization code. Exclude test fixtures. | Critical |

---

## Reference Loading

If the project uses a specific framework or language, load the relevant reference file from `../probe/references/{file}.md` using Read. Available references include:

- `php-laravel.md` for PHP/Laravel projects (mass assignment, Blade XSS, middleware patterns)
- `javascript-typescript.md` for JS/TS projects (XSS in React/Vue, prototype pollution)
- `python.md` for Python projects (pickle deserialization, Django/FastAPI security)
- `react-nextjs.md` for React/Next.js projects (dangerouslySetInnerHTML, API route security)

If the reference file is unavailable, continue the analysis without it.

---

## Output Contract

Every finding MUST include ALL of the following fields:

```json
{
  "id": "SEC-{NNN}",
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

All findings use the `SEC-` prefix, numbered sequentially: `SEC-001`, `SEC-002`, `SEC-003`, etc.

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

- "In `UserController@update` (line 34), replace `$request->all()` with `$request->only(['name', 'email'])` to prevent mass assignment on the `is_admin` field. Also add `$fillable = ['name', 'email']` to the `User` model if not already present."
- "Wrap the user input at line 55 of `app/Services/SearchService.php` in a parameterized query: change `DB::select(\"SELECT * FROM products WHERE name LIKE '%$search%'\")` to `DB::select('SELECT * FROM products WHERE name LIKE ?', [\"%{$search}%\"])`."
- "In `routes/api.php`, add auth middleware to the `POST /api/orders` route at line 22: change `Route::post('/orders', [OrderController::class, 'store'])` to `Route::post('/orders', [OrderController::class, 'store'])->middleware('auth:sanctum')`."
- "Move the hardcoded API key at line 15 of `config/services.php` to an environment variable: replace `'key' => 'sk-live-abc123...'` with `'key' => env('STRIPE_SECRET_KEY')` and add `STRIPE_SECRET_KEY=` to `.env.example`."

---

## Execution Modes

This sub-skill supports three modes, set by the orchestrator:

### `full` Mode
Analyze the target path thoroughly. Scan every source file for all security vulnerability categories. Produce detailed findings for every detected vulnerability with all required fields (id, severity, location, problem, evidence, suggestion, fix_prompt). Include refactored_sketch for critical findings. Trace data flow from user input to dangerous sinks where possible.

### `scan` Mode
Quick count of vulnerabilities by severity. Identify the worst offenders (files with the most security issues). Skip the `evidence` and `fix_prompt` fields. Return:
- Count of vulnerabilities per category (Injection, Auth, XSS, Mass Assignment, CSRF, Deserialization, Data Exposure, Access Control, Misconfiguration)
- Count by severity (critical, major, minor, suggestion)
- Top 3 most vulnerable files with brief descriptions

### `score-only` Mode
Count vulnerabilities by severity per category. Return only the summary counts — no individual findings, no evidence, no fix prompts. Output the summary object only.

---

## Summary Output

At the end of every execution (regardless of mode), provide a summary:

```json
{
  "skill": "probe-security",
  "summary": { "critical": 0, "major": 0, "minor": 0, "suggestion": 0 }
}
```

Replace the zeros with actual counts from the analysis.
