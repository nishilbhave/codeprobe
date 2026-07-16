# Feedback Gaps

A running log of gaps in codeprobe that surfaced from user feedback. Each entry captures the source, the problem, the options on the table, and the current decision posture. **Nothing here is committed work** — this doc exists so we can decide later without re-discovering the context.

When a gap is closed (shipped, declined, or rolled into another change), move it to the bottom under **Closed**.

---

## Open

### Gap 2 — Intent / spec review (the "wrong thing built well" problem)

**Source:** dev.to comment on [the multi-agent code review post](https://dev.to/nishilbhave/i-built-a-multi-agent-code-review-skill-for-claude-code-heres-how-it-works-366i), 2026-05. (Commenter handle: TODO)
> "An agent that builds the wrong thing well is going to pass a multi-agent review of that wrong thing. The reviewers will check the SOLID-ness of the wrong abstraction, the security of the wrong endpoint, the test coverage of the wrong behavior… ~40% the agent built almost the right thing — wrong abstraction, wrong scope, fine code; ~20% the agent built the wrong thing entirely because the plan was bad."

**Problem:** codeprobe is strictly post-implementation. The reviewers will diligently audit the SOLID-ness of the wrong abstraction without ever flagging that it's the wrong abstraction. The commenter's 40/40/20 split (right-thing-sloppy / almost-right-thing / wrong-thing) implies codeprobe catches at most 40% of "almost right" failures. The remaining 60% is upstream — in the plan, not the code.

**Options:**

1. **Document as out of scope (cheapest).** Add a short README section: "codeprobe is post-implementation by design. Intent review is deliberately a different problem." Turns a perceived gap into an explicit scope decision. Zero shipping risk. Doesn't actually solve the failure mode.
2. **Intent-aware audit inside codeprobe.** Operator passes intent as input via `/codeprobe audit . --intent "..."` or a `.codeprobe-intent.md` file at repo root. New `codeprobe-intent-fit` sub-skill checks whether produced code matches stated intent. If no intent provided, codeprobe runs as today (no change to default UX). Catches bucket 2 (wrong abstraction) without disrupting workflow. Does not catch bucket 3 (operator was wrong about what to build).
3. **Separate planner tool (`specprobe` or similar).** Pre-implementation review of the spec itself: clarity, scope, fit-with-existing-code, testability of the spec. Runs *before* code is written. Different surface, different sub-skills, different output (gate decision rather than severity scores). Catches all three buckets but is a much bigger build and a different product.

**Status:** Not decided. Option 1 is free and worth doing regardless of whether we build 2 or 3. Option 2 is the smallest real solve and fits inside the existing skill. Option 3 is a separate product that may or may not be worth pursuing — depends on whether demand surfaces.

Open questions before committing to 2:
- How specific does intent need to be for the reviewer to use it usefully? ("clean code" gives zero signal; "simple user CRUD, no caching" gives a lot.)
- Do users actually want to write intent down, or will the field stay empty in practice?

---

### Gap 3 — Cross-sub-skill disagreement policy

**Source:** Same commenter as Gap 1 — the broader version of the question.
> "do you let them argue, or does the orchestrator just present both?"

**Problem:** codeprobe has no explicit policy for what happens when sub-skills disagree. Today the answer is "the orchestrator's §7A dedup logic picks a winner by category priority and demotes the loser to a suggestion." That works for overlap, fails for genuine disagreement (Gap 1), and is silent about other disagreement shapes:
- One sub-skill flags a finding, another deliberately skipped it because of a known exception (e.g., test fixture).
- Two sub-skills assign different severities to the same finding.
- Sub-skill A says "missing test for X," sub-skill B says "X is intentionally untested utility code."

**Options:**

1. **Status quo: implicit policy via priority order.** Keep the §7A dedup logic, ship per-case fixes (e.g., Gap 1's conflict section) as they come up. Pragmatic, accumulates technical debt as edge cases pile up.
2. **Explicit disagreement policy section in `codeprobe/SKILL.md`.** Write down the rules for each disagreement shape: opposite recommendations → conflict section; severity mismatch → take the higher; suppression overrides finding → skip silently with a debug note. Forces the design choices to be explicit, makes future contributions easier to reason about.
3. **Sub-skills emit confidence scores; orchestrator weights them.** Each finding includes a confidence rating; conflicts resolved by weighted vote. More principled but adds a field to the contract and assumes sub-skills can self-assess confidence (they often can't).

**Status:** Partially addressed in v2.2.0 — the opposite-recommendations rule is now explicit in §7A (conflicts skip dedup and render in a "Conflicting Recommendations" section; see Gap 1 under Closed). The other disagreement shapes (severity mismatch between sub-skills, suppression-vs-finding, "missing test" vs "intentionally untested") remain undecided. Option 2 (a full disagreement-policy section) is still the likely next step once we see which shapes show up in real audits.

**Related:** Gap 1 (Closed) was the concrete instance that forced the first rule into the open.

---

## Closed

### Gap 1 — Conflicting Recommendations between sub-skills *(shipped, v2.2.0 — 2026-07-16)*

**Source:** dev.to comment on [the multi-agent code review post](https://dev.to/nishilbhave/i-built-a-multi-agent-code-review-skill-for-claude-code-heres-how-it-works-366i), 2026-05. (Commenter handle: TODO)
> "when two domain experts disagree (e.g., the SOLID reviewer wants an abstraction the performance reviewer flags as overhead), do you let them argue, or does the orchestrator just present both? We've gone back and forth on that one."

**Problem (as logged):** When two sub-skills emit *opposite recommendations* at the same location, the §7A dedup logic silently picked a winner and demoted the loser to a suggestion — designed for "same issue, different lens," misapplied to genuine disagreement.

**What shipped:** A minimal version of Option 1 (detect-and-present), without the curated pair table. §7A now checks each overlap group for opposing recommendations *before* dedup'ing; conflicts keep both findings at full severity and render in a "Conflicting Recommendations" section of the audit report (new block in `templates/full-audit-report.md`) with a one-line tradeoff note. Detection relies on the orchestrator judging "opposite directions" from the two `suggestion` fields rather than a static pair list.

**Still open (folded into Gap 3):** whether a curated conflict-pair table is worth adding. Before investing, measure the **base rate** — scan past audit reports in `./codeprobe-reports/` and count how often overlapping findings actually point in opposite directions. If <1% of audits, the table is over-engineering.

**Options considered:** (1) detect-and-present with curated pair table — shipped without the table; (2) semantic conflict detection via a dedicated LLM call per overlap — rejected for cost and classifier drift; (3) agents-argue adjudication — rejected: unstable picks, and the right answer usually depends on context the model doesn't have.
