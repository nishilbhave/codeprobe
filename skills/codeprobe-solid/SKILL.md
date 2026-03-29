---
name: probe-solid
description: >
  Audits code for SOLID principle violations — Single Responsibility, Open/Closed,
  Liskov Substitution, Interface Segregation, and Dependency Inversion. Identifies
  classes and methods that violate these principles and generates fix prompts.
  Trigger phrases: "SOLID check", "solid review", "SRP violation", "dependency inversion".
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# SOLID Principles Auditor

## READ-ONLY CONSTRAINT

**This sub-skill is strictly read-only. Never modify, write, edit, or delete any file in the user's codebase. Report findings only.**

---

## Domain Scope

This sub-skill detects violations of the five SOLID principles:

1. **Single Responsibility Principle (SRP)** — A class or module should have only one reason to change.
2. **Open/Closed Principle (OCP)** — Software entities should be open for extension but closed for modification.
3. **Liskov Substitution Principle (LSP)** — Subtypes must be substitutable for their base types without altering program correctness.
4. **Interface Segregation Principle (ISP)** — Clients should not be forced to depend on interfaces they do not use.
5. **Dependency Inversion Principle (DIP)** — High-level modules should not depend on low-level modules; both should depend on abstractions.

---

## What It Does NOT Flag

- **Simple DTOs/value objects** with multiple fields — having many properties is not an SRP violation when the class represents a single data concept.
- **Small scripts and CLIs** that don't need dependency injection — proportional design matters.
- **Enums used in switches** where the enum is stable and closed (e.g., compass directions, days of the week) — OCP applies when variants are likely to grow.
- **Framework-generated classes** following framework conventions (e.g., Laravel migrations, Django admin classes, Rails ActiveRecord models with standard callbacks).
- **Test helper classes** that aggregate setup utilities — test infrastructure has different design constraints.

---

## Detection Instructions

### SRP — Single Responsibility Principle

| ID Prefix | Signal | How to Detect | Severity |
|-----------|--------|---------------|----------|
| `SRP` | Class has 5+ public methods doing unrelated things | Count public methods. If 5+ exist, check whether they cluster around a single responsibility or span multiple concerns (e.g., authentication + email + database). Look for method name prefixes that suggest different domains. | Major |
| `SRP` | Method exceeds 30 LOC doing multiple concerns | Count lines in each method (excluding blank lines and comments). If > 30 LOC, check whether the method handles multiple distinct steps (validation, transformation, persistence, notification) that could be extracted. | Minor |
| `SRP` | Class name is vague | Flag classes named `Manager`, `Handler`, `Utils`, `Helper`, `Processor`, `Service` (when not domain-qualified) — these names suggest the class has no clear single purpose. Exception: if the class is small (< 5 methods, < 100 LOC), downgrade to suggestion. | Minor |
| `SRP` | Constructor takes 5+ dependencies | Count constructor parameters or injected dependencies. 5+ dependencies suggest the class has too many responsibilities. Check whether dependencies serve different domains. | Major |

### OCP — Open/Closed Principle

| ID Prefix | Signal | How to Detect | Severity |
|-----------|--------|---------------|----------|
| `OCP` | Switch/if-else chains on type or status | Look for `switch`/`if-else` chains that branch on a type, status, role, or kind field — especially where adding a new variant requires modifying this block. Count the number of cases: 3+ cases on a growable type is a signal. | Major |
| `OCP` | No extension point where variants are likely to grow | When a switch/if-else on type is found, check whether there is an interface, abstract class, strategy pattern, or plugin mechanism that would allow adding new variants without modifying the existing code. If absent, flag it. | Minor |

### LSP — Liskov Substitution Principle

| ID Prefix | Signal | How to Detect | Severity |
|-----------|--------|---------------|----------|
| `LSP` | Subclass overrides method but changes semantics | Check overridden methods: does the subclass return a fundamentally different type, change the meaning of the return value, or produce side effects the parent does not? Compare method signatures and doc comments. | Major |
| `LSP` | Subclass throws exception parent doesn't declare | Look for overridden methods that throw exceptions not present in the parent's throws clause or documented contract. In dynamic languages, look for `raise`/`throw` in overrides where the parent method doesn't throw. | Major |
| `LSP` | Subclass ignores or no-ops parent behavior | Look for overridden methods with empty bodies, `pass`, `return null`, `return`, or `// not implemented` comments. The subclass is refusing the parent's contract. | Minor |
| `LSP` | `instanceof`/type checks after polymorphic call | Search for `instanceof`, `is_a`, `typeof`, `type()`, `is` checks on objects that should be used polymorphically. If code calls a method on a base type and then checks the concrete type, it signals broken substitutability. | Major |

### ISP — Interface Segregation Principle

