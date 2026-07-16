---
name: codeprobe-testing
description: >
  Audits code for test quality and coverage issues — missing tests, test smells,
  poor test structure, mock abuse, coverage gaps, and fragile test data. Identifies
  weaknesses in the test suite and generates fix prompts.
  Trigger phrases: "test quality", "test audit", "test review", "coverage check", "missing tests", "test quality audit".
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

# Test Quality & Coverage Auditor

## Domain Scope

This sub-skill detects test quality and coverage issues across six categories:

1. **Missing Tests** — Public methods without corresponding tests, critical business logic untested.
2. **Test Smells** — Tests with no assertions, testing implementation details, brittle tests.
3. **Test Structure** — Missing Arrange-Act-Assert separation, poor naming, testing too many things.
4. **Mock Abuse** — Mocking the system under test, mock returning mocks, over-mocking.
5. **Coverage Gaps** — No tests for error paths, authorization logic, edge cases.
6. **Test Data** — Hardcoded IDs, fragile fixtures, environment-dependent tests.

---

## What It Does NOT Flag

- **Missing tests for trivial getters/setters or pure DTOs** — these add testing overhead without meaningful coverage.
- **Framework-generated test stubs** that are empty but clearly scaffolded (e.g., Laravel's `ExampleTest.php`, Create React App's `App.test.js`) — these are starting points, not abandoned tests.
- **Integration/E2E test suites** that intentionally don't follow unit test conventions — different test levels have different design constraints.
- **Test execution speed** — this sub-skill assesses test design quality, not runtime performance.
- **Tests in `vendor/`, `node_modules/`, or other dependency directories.**

---

## Detection Instructions

### Severity Ceiling

**No finding from this sub-skill should ever be classified as Critical.** Missing tests, even for critical business logic, are a maintainability and risk issue (Major), not a confirmed production defect. The highest severity this sub-skill may assign is **Major**. Follow the severity column in each detection table exactly — do not escalate beyond it.

### Missing Tests

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|----------------|---------------|----------|
| `TEST` | Public methods with no corresponding test | Scan source directories for public class methods. For each, check if a corresponding test file/method exists. Use test file naming conventions: `test_`, `_test.`, `.test.`, `Test[A-Z]`, `spec_`, `_spec.`, `.spec.` (matching `file_stats.py` patterns). | Major |
| `TEST` | Critical business logic untested | Identify classes/methods handling payments, authentication, authorization, order processing, or data mutations. Check whether these have dedicated test coverage. | Major |
| `TEST` | Edge cases unaddressed | When tests exist for a method, check whether they cover: null/empty inputs, boundary values (0, -1, max), error cases, and the happy path. Flag methods with only happy-path tests. | Minor |

### Test Smells

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|----------------|---------------|----------|
| `TEST` | Tests with no assertions | Search test methods for assertion calls (`assert`, `expect`, `should`, `verify`). Flag test methods that execute code but never assert on the outcome — they only verify "no exception thrown." | Major |
| `TEST` | Tests testing implementation details | Tests that mock every dependency and only verify call order/counts rather than outcomes. Tests that break when internal implementation changes but behavior stays the same. Look for excessive `->expects()->method()->with()` chains or `toHaveBeenCalledWith` without checking return values. | Minor |
| `TEST` | Brittle tests coupled to external state | Tests that depend on database state not set up in the test, file system paths, network calls, or system time without mocking. Look for raw SQL in tests, `file_exists()` checks, HTTP calls without mocking. | Minor |
| `TEST` | Tests dependent on execution order | Tests that pass individually but fail when run together (or vice versa). Look for shared mutable state between test methods: class-level properties modified in tests, database records not cleaned up. | Major |

### Test Structure

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|----------------|---------------|----------|
| `TEST` | Missing Arrange-Act-Assert separation | Test methods where setup, execution, and assertion are interleaved rather than clearly separated. Multiple act+assert cycles in one test. | Minor |
| `TEST` | Test names that don't describe the scenario | Test methods named `test1`, `testFunction`, `it_works`, or using generic names that don't describe the input condition and expected outcome. Good: `test_empty_cart_returns_zero_total`. Bad: `testCalculate`. | Minor |
| `TEST` | Single test testing too many things | Test methods with 5+ assertions on unrelated outcomes, or that test multiple scenarios in sequence. Should be split into focused tests. | Minor |

### Mock Abuse

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|----------------|---------------|----------|
| `TEST` | Mocking the system under test | Test creates a mock/partial mock of the class being tested. The test is testing the mock, not the actual code. Look for `$this->createPartialMock(ClassName::class)` or `jest.spyOn(sut, 'method')` where sut is the class being tested. | Major |
| `TEST` | Mock returning mocks | Mock objects configured to return other mock objects, creating deep mock chains. `$mock->method('getUser')->willReturn($userMock)` where `$userMock->method('getProfile')->willReturn($profileMock)`. | Major |
| `TEST` | Over-mocking making tests pass regardless | Tests where every dependency is mocked and the mocks return exactly what the code expects, making the test a tautology. If you change the implementation logic, the test still passes because the mocks drive the result. | Minor |

### Coverage Gaps

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|----------------|---------------|----------|
| `TEST` | No tests for error/exception paths | Methods with try/catch blocks or error handling where tests only cover the success path. No test triggers the catch/error branch. | Minor |
| `TEST` | No tests for authorization logic | Permission checks, policy methods, gate definitions, middleware authorization — code that controls access but has no dedicated tests. | Major |
| `TEST` | No edge case tests | Functions handling arrays/collections without tests for empty input. Numeric functions without tests for zero, negative, or boundary values. String functions without tests for empty string, unicode, or very long input. | Minor |

### Test Data

| ID Prefix | What to Detect | How to Detect | Severity |
|-----------|----------------|---------------|----------|
| `TEST` | Hardcoded IDs that may collide | Tests using hardcoded numeric IDs (`$userId = 42`, `id: 1`) instead of factory-generated values. These collide in parallel test runs or with seeded data. | Minor |
| `TEST` | Fragile factory/fixture setup | Tests with complex inline data setup that duplicates across multiple tests instead of using factories/fixtures/builders. | Minor |
| `TEST` | Tests relying on specific database state | Tests that assume certain records exist in the database without creating them in the test setup. Depends on seeders or previous test execution. | Minor |

---

## ID Prefix & Fix Prompt Examples

All findings use the `TEST-` prefix, numbered sequentially: `TEST-001`, `TEST-002`, etc.

### Fix Prompt Examples

- "Write a test for `OrderService@calculateTotal` that covers: empty cart (expect 0), single item, multiple items, and item with discount. Use `OrderFactory` for test data. Place in `tests/Unit/Services/OrderServiceTest.php`."
- "The test `test_user_can_login` at `tests/Feature/AuthTest.php:25` has no assertions — it only calls the login endpoint. Add `assertStatus(200)`, `assertAuthenticated()`, and `assertJsonStructure(['token'])` assertions."
- "In `tests/Unit/PaymentServiceTest.php:40`, the mock chain is mocking too deeply. Create a concrete `FakePaymentGateway` that implements the gateway interface and returns predictable responses instead of nested mock returns."
- "Replace the hardcoded user ID `42` in `tests/Feature/OrderTest.php:15` with `User::factory()->create()->id` to prevent test collisions in parallel test runs."
