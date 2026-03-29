# React & Next.js Reference Guide

## Component Patterns

### Composition Over Prop Drilling

| Anti-pattern | Detection Signal | Correct Pattern |
|---|---|---|
| Prop drilling > 3 levels | Same prop passed through 3+ intermediate components that don't use it | Use Context API, composition (children), or state management |
| Mega-component > 200 LOC | Single component file exceeding 200 lines | Extract into smaller, focused components |
| Render logic mixed with data fetching | `useEffect` + `useState` for data fetching alongside JSX | Separate data layer (custom hook, server component, or React Query) |
| Boolean prop explosion | `<Button primary large disabled rounded />` | Use variant enum: `<Button variant="primary" size="lg" />` |

```tsx
// BAD: prop drilling
function App() {
  const [user, setUser] = useState<User | null>(null);
  return <Layout user={user}><Sidebar user={user}><Profile user={user} /></Sidebar></Layout>;
}

// GOOD: composition with children
function App() {
  const [user, setUser] = useState<User | null>(null);
  return (
    <Layout>
      <Sidebar>
        <Profile user={user} />
      </Sidebar>
    </Layout>
  );
}

// GOOD: context for truly global data
const UserContext = createContext<User | null>(null);
function App() {
  const [user, setUser] = useState<User | null>(null);
  return (
    <UserContext.Provider value={user}>
      <Layout><Sidebar><Profile /></Sidebar></Layout>
    </UserContext.Provider>
  );
}
```

### Controlled vs Uncontrolled

| Flag | Why |
|---|---|
| `useRef` to read input value on submit when controlled state exists | Mixed paradigm — pick one |
| `defaultValue` + `value` on same input | Contradictory: React will warn |
| Form with 10+ `useState` for individual fields | Use a form library (React Hook Form) or `useReducer` |

---

## Hooks

### useEffect Rules

| Anti-pattern | Why It's Wrong | Fix |
|---|---|---|
| Missing dependency in dependency array | Stale closure: effect reads outdated values | Add the missing dependency (or rethink the effect) |
| `// eslint-disable-next-line react-hooks/exhaustive-deps` | Suppressing the lint rule usually hides a real bug | Fix the dependency issue instead of disabling |
| Effect without cleanup for subscriptions | Memory leak: subscription persists after unmount | Return a cleanup function |
| Setting state that derives from props/state | Unnecessary render cycle | Compute during render: `const derived = items.filter(...)` |
| Fetching data in useEffect without abort | Race condition on fast re-renders | Use `AbortController` or React Query/SWR |

```tsx
// BAD: missing cleanup, no abort, stale closure risk
useEffect(() => {
  fetch(`/api/users/${id}`)
    .then(res => res.json())
    .then(setUser);
}, []); // missing `id` dependency

// GOOD: abort controller, correct deps, cleanup
useEffect(() => {
  const controller = new AbortController();
  fetch(`/api/users/${id}`, { signal: controller.signal })
    .then(res => res.json())
    .then(setUser)
    .catch(err => {
      if (err.name !== 'AbortError') throw err;
    });
  return () => controller.abort();
}, [id]);
```

### Massive useEffect Anti-pattern

```tsx
// BAD: one effect doing 5 unrelated things
useEffect(() => {
  fetchUser();
  trackPageView();
  initWebSocket();
  loadPreferences();
  syncCart();
}, []);

// GOOD: one effect per concern
useEffect(() => { fetchUser() }, [userId]);
useEffect(() => { trackPageView() }, [pathname]);
useEffect(() => {
  const ws = initWebSocket();
  return () => ws.close();
}, []);
```

### useMemo / useCallback

| Flag | When It Actually Helps |
|---|---|
| `useMemo` on a simple string concatenation | Only useful for expensive computations or referential equality for children |
| `useCallback` on every handler | Only useful when passed to `React.memo`-wrapped children or as a dependency |
| Missing `useMemo` on expensive computation re-running every render | Filter/sort/transform of large arrays |
| Missing `useCallback` for handler passed to memoized list items | Causes all list items to re-render |

---

## State Management

| Situation | Recommended Approach | Anti-pattern |
|---|---|---|
| Local UI state (open/closed, selected tab) | `useState` | Putting UI state in global store |
| Form state | `useReducer` or React Hook Form | 10+ separate `useState` calls |
| Data shared by 2-3 nearby components | Lift state to common parent | Global store for local sharing |
| App-wide authenticated user, theme | Context API | Prop drilling through 5+ components |
| Server data (API cache) | React Query / SWR / server components | Manual `useEffect` + `useState` fetch pattern |
| Complex client state with many actions | Zustand, Jotai, or `useReducer` | Redux for simple apps |

### Derived State

```tsx
// BAD: state that should be computed
const [items, setItems] = useState<Item[]>([]);
const [filteredItems, setFilteredItems] = useState<Item[]>([]);
const [totalPrice, setTotalPrice] = useState(0);

useEffect(() => {
  setFilteredItems(items.filter(i => i.active));
}, [items]);

useEffect(() => {
  setTotalPrice(filteredItems.reduce((sum, i) => sum + i.price, 0));
}, [filteredItems]);

// GOOD: compute during render
const [items, setItems] = useState<Item[]>([]);
const filteredItems = items.filter(i => i.active);
const totalPrice = filteredItems.reduce((sum, i) => sum + i.price, 0);
// useMemo only if the computation is actually expensive:
// const filteredItems = useMemo(() => items.filter(i => i.active), [items]);
```

---

## Performance

