---
name: codeprobe-code-smells
description: >
  Detects code smells and anti-patterns — long methods, large classes, feature envy,
  data clumps, primitive obsession, dead code, magic numbers, deep nesting, and more.
  Uses configurable thresholds from .codeprobe-config.json when available.
  Trigger phrases: "code smells", "smell check", "anti-patterns", "clean code review".
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

# Code Smells & Anti-Pattern Detector

## Domain Scope

This sub-skill detects code smells and anti-patterns organized into these categories:

1. **Bloaters** — Long Method, Large Class, Data Clumps, Primitive Obsession
2. **Object-Orientation Abusers** — Feature Envy, Inappropriate Intimacy, Refused Bequest
3. **Change Preventers** — Shotgun Surgery, Divergent Change
4. **Dispensables** — Dead Code, Speculative Generality, Middle Man
5. **Couplers** — Temporal Coupling
6. **Readability** — Magic Numbers, Boolean Blindness, Deep Nesting

---

## What It Does NOT Flag

- **Generated code** — Migrations, compiled output, vendor directories (`vendor/`, `node_modules/`, `dist/`, `build/`, `.next/`), and auto-generated files (e.g., GraphQL codegen, Prisma client).
- **Test files** with long setup methods — Test context is different; long `setUp()` or `beforeEach()` methods arranging test data are expected and acceptable.
- **Configuration files** with many entries — A config file with 50 key-value pairs is not a "Large Class" smell.
- **Data migration files** — These are procedural by nature and often contain long methods.
- **Third-party code** checked into the repository (e.g., vendored libraries).
- **Structural issues already flagged by `codeprobe-solid` or `codeprobe-architecture`** — Large classes may also be flagged as SRP violations or god objects. This sub-skill should still detect and report them, but the orchestrator will deduplicate overlapping findings at the same location.

---

## Detection Instructions

### Configurable Thresholds

Before analysis, check for a `.codeprobe-config.json` file in the project root. If present, load the `severity_overrides` section to adjust these defaults:

| Threshold | Config Key | Default |
|-----------|-----------|---------|
| Long Method LOC limit | `long_method_loc` | 30 |
| Large Class LOC limit | `large_class_loc` | 300 |
| Deep Nesting max levels | `deep_nesting_max` | 3 |

### Bloaters

| ID Prefix | Smell | Signal | How to Detect | Default Threshold | Severity |
|-----------|-------|--------|---------------|-------------------|----------|
| `SMELL` | Long Method | Function/method exceeds LOC threshold | Count lines in each function/method body (excluding blank lines and single-line comments). Compare against `long_method_loc` threshold. For methods 2x over threshold, escalate to major. | > 30 LOC | Minor |
| `SMELL` | Large Class | Class exceeds LOC threshold | Count total lines in each class definition. Compare against `large_class_loc` threshold. For classes 2x over threshold, escalate to major (if not already major). Never escalate to critical — large classes are a maintainability concern, not a production defect. | > 300 LOC | Major |
| `SMELL` | Data Clumps | Same 3+ params passed together in 3+ places | Search for function/method signatures. Identify groups of 3+ parameters that appear together in 3+ different function signatures or call sites. These should be extracted into a parameter object or value object. | 3+ params, 3+ occurrences | Minor |
| `SMELL` | Primitive Obsession | String/int used where a value object is warranted | Look for string/integer variables representing domain concepts: email addresses (validated by regex inline), money amounts (numeric + currency passed separately), phone numbers, status strings compared in multiple places, ZIP codes, UUIDs passed as plain strings through multiple layers. | Pattern recognition | Minor |

### Object-Orientation Abusers

| ID Prefix | Smell | Signal | How to Detect | Default Threshold | Severity |
|-----------|-------|--------|---------------|-------------------|----------|
| `SMELL` | Feature Envy | Method accesses another object's data 3x+ more than its own | Count how many times a method references `$other->property` or `other.property` versus `$this->property` or `this.property` (or `self.`). If external references outnumber internal ones by 3x or more, the method likely belongs in the other class. | 3+ external accesses | Minor |
| `SMELL` | Inappropriate Intimacy | Class accessing another's private/protected internals | Search for reflection-based access (`setAccessible(true)`, `__get`, `__set` magic methods accessing protected fields), friend class patterns, or direct access to properties that are conventionally private (prefixed with `_` in Python/JS). | Any occurrence | Major |
| `SMELL` | Refused Bequest | Subclass inherits but doesn't use most of parent's methods | Examine subclasses: if the parent has N public methods and the subclass overrides fewer than 30% of them while also not calling `super`/`parent::` for most, this suggests the subclass doesn't truly need the inheritance relationship. | Unused majority of parent methods | Minor |

### Change Preventers

