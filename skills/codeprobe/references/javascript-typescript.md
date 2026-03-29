# JavaScript & TypeScript Reference Guide

## TypeScript Strict Mode

### Avoiding `any`

| Anti-pattern | Why It's Wrong | Correct Pattern |
|---|---|---|
| `param: any` | Disables all type checking for that value | Use a specific type, `unknown`, or a generic |
| `as any` type assertion | Silences legitimate type errors | Fix the root cause or use a narrower assertion |
| `// @ts-ignore` | Hides the error without fixing it | Use `// @ts-expect-error` with explanation if truly unavoidable |
| `Record<string, any>` for API responses | No validation of response shape | Define an interface or use a runtime validator (Zod, io-ts) |

```typescript
// BAD
function process(data: any) {
  return data.items.map((x: any) => x.name);
}

// GOOD
interface ApiResponse {
  items: Array<{ name: string }>;
}
function process(data: ApiResponse) {
  return data.items.map((x) => x.name);
}
```

### Type Narrowing & Discriminated Unions

```typescript
// BAD: type assertion instead of narrowing
function handle(value: string | number) {
  const len = (value as string).length; // crashes if number
}

// GOOD: type narrowing
function handle(value: string | number) {
  if (typeof value === 'string') {
    return value.length;
  }
  return value.toFixed(2);
}

// GOOD: discriminated union
type Result =
  | { status: 'success'; data: User }
  | { status: 'error'; error: string };

function handle(result: Result) {
  if (result.status === 'success') {
    return result.data; // TypeScript knows this is User
  }
  throw new Error(result.error);
}
```

### Generic Constraints

```typescript
// BAD: unconstrained generic loses type info
function getProperty<T>(obj: T, key: string) {
  return (obj as any)[key]; // no type safety
}

// GOOD: constrained generic
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}
```

---

## Async/Await

### Common Pitfalls

| Anti-pattern | Why It's Wrong | Correct Pattern |
|---|---|---|
| Sequential awaits for independent operations | Wastes time — runs serially when parallel is possible | `await Promise.all([fetchA(), fetchB()])` |
| Missing `try/catch` around `await` | Unhandled promise rejection crashes Node process | Wrap in `try/catch` or add `.catch()` handler |
| `async` function that never awaits | Unnecessary async wrapper | Remove `async` keyword if not needed |
| Floating promises (no `await`, no `.catch()`) | Silent failures — errors vanish | Always `await` or attach `.catch()` |
| `await` inside a loop body | Sequential execution, N round trips | Collect promises, `await Promise.all()` |

```typescript
// BAD: sequential when parallel is possible
const users = await fetchUsers();
const orders = await fetchOrders(); // waits for users to finish first

// GOOD: parallel execution
const [users, orders] = await Promise.all([
  fetchUsers(),
  fetchOrders(),
]);

// BAD: await in loop
for (const id of ids) {
  const user = await fetchUser(id); // N sequential requests
}

// GOOD: parallel with concurrency control
const users = await Promise.all(ids.map((id) => fetchUser(id)));
```

### Error Handling in Async

```typescript
// BAD: swallowing errors
async function save(data: Data) {
  try {
    await db.insert(data);
  } catch (e) {
    // silently ignores the error
  }
}

// GOOD: handle or rethrow with context
async function save(data: Data) {
  try {
    await db.insert(data);
  } catch (error) {
    logger.error('Failed to save data', { error, dataId: data.id });
    throw new DatabaseError('Insert failed', { cause: error });
  }
}
```

---

## Module System

### ESM vs CJS Issues

| Flag | Why It Matters |
|---|---|
| `require()` mixed with `import` in the same project | Causes dual-package hazard and confusing resolution |
| `module.exports` in a TypeScript project with `"module": "ESNext"` | Mismatched module system |
| `__dirname` / `__filename` used in ESM | Not available in ESM — use `import.meta.url` instead |

### Barrel Exports and Circular Imports

| Anti-pattern | Why | Fix |
|---|---|---|
| `index.ts` re-exporting everything from a large directory | Prevents tree-shaking, increases bundle size | Import directly from the specific module |
| Circular imports between modules | Runtime errors, `undefined` values at import time | Restructure to break the cycle — extract shared code into a third module |

---

## Error Handling

| Anti-pattern | Correct Pattern |
|---|---|
| `catch (e) {}` — empty catch block | Log the error or rethrow with context |
| `catch (e) { throw e }` — pointless catch | Remove the try/catch entirely |
| Throwing plain strings: `throw 'something failed'` | Throw `Error` instances: `throw new Error('...')` |
| Catching broad `Error` when only expecting specific errors | Use custom error classes and check `instanceof` |
| Error messages without context | Include relevant IDs, inputs, and operation name |