| ID Prefix | Signal | How to Detect | Severity |
|-----------|--------|---------------|----------|
| `ISP` | Interface has 8+ methods | Count methods declared in each interface/abstract class/protocol. If 8+, the interface is likely too broad. Check whether the methods cluster into distinct groups. | Minor |
| `ISP` | Class implements interface but leaves methods empty or throwing | Look for interface implementations where one or more methods are empty, return null, throw `NotImplementedError`/`UnsupportedOperationException`, or contain only `pass`/`TODO` comments. | Major |
| `ISP` | Multiple unrelated method groups in one interface | Analyze the interface's methods: do they fall into 2+ distinct responsibility groups (e.g., read operations + write operations + notification methods)? If so, the interface should be split. | Major |

### DIP — Dependency Inversion Principle

| ID Prefix | Signal | How to Detect | Severity |
|-----------|--------|---------------|----------|
| `DIP` | `new ConcreteClass()` inside business logic | Search for direct instantiation (`new ClassName()`, direct constructor calls) of infrastructure or service classes inside business logic methods. Exclude: DTOs, value objects, exceptions, collections, factories, and DI container registrations. | Major |
| `DIP` | High-level module imports from infrastructure layer directly | Check import statements: does a domain/business logic module import directly from database drivers, HTTP clients, file system libraries, or third-party SDKs without an abstraction layer? Look for patterns like `import mysql`, `use Illuminate\Support\Facades\DB`, `from requests import`. | Major |
| `DIP` | No constructor injection — static method calls to concrete dependencies | Look for static method calls like `Database::query()`, `Cache::get()`, `Logger.log()` in business logic where no interface is injected. The class is tightly coupled to the concrete implementation via static access. | Minor |

---

## Reference Loading

If the project uses a specific framework or language, load the relevant reference file from `../probe/references/{file}.md` using Read. Available references include:

- `php-laravel.md` for PHP/Laravel projects
- `javascript-typescript.md` for JS/TS projects
- `python.md` for Python projects
- `react-nextjs.md` for React/Next.js projects

If the reference file is unavailable, continue the analysis without it.

---

## Output Contract

Every finding MUST include ALL of the following fields:

```json
{
  "id": "{PREFIX}-{NNN}",
  "severity": "critical|major|minor|suggestion",
  "location": { "file": "path/to/file.ext", "lines": "45-120" },
  "problem": "One sentence describing what's wrong",
  "evidence": "Concrete proof from the code — quote specific patterns, counts, names",
  "suggestion": "Human-readable recommendation",
  "fix_prompt": "Copy-pasteable prompt for Claude Code to apply the fix. Must reference specific file names, line ranges, method names, and the exact change to make.",
  "refactored_sketch": "// optional: minimal code showing the fix direction"
}
```

### ID Prefixes

- `SRP-` — Single Responsibility Principle violations
- `OCP-` — Open/Closed Principle violations
- `LSP-` — Liskov Substitution Principle violations
- `ISP-` — Interface Segregation Principle violations
- `DIP-` — Dependency Inversion Principle violations

Number findings sequentially within each prefix: `SRP-001`, `SRP-002`, `OCP-001`, etc.

### Rendered Finding Format

```
### {ID} | {Severity} | `{file}:{lines}`

**Problem:** {problem description}

**Evidence:**
> {quoted code patterns, method names, counts, specific line references}

**Suggestion:** {what to do to fix it}

**Fix prompt:**
> {copy-pasteable prompt for Claude Code}

**Refactored sketch:** (optional)
```

### Fix Prompt Examples

- "Refactor `src/OrderService.php`: extract payment logic (lines 45-78) into a new `PaymentService` class. Inject `PaymentService` via constructor into `OrderService`. Move methods `calculateTotal()`, `applyDiscount()`, and `processPayment()` to the new class."
- "Replace the switch on `$type` in `NotificationSender` (lines 30-65) with a Strategy pattern: create a `NotificationChannel` interface with a `send(Message $message)` method. Create `EmailChannel`, `SmsChannel`, and `PushChannel` implementations. Use a `NotificationChannelFactory` to resolve the correct channel by type."
- "In `UserRepository.php`, replace `new MySqlConnection()` at line 23 with constructor injection: add a `DatabaseConnectionInterface $connection` parameter to the constructor and use it instead of the concrete instantiation."

---

## Execution Modes

This sub-skill supports three modes, set by the orchestrator:

### `full` Mode
Analyze the target path thoroughly. Produce detailed findings for every detected violation with all required fields (id, severity, location, problem, evidence, suggestion, fix_prompt). Include refactored_sketch for major and critical findings where it adds clarity.

### `scan` Mode
Quick count of violations by severity. Identify the worst offenders (files/classes with the most violations). Skip the `evidence` and `fix_prompt` fields. Return:
- Count of violations per principle (SRP, OCP, LSP, ISP, DIP)
- Count by severity (critical, major, minor, suggestion)
- Top 3 worst-offending files with brief descriptions

### `score-only` Mode
Count violations by severity per principle. Return only the summary counts — no individual findings, no evidence, no fix prompts. Output the summary object only.

---

## Summary Output

At the end of every execution (regardless of mode), provide a summary:

```json
{
  "skill": "probe-solid",
  "summary": { "critical": 0, "major": 0, "minor": 0, "suggestion": 0 }
}
```

Replace the zeros with actual counts from the analysis.