| Anti-pattern | Detection Signal | Fix |
|---|---|---|
| Re-rendering long lists on every state change | List of 100+ items without virtualization | Use `react-window` or `@tanstack/virtual` |
| Inline object/array as prop | `<Child style={{ color: 'red' }} />` in every render | Extract to constant or `useMemo` |
| Missing `key` or using index as `key` for dynamic lists | `arr.map((item, i) => <Item key={i} />)` | Use stable unique ID: `key={item.id}` |
| Large bundle from unused imports | Importing entire libraries (`import _ from 'lodash'`) | Use tree-shakable imports (`import debounce from 'lodash/debounce'`) |
| No code splitting | All routes loaded upfront | `React.lazy()` + `Suspense` for route-based splitting |
| Image without dimensions | `<img src={url} />` without width/height | Causes layout shift — set dimensions or use `next/image` |

---

## Next.js Specifics (App Router / Next.js 14-15)

### Server vs Client Components

| Principle | Details |
|---|---|
| Default is Server Component | Do not add `'use client'` unless needed |
| `'use client'` required when | Using hooks (`useState`, `useEffect`), browser APIs, event handlers, or React context |
| Keep `'use client'` boundary low | Put it on the smallest component that needs interactivity, not a whole page |
| Server Components cannot | Import client-only code, use hooks, or access browser APIs |
| Client Components cannot | Use `async/await` directly, access filesystem, or use server-only packages |

```tsx
// BAD: entire page is client component because of one button
'use client';
export default function ProductPage({ params }: { params: { id: string } }) {
  const product = useProduct(params.id); // client fetch
  return (
    <div>
      <h1>{product.name}</h1>
      <p>{product.description}</p>
      <AddToCartButton productId={product.id} />
    </div>
  );
}

// GOOD: server component page with client island
// app/products/[id]/page.tsx (Server Component)
export default async function ProductPage({ params }: { params: { id: string } }) {
  const product = await getProduct(params.id); // direct DB/API call
  return (
    <div>
      <h1>{product.name}</h1>
      <p>{product.description}</p>
      <AddToCartButton productId={product.id} /> {/* client island */}
    </div>
  );
}

// components/AddToCartButton.tsx
'use client';
export function AddToCartButton({ productId }: { productId: string }) {
  const [adding, setAdding] = useState(false);
  // ... interactive logic
}
```

### Data Fetching

| Anti-pattern | Correct Pattern |
|---|---|
| `useEffect` fetch in server component page | Fetch directly in the async server component |
| `getServerSideProps` in App Router | Use async server components or `generateMetadata` |
| Waterfall fetches (sequential `await`) | Parallel fetches with `Promise.all()` or parallel data segments |
| No loading/error states | Use `loading.tsx` and `error.tsx` in route segments |
| Fetching same data in parent and child | Fetch once in parent, pass as props; or use React cache |

### Route Handlers & Middleware

| What to Check | Flag If |
|---|---|
| Route handler without input validation | `request.json()` used without schema validation |
| Middleware doing heavy computation | Middleware runs on every request — keep it fast |
| Missing auth check in API route handlers | POST/PUT/DELETE handlers without authentication |
| `NextResponse.json()` without status code | Defaults to 200; set explicit 201, 400, etc. |

---

## TypeScript with React

### Props Typing

| Anti-pattern | Correct Pattern |
|---|---|
| `props: any` | Define an interface: `interface ButtonProps { ... }` |
| Extending HTML attributes manually | `interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>` |
| Not typing children | Use `React.PropsWithChildren<Props>` or `children: React.ReactNode` |
| Inline type in component signature | Extract to named interface above the component |

### Event Handler Types

```tsx
// BAD: any or missing type
const handleChange = (e: any) => { ... }

// GOOD: specific event types
const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => { ... }
const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => { ... }
const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => { ... }
```

### Ref Types

```tsx
// BAD: untyped ref
const inputRef = useRef(null);

// GOOD: typed ref
const inputRef = useRef<HTMLInputElement>(null);
```

---

## Accessibility

| What to Check | Flag If | Fix |
|---|---|---|
| Click handlers on `<div>` / `<span>` | Non-interactive element used as button | Use `<button>` or add `role="button"`, `tabIndex={0}`, and keyboard handler |
| Images without `alt` | `<img>` missing `alt` attribute | Add descriptive `alt` text; use `alt=""` for decorative images |
| Form inputs without labels | `<input>` without associated `<label>` or `aria-label` | Add `<label htmlFor={id}>` or `aria-label` |
| Color as sole indicator | Status shown only by color (red/green) | Add text, icon, or pattern alongside color |
| Missing heading hierarchy | `<h1>` followed by `<h3>` (skipping `<h2>`) | Maintain sequential heading levels |
| Auto-focus without reason | `autoFocus` on non-primary inputs | Only auto-focus the primary action input |
| Modal without focus trap | Focus escapes modal to background content | Use a focus-trap library or `<dialog>` element |

---

## Anti-pattern Summary

| Pattern | Signal | Severity |
|---|---|---|
| Prop drilling > 3 levels | Same prop threaded through 3+ wrapper components | Minor |
| Massive `useEffect` (> 20 lines, multiple concerns) | Single effect with unrelated logic | Major |
| Derived state stored in `useState` | `useEffect` that sets state based on other state | Major |
| `useEffect` as event handler | Effect that runs on mount to handle something that should be an event | Major |
| Missing error boundary | No `ErrorBoundary` wrapping async UI sections | Minor |
| Unnecessary `'use client'` on data-display components | Component only renders props, no interactivity | Minor |
| `suppressHydrationWarning` used broadly | Masking real hydration mismatches | Major |
| Direct DOM manipulation in React | `document.getElementById` instead of refs | Major |
