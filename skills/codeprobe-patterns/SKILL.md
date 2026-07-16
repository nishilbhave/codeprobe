---
name: codeprobe-patterns
description: >
  Audits code for design pattern opportunities and anti-patterns — identifies places
  where a specific GoF or architectural pattern would solve an observable problem, and
  flags misapplied patterns that add complexity without benefit. Generates fix prompts.
  Trigger phrases: "design patterns", "pattern check", "pattern review", "refactoring patterns", "pattern analysis".
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

# Design Patterns Advisor

## Domain Scope

**Never recommend a pattern for the sake of it. Only flag a pattern opportunity when a concrete problem exists in the code that the pattern would solve. If the code works, is readable, and is maintainable without a pattern, do not suggest one.**

This sub-skill detects two categories of design pattern issues:

1. **Pattern Opportunities** — Places where a specific GoF or architectural pattern would solve an observable problem in the code (complexity, duplication, rigidity, hidden dependencies).
2. **Anti-Patterns** — Misapplied patterns that add complexity, indirection, or abstraction layers without delivering measurable benefit.

---

## What It Does NOT Flag

- **Switch statements on type/status are already flagged by `codeprobe-solid` (OCP-xxx).**
  This sub-skill flags them *only* when it can recommend a *specific named pattern* (e.g., Strategy, State) with concrete benefits over the current implementation. If the finding would be a generic "consider a pattern here" without naming one, defer to the SOLID auditor. To avoid duplicate findings, check whether the same switch/if-else block would already be covered by an OCP violation. If `codeprobe-solid` would flag it and your recommendation is simply "use polymorphism," do not emit a finding.
  **Decision rule:** if you can name the pattern, show the interface, and list the concrete implementations, emit a `PATTERN-` finding. If you can only say "this violates OCP," let `codeprobe-solid` handle it.

- **God classes are already flagged by `codeprobe-architecture` (ARCH-xxx).**
  This sub-skill only flags them when a *specific pattern* (e.g., Facade, Mediator) would be the recommended decomposition approach. If the recommendation is simply "split this class," defer to the architecture auditor. Only emit a finding when you can name the exact pattern and explain why it fits better than a generic decomposition.
  **Decision rule:** if your fix prompt says "extract into a Facade with these methods," emit a `PATTERN-` finding. If it says "break this into smaller classes," let `codeprobe-architecture` handle it.

- **Cross-cutting concerns flagged by `codeprobe-code-smells` (SMELL-xxx).**
  Duplicated logging, caching, or authorization code may already be flagged as code duplication. Only emit a `PATTERN-` finding when you recommend a specific pattern (Decorator, Middleware) as the solution. If the duplication is the primary issue, defer to the code smells auditor.

- **Simple scripts or small applications** where patterns would be over-engineering. A 50-line CLI script does not need a Strategy pattern. A single-file utility does not need a Factory. Apply proportional design judgment — patterns are tools for managing complexity, not goals in themselves.

- **Code that already implements a pattern correctly** — do not suggest replacing one correct pattern with another. If a Factory is working well, do not suggest switching to a Builder unless there is a concrete problem. If a class uses Observer correctly, do not suggest switching to a Mediator.

- **Test files** — test utilities and helpers have different design constraints. Test setup classes, fixture builders, and mock factories are not subject to the same pattern expectations as production code. Do not flag test doubles, test data builders, or test orchestration helpers.

- **Low-confidence pattern matches** (e.g., Prototype pattern) unless there is strong evidence of cloning behavior. Emit as Suggestion severity at most. When in doubt, do not emit the finding.

---

## Detection Instructions

### Pattern Opportunities