| ID Prefix | Smell | Signal | How to Detect | Default Threshold | Severity |
|-----------|-------|--------|---------------|-------------------|----------|
| `SMELL` | Shotgun Surgery | Changing one concept requires edits in 5+ files | Search for a single concept (e.g., a field name, a status value, a business rule) that appears across many files. If the same constant, column name, or business term appears in 5+ files without being centralized behind a single source of truth, flag it. | 5+ files for one concept | Major |
| `SMELL` | Divergent Change | One class modified for 3+ unrelated reasons | Examine large classes (> 200 LOC). Check whether the methods cluster around distinct, unrelated concerns. If a single class handles user authentication, email formatting, AND report generation, it has divergent change — any of those 3 areas changing forces this class to change. | 3+ distinct concerns | Major |

### Dispensables

| ID Prefix | Smell | Signal | How to Detect | Default Threshold | Severity |
|-----------|-------|--------|---------------|-------------------|----------|
| `SMELL` | Dead Code | Unreachable branches, unused imports, commented-out code blocks | Search for: (1) `import`/`use`/`require` statements for symbols never referenced elsewhere in the file, (2) commented-out code blocks (3+ consecutive commented lines that contain code syntax, not documentation), (3) functions/methods never called from anywhere in the codebase (use Grep across the project), (4) `if (false)` or `if (0)` blocks, unreachable code after unconditional `return`/`throw`/`exit`. | Any occurrence | Minor |
| `SMELL` | Speculative Generality | Abstractions/interfaces with only one implementation and no foreseeable second | Search for interfaces, abstract classes, or generic type parameters that have exactly one concrete implementation. If the abstraction does not appear in a DI container config or test mock, and the domain doesn't suggest future variants, flag it as premature abstraction. | Single implementation | Suggestion |
| `SMELL` | Middle Man | Class that only delegates to another class with no added logic | Look for classes where every method simply calls the same method on an injected dependency and returns the result, with no added logic, validation, transformation, or error handling. The class adds an unnecessary indirection layer. | Pure delegation in all methods | Minor |

### Couplers

| ID Prefix | Smell | Signal | How to Detect | Default Threshold | Severity |
|-----------|-------|--------|---------------|-------------------|----------|
| `SMELL` | Temporal Coupling | Methods must be called in specific order but nothing enforces it | Look for patterns where: (1) method A must be called before method B but there's no compile-time or runtime check, (2) `init()`/`setup()` must be called before `process()` but the class allows `process()` to be called first, (3) sequential method calls with shared mutable state where reordering would cause bugs. Check for comments like "must call X first" or "call after Y". | Implicit ordering dependency | Major |

### Readability

| ID Prefix | Smell | Signal | How to Detect | Default Threshold | Severity |
|-----------|-------|--------|---------------|-------------------|----------|
| `SMELL` | Magic Numbers | Hardcoded numeric/string literals without named constants in business logic | Search for numeric literals (other than 0, 1, -1) and string literals used in conditionals, calculations, or business logic. Flag values like `86400`, `3.14159`, `"pending"`, `0.15` that appear in logic paths without a named constant. Exclude: array indices, loop bounds of 0/1, common math constants in math libraries. | Any in logic paths | Minor |
| `SMELL` | Boolean Blindness | Method with 2+ boolean params | Search for function/method signatures with 2 or more `bool`/`boolean` parameters. Call sites like `process(true, false, true)` are unreadable. Suggest using named parameters, enums, or option objects instead. | 2+ boolean parameters | Minor |
| `SMELL` | Deep Nesting | Indentation levels exceed threshold | Count nesting depth in each function: each `if`, `for`, `while`, `foreach`, `switch`, `try`, `match` that is nested inside another adds a level. Flag when nesting exceeds `deep_nesting_max` threshold. Suggest early returns, guard clauses, or method extraction. | > 3 levels | Minor |

---

## ID Prefix & Fix Prompt Examples

All findings use the `SMELL-` prefix, numbered sequentially: `SMELL-001`, `SMELL-002`, etc.

### Fix Prompt Examples

- "Extract lines 45-90 of `UserService@register` into a private method `validateAndNormalizeInput()` — the method is 120 LOC doing 3 unrelated things: input validation (lines 45-65), data normalization (lines 66-80), and persistence (lines 81-90). Keep persistence in `register()` and extract the other two concerns."
- "Replace the magic number `86400` at line 55 of `app/Services/CacheService.php` with a named constant `SECONDS_PER_DAY = 86400` defined at the top of the class."
- "Refactor `processOrder(bool $isExpress, bool $requiresSignature, bool $isFragile)` in `OrderProcessor.php` (line 30) to accept a `ShippingOptions` value object instead of 3 boolean parameters. Create a `ShippingOptions` class with named properties."
- "Remove the commented-out code block at lines 88-105 of `PaymentGateway.php` — this is dead code from a previous implementation. If needed later, it can be recovered from version control."
- "In `ReportGenerator.php`, the `generate()` method at line 20 is 95 LOC. Extract the data-fetching logic (lines 25-50) into `fetchReportData()` and the formatting logic (lines 51-85) into `formatReport()`. The `generate()` method should orchestrate these two steps."