```typescript
// BAD
throw 'not found';

// GOOD: custom error hierarchy
class AppError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly statusCode: number = 500,
    options?: ErrorOptions,
  ) {
    super(message, options);
    this.name = this.constructor.name;
  }
}

class NotFoundError extends AppError {
  constructor(resource: string, id: string) {
    super(`${resource} with id ${id} not found`, 'NOT_FOUND', 404);
  }
}
```

---

## Immutability & Pure Functions

| Anti-pattern | Why | Correct Pattern |
|---|---|---|
| `let` when value is never reassigned | Signals mutability to the reader | Use `const` by default |
| Mutating function parameters | Causes hidden side effects for callers | Spread/clone: `{ ...obj, key: newValue }` |
| `Array.push()` to build a new array in a pure function | Mutates in place | Use `[...existing, newItem]` or `.concat()` |
| `arr.sort()` without cloning | Mutates the original array | `[...arr].sort()` or `arr.toSorted()` (ES2023) |
| Side effects inside `.map()` / `.filter()` / `.reduce()` | These should be pure transformations | Move side effects out; use `.forEach()` for side effects |

---

## Common Anti-patterns

| Anti-pattern | Detection Signal | Fix |
|---|---|---|
| Callback hell (3+ nested callbacks) | Deeply indented `.then().then()` chains or nested callbacks | Refactor to async/await |
| Event listener leaks | `addEventListener` without corresponding `removeEventListener` or `AbortController` | Clean up in `useEffect` return, `ngOnDestroy`, or via `AbortController` |
| Blocking the event loop | `while` loops, `fs.readFileSync` in server request handlers, heavy computation without `worker_threads` | Use async I/O, offload CPU work to workers |
| `eval()` or `Function()` constructor | Dynamic code execution from strings | Almost never needed — use safer alternatives |
| `==` instead of `===` | Coercion bugs | Always use strict equality |
| Nested ternaries | Unreadable conditional logic | Use `if/else` or extract into a function |

---

## ES2022+ Features to Prefer

| Old Pattern | Modern Alternative | Standard |
|---|---|---|
| `JSON.parse(JSON.stringify(obj))` for deep clone | `structuredClone(obj)` | ES2022 |
| `arr[arr.length - 1]` | `arr.at(-1)` | ES2022 |
| `obj.hasOwnProperty('key')` | `Object.hasOwn(obj, 'key')` | ES2022 |
| Top-level async IIFE: `(async () => { ... })()` | Top-level `await` (in ESM) | ES2022 |
| `Object.assign({}, a, b)` | `{ ...a, ...b }` (already standard, but still seen) | ES2018 |
| `arr.find(x => x.id === id) !== undefined` | `arr.some(x => x.id === id)` for boolean check | ES2015 |
| Manual group-by loops | `Object.groupBy(arr, fn)` | ES2024 |
| `arr.flat().map(fn)` | `arr.flatMap(fn)` | ES2019 |

---

## Package Management

| What to Check | Flag If | Why |
|---|---|---|
| Lock file | `package-lock.json` or `yarn.lock` or `pnpm-lock.yaml` missing from repo | Non-reproducible builds |
| Lock file in `.gitignore` | Lock file is gitignored for an application (not a library) | Applications must commit lock files |
| Duplicate functionality | Multiple packages doing the same thing (e.g., `axios` + `node-fetch` + `got`) | Pick one HTTP client |
| Unnecessary dependencies | Package used for trivial functionality (e.g., `is-odd`, `left-pad`) | Write the 2-line function inline |
| `dependencies` vs `devDependencies` | Test frameworks, linters, build tools in `dependencies` | Move to `devDependencies` |

---

## Node.js Specifics

| Anti-pattern | Detection Signal | Correct Pattern |
|---|---|---|
| Unhandled rejection without global handler | No `process.on('unhandledRejection', ...)` in entry point | Add handler that logs and exits |
| Synchronous I/O in request handlers | `fs.readFileSync`, `fs.writeFileSync` in route handlers | Use `fs.promises.readFile` |
| Secrets in source code | String literals assigned to variables named `secret`, `key`, `token`, `password` | Use environment variables |
| `console.log` for production logging | `console.log` in service/production code | Use a structured logger (pino, winston) |
| Missing `AbortController` for fetch timeouts | `fetch()` without timeout or abort signal | Pass `signal: AbortSignal.timeout(5000)` |