| Observed Problem | Candidate Pattern | How to Detect | Confidence | Severity |
|-----------------|-------------------|---------------|------------|----------|
| Complex object construction with 4+ optional params | Builder | Constructor or factory method with 4+ optional/nullable parameters. Methods that build objects step-by-step using setters then `build()` would be clearer. | High | Minor |
| Duplicated `new X()` with conditionals scattered across codebase | Factory | Search for `new ClassName()` instantiation of the same family of classes in 3+ locations with surrounding if/switch logic to decide which class to create. | High | Major |
| Switch on type to select behavior (when a specific pattern applies) | Strategy | Switch/if-else chain where each branch executes a different *algorithm* or *behavior* — not just returning a value. Must have 3+ branches and the variants are likely to grow. Only flag if NOT already covered by an OCP finding. | High | Major |
| Object behavior changes based on internal state field | State | A class with methods containing if/switch on `$this->status` or `this.state` where the same field controls behavior in 3+ methods. State transitions are scattered across the class. | Medium | Minor |
| Multiple listeners need to react to a change | Observer / Event Dispatcher | A method that directly calls 3+ other services/handlers after a state change (e.g., after order creation: send email, update inventory, notify warehouse, log audit). Should be events. | High | Minor |
| Cross-cutting logic interleaved with business logic | Decorator / Middleware | Logging, caching, authorization, or timing code mixed into business logic methods. Same cross-cutting concern copy-pasted across 3+ methods. | High | Major |
| God class wrapping a complex subsystem | Facade | A large class (300+ LOC) that coordinates multiple subsystems. Clients only need a simplified interface. Only flag when probe-architecture hasn't already flagged as a god object. | Medium | Minor |
| Undo/redo or command queue requirements | Command | Code that needs to queue, log, or reverse operations but currently executes them inline. | Medium | Suggestion |
| Data flows through conditional transformation steps | Pipeline / Chain of Responsibility | Data processed through 3+ sequential if/else transformation steps where each step is conditionally applied. Could be a pipeline of composable stages. | Medium | Minor |
| Multiple similar objects differing by a few fields | Prototype | Factory-like code that creates copies of objects with minor variations. | Low | Suggestion |

### Anti-Patterns (Misapplied Patterns)

| Anti-Pattern | What to Detect | How to Detect | Severity |
|-------------|----------------|---------------|----------|
| Singleton for dependency hiding | Class uses `getInstance()`, `static::$instance`, or module-level singleton to access dependencies that should be injected via constructor. The singleton pattern hides dependencies and makes testing difficult. | Search for `getInstance()`, `static::$instance`, `self::$instance`, module-level singleton access patterns in business logic classes. Check whether these dependencies could be injected via constructor instead. | Major |
| Pass-through Repository | Repository class wrapping ORM (Eloquent, Doctrine, Prisma) where every method is a 1-line delegation with zero added abstraction, caching, or query logic. The repository adds a layer without value. | Find repository classes and check each public method body: if every method is a single-line call to the underlying ORM model with no additional logic, the repository is a pass-through. | Minor |
| Service class that's a renamed controller action | Service class with a single public method that exactly mirrors a controller action — same params, same logic, just moved to a different file. Adds indirection without reuse. | Find service classes with only one public method. Check if the method signature and logic closely match a corresponding controller action. Look for zero reuse across the codebase (only one caller). | Minor |
| Abstract Factory with one family | Abstract factory interface with only one concrete factory implementation and no foreseeable second implementation. Over-abstraction. | Find abstract factory interfaces/classes. Count the number of concrete implementations. If there is exactly one and no indicators of planned expansion (no TODO comments, no documentation mentioning future variants), flag it. | Suggestion |

---

## ID Prefix & Fix Prompt Examples

All findings use the `PATTERN-` prefix, numbered sequentially: `PATTERN-001`, `PATTERN-002`, etc.

### Fix Prompt Examples

- "Replace the switch on `$type` in `NotificationSender` (lines 30-65) with a Strategy pattern: create a `NotificationChannel` interface with `send(Message $message)` method. Create `EmailChannel`, `SmsChannel`, and `PushChannel` implementations. Use a `NotificationChannelFactory` to resolve the correct channel by type."
- "Refactor `ReportBuilder` constructor (line 15) which takes 7 optional params (`$title`, `$subtitle`, `$dateRange`, `$format`, `$includeCharts`, `$paperSize`, `$orientation`) into a Builder pattern: create `ReportBuilderConfig` with fluent setter methods and a `build()` method."
- "The `AuditLogger` at `app/Services/AuditLogger.php` uses `AuditLogger::getInstance()` (line 5) as a singleton. Replace with constructor injection: register `AuditLogger` in the DI container as a singleton binding, and inject it via constructor in the 4 classes that currently call `::getInstance()`."
- "Remove the `UserRepositoryInterface` and `UserRepository` wrapper at `app/Repositories/` — every method (`find`, `create`, `update`, `delete`) is a single-line delegation to Eloquent with zero added logic. Use the Eloquent model directly until you have a concrete reason for the abstraction."
