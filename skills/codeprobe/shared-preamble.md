# Shared Sub-Skill Preamble

## READ-ONLY CONSTRAINT

**This sub-skill is strictly read-only. Never modify, write, edit, or delete any file in the user's codebase. Report findings only.**

---

## Output Contract

Every finding MUST include ALL of the following fields:

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | `{PREFIX}-{NNN}` — use the ID prefix specified by your sub-skill |
| `severity` | Yes | One of: `critical`, `major`, `minor`, `suggestion` |
| `severity_rationale` | Yes | One sentence explaining why this severity bucket and not the one below. See "How to write `severity_rationale`" below. |
| `location` | Yes | File path + line range (e.g., `src/UserService.php:45-67`) |
| `problem` | Yes | One sentence describing the issue |
| `evidence` | Yes | Concrete proof from the code — quote the relevant lines |
| `suggestion` | Yes | What to do to fix it |
| `fix_prompt` | Yes | A copy-pasteable prompt the user can give to Claude Code to apply the fix. Must reference specific file names, line ranges, method names, and the exact change to make. |
| `refactored_sketch` | No | Optional code snippet showing the improved version |

### Rendered Finding Format

```
### {ID} | {Severity} | `{file}:{lines}`

**Problem:** {problem description}

**Severity rationale:** {one sentence: why this bucket, not the one below}

**Evidence:**
> {quoted code patterns, specific variable names, line references}

**Suggestion:** {what to do to fix it}

**Fix prompt:**
> {copy-pasteable prompt for Claude Code}

**Refactored sketch:** (optional)
```

### How to write `severity_rationale`

A one-sentence justification of *why this severity, not the one below*. The format forces the reviewer to commit to a boundary call rather than picking a bucket by gut feel — this is the primary mechanism for keeping severity scoring stable across runs.

Rules:
- One sentence. No hedging ("could be either Major or Critical" is not allowed).
- Reference the specific signal that crossed the boundary (input source, blast radius, exploitability, scope of breakage), not a generic restatement of the problem.
- For Critical: state why Critical and not Major. Usually: confirmed exploit path, data loss path, or production crash on a core flow.
- For Suggestion (lowest level): state why Suggestion and not Minor. Usually: no real risk, purely a style/preference improvement.

Examples:
- **Critical:** "Critical (not Major) because user input flows directly into the SQL string with no parameterization — exploitable as-is via the public `POST /reports` endpoint."
- **Major:** "Major (not Minor) because the endpoint requires no auth and enables credential-stuffing; not Critical because rate-limiting at the load balancer partially mitigates."
- **Minor:** "Minor (not Major) because the magic number appears in a single internal helper with no callers depending on its specific value."
- **Suggestion:** "Suggestion (not Minor) because the pattern works fine today; the abstraction would only pay off if a second consumer appears."

---

## Execution Modes

### `full` Mode
Analyze the target path thoroughly. Produce detailed findings for every detected issue with all required fields. Include refactored_sketch for critical and major findings where it adds clarity.

### `scan` Mode
Run the same complete analysis as `full` mode, but trim the output: return (1) issue counts by severity, and (2) your **top 5 candidate findings** — the most impactful issues you found — each with ALL required output-contract fields (including `evidence` and `fix_prompt`). The orchestrator ranks candidates across all sub-skills to build a global top-5, so a candidate missing detail cannot be promoted into the final report. Do not return findings beyond your top 5.

---

## Summary Output

At the end of every execution (regardless of mode), provide a summary:

```json
{
  "skill": "{skill-name}",
  "summary": { "critical": 0, "major": 0, "minor": 0, "suggestion": 0 }
}
```

Replace the zeros with actual counts from the analysis.

---

## Source Files & References

The orchestrator provides a **file manifest** (paths + line counts + detected stacks) and the **paths** of applicable reference guides. Use Read, Grep, and Glob to inspect the source files relevant to your detection tables — you know your domain best, so target what matters (e.g., the security sub-skill prioritizes routes, controllers, config, and templates; the testing sub-skill prioritizes test directories and their subjects). Do not read every file blindly, but do not skip files your tables need either — an unread file is an unreviewed file.

Read the reference guide(s) relevant to your findings before finalizing severities and fix prompts.

**Degraded mode exception:** if the code was pasted or uploaded in-context (no filesystem), analyze the provided content directly — no manifest or Read calls involved.
