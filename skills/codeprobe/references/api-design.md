# API Design Reference Guide

## REST Conventions

### Resource Naming

| Rule | Correct | Wrong |
|---|---|---|
| Plural nouns for collections | `/users`, `/orders` | `/user`, `/getOrders`, `/order-list` |
| Nested resources for ownership | `/users/{id}/orders` | `/orders?user_id={id}` (acceptable but less clear) |
| No verbs in URLs | `POST /orders` | `POST /createOrder` |
| Kebab-case for multi-word | `/order-items` | `/orderItems`, `/order_items` |
| No trailing slashes (be consistent) | `/users` | Mixed `/users` and `/users/` |
| Resource IDs in path, filters in query | `/users/123`, `/users?status=active` | `/users/status/active` |

### HTTP Method Semantics

| Method | Purpose | Idempotent | Request Body | Success Code |
|---|---|---|---|---|
| `GET` | Read resource(s) | Yes | No | 200 |
| `POST` | Create resource | No | Yes | 201 |
| `PUT` | Full replacement of resource | Yes | Yes | 200 |
| `PATCH` | Partial update | No* | Yes | 200 |
| `DELETE` | Remove resource | Yes | No | 204 |

*PATCH can be idempotent depending on implementation; treat as non-idempotent for safety.

| Anti-pattern | Why | Fix |
|---|---|---|
| `GET` with side effects | GET must be safe; caches, crawlers, and prefetch trigger GET | Use POST for state changes |
| `POST` for reads | Misuses HTTP semantics | Use GET with query parameters |
| `DELETE` returning 200 with body | Convention is 204 No Content | Return 204 with empty body |
| `PUT` for partial updates | PUT means full replacement — missing fields get nulled | Use PATCH for partial updates |

---

## Status Codes

### Use the Right Code

| Code | Meaning | Use When |
|---|---|---|
| **200** OK | Successful GET, PUT, PATCH | Returning data after successful operation |
| **201** Created | Successful POST that created a resource | Include `Location` header with URL of new resource |
| **204** No Content | Successful DELETE or action with no response body | No body should be sent |
| **400** Bad Request | Malformed request syntax | JSON parse error, missing required field, wrong type |
| **401** Unauthorized | Not authenticated | No token, expired token, invalid token |
| **403** Forbidden | Authenticated but not authorized | User exists but lacks permission for this action |
| **404** Not Found | Resource doesn't exist | Also use for resources the user can't know about (security) |
| **409** Conflict | State conflict | Duplicate resource (email taken), version conflict |
| **422** Unprocessable Entity | Validation failure on semantically valid request | Business rule violation: "balance too low", "date in past" |
| **429** Too Many Requests | Rate limit exceeded | Include `Retry-After` header |
| **500** Internal Server Error | Unexpected server failure | Never intentionally return this — fix the bug |

### Common Mistakes

| Anti-pattern | Why It's Wrong | Fix |
|---|---|---|
| 200 for everything (error in body) | Clients can't use status code for branching | Return appropriate 4xx/5xx codes |
| 500 for validation errors | 500 means server bug, not user error | Return 400 or 422 |
| 401 when you mean 403 | 401 = "who are you?", 403 = "you can't do this" | Use 401 for auth, 403 for authz |
| 404 for method not allowed | Resource exists, method is wrong | Return 405 Method Not Allowed |
| Returning 200 with `{ "success": false }` | Hides the error from HTTP-level clients | Return proper status code |

---

## Error Response Format

### Standard Structure (RFC 7807 Problem Details)

```json
{
  "type": "https://api.example.com/errors/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "The request body contains invalid fields.",
  "instance": "/orders/create",
  "errors": [
    {
      "field": "email",
      "code": "INVALID_FORMAT",
      "message": "Must be a valid email address."
    },
    {
      "field": "quantity",
      "code": "OUT_OF_RANGE",
      "message": "Must be between 1 and 100."
    }
  ]
}
```

### Error Format Rules

| Rule | Why |
|---|---|
| Consistent structure across all endpoints | Clients should parse errors the same way everywhere |
| Machine-readable error codes (e.g., `INVALID_FORMAT`) | Enables programmatic error handling without parsing messages |
| Human-readable messages | For display to users or developer debugging |
| Field-level errors for validation | Client can highlight specific form fields |
| No stack traces in production | Security risk — leaks internals |
| Include request ID for tracing | `"request_id": "req_abc123"` enables support debugging |

---

## Versioning

### Approaches

| Method | Example | Pros | Cons |
|---|---|---|---|
| URL path | `/v1/users` | Simple, explicit, easy to route | URL changes for every version |
| Header | `Accept: application/vnd.api+json; version=2` | Clean URLs | Hidden, harder to test in browser |
| Query param | `/users?version=2` | Easy to test | Clutters query string |

**Recommendation:** URL path versioning (`/v1/`) is the most widely adopted and debuggable approach.

### Deprecation Strategy

| Practice | Details |
|---|---|
| `Deprecation` header | Include `Deprecation: true` and `Sunset: <date>` headers on deprecated endpoints |
| Overlap period | Run old and new versions simultaneously for at least 3-6 months |
| Documentation | Clearly document what changed and migration path |
| Usage tracking | Monitor traffic to deprecated endpoints before removal |

---

## Pagination

### Cursor-based (Recommended for APIs)

```json
{
  "data": [...],
  "pagination": {
    "next_cursor": "eyJpZCI6MTAwfQ==",
    "has_more": true
  }
}
```

| Rule | Details |
|---|---|
| Cursor should be opaque | Base64-encoded; client should not parse it |
| Include `has_more` boolean | Easier than checking `data.length < limit` |
| Default page size | 20-50 items; document it |
| Max page size | Cap at 100; reject larger requests |

### Offset-based

```json
{
  "data": [...],
  "pagination": {
    "page": 2,
    "per_page": 20,
    "total": 354,
    "total_pages": 18
  }
}
```

| Anti-pattern | Why | Fix |
|---|---|---|
| No pagination on list endpoints | Returns unbounded data; crashes clients or server | Always paginate collections |
| `total` count on large tables | `COUNT(*)` is expensive | Make total optional, omit for large datasets, or use estimate |
| Page size > 100 | Slow responses, excessive memory | Enforce max page size server-side |
| No default page size | Clients must always specify | Default to 20-50 if not provided |

---

## Rate Limiting

### Headers

| Header | Purpose | Example |
|---|---|---|
| `X-RateLimit-Limit` | Max requests allowed in window | `100` |
| `X-RateLimit-Remaining` | Requests remaining in current window | `47` |
| `X-RateLimit-Reset` | Unix timestamp when window resets | `1709251200` |
| `Retry-After` | Seconds until client can retry (on 429) | `30` |

### 429 Response

```json
{
  "type": "https://api.example.com/errors/rate-limit",
  "title": "Too Many Requests",
  "status": 429,
  "detail": "Rate limit of 100 requests per minute exceeded.",
  "retry_after": 30
}
```

| What to Check | Flag If |
|---|---|
| No rate limiting on public endpoints | Any unauthenticated endpoint without rate limits |
| Rate limit on read but not write | Write endpoints (POST/PUT/DELETE) are more dangerous to abuse |
| Missing `Retry-After` header on 429 | Client doesn't know when to retry |
| Rate limit per IP only | Authenticated endpoints should rate limit per user/token |

---

## Authentication

### Bearer Token Pattern

```
Authorization: Bearer <token>
```

| What to Check | Flag If |
|---|---|
| Token in URL query parameter | `?token=abc123` — logged in server access logs, browser history, referrer headers |
| Token in cookie without `HttpOnly` | Accessible to JavaScript — XSS can steal it |
| No token expiration | Compromised token works forever |
| No token refresh mechanism | Users forced to re-authenticate when token expires |

### API Key Pattern

| Rule | Details |
|---|---|
| Pass in header, not URL | `X-API-Key: <key>` — avoid query string exposure |
| Prefix keys for identification | `sk_live_`, `pk_test_` — makes it clear what the key is for |
| Allow key rotation | Support multiple active keys per account for zero-downtime rotation |
| Scope keys | Limit what each key can access (read-only, admin, specific resources) |

### OAuth Flows

| Flag | Why |
|---|---|
| Implicit flow (response_type=token) | Deprecated in OAuth 2.1 — use Authorization Code + PKCE |
| No `state` parameter in authorize URL | CSRF vulnerability |
| Refresh token without rotation | Compromised refresh token is permanent — rotate on use |
| No PKCE for public clients (SPAs, mobile) | Authorization code can be intercepted without PKCE |

---

## Request/Response Design

### Naming Consistency

| Rule | Details |
|---|---|
| Pick one convention and keep it | `camelCase` or `snake_case` — never mix in the same API |
| Match the platform convention | JavaScript APIs typically use `camelCase`; Python/Ruby APIs use `snake_case` |
| Consistent date format | Always ISO 8601: `2025-03-15T14:30:00Z` |
| Consistent ID format | Use string UUIDs or integer IDs — not both |
| Null vs absent | Define policy: omit null fields or include them explicitly |

### Envelope vs Flat

```json
// Envelope (recommended for collections)
{
  "data": [{ "id": 1, "name": "Alice" }],
  "pagination": { "next_cursor": "abc", "has_more": true },
  "meta": { "request_id": "req_123" }
}

// Flat (acceptable for single resources)
{
  "id": 1,
  "name": "Alice",
  "email": "alice@example.com"
}
```

| Anti-pattern | Why | Fix |
|---|---|---|
| Inconsistent response wrapping | `{ "data": [...] }` on some endpoints, bare array on others | Always wrap collections in `data` key |
| Array as top-level response | JSON hijacking risk (historical); harder to extend | Wrap in object: `{ "data": [...] }` |
| Including sensitive data by default | User objects returning password hashes, internal IDs | Explicit field selection; never return secrets |
| Inconsistent null handling | Same field is `null` in one response and missing in another | Pick a convention and enforce it |

### Partial Responses

```
GET /users/123?fields=id,name,email
```

| Practice | Details |
|---|---|
| Support field selection for large resources | Reduces payload and processing |
| Always include `id` even if not requested | Client needs it for cache keys and operations |
| Document which fields are available | Don't let clients guess |

---

## GraphQL Patterns

### N+1 in Resolvers

| Anti-pattern | Why | Fix |
|---|---|---|
| Resolver fetches related data per-object | 1 query per resolver call = N+1 | Use DataLoader for batching |
| No DataLoader for nested relations | `user.posts` resolver fires per user | Batch: collect IDs, single query |

```typescript
// BAD: N+1 in resolver
const resolvers = {
  User: {
    posts: (user) => db.posts.findMany({ where: { userId: user.id } }),
    // Called once per user in the result set
  },
};

// GOOD: DataLoader batching
const postsByUserLoader = new DataLoader(async (userIds) => {
  const posts = await db.posts.findMany({ where: { userId: { in: userIds } } });
  return userIds.map(id => posts.filter(p => p.userId === id));
});

const resolvers = {
  User: {
    posts: (user) => postsByUserLoader.load(user.id),
  },
};
```

### Query Complexity

| What to Check | Flag If |
|---|---|
| No query depth limit | Deeply nested queries can crash the server: `{ user { posts { comments { author { posts { ... } } } } } }` |
| No complexity scoring | Single query can trigger thousands of DB rows |
| No persisted queries for production | Arbitrary client queries accepted without validation |

### Schema Design

| Anti-pattern | Fix |
|---|---|
| Giant `Query` type with all fields | Group into logical types: `Query.users`, `Query.orders` |
| `String` for everything | Use custom scalars: `DateTime`, `Email`, `URL` |
| No input types | Use `input CreateUserInput { ... }` for mutations |
| Nullable by default | Make fields non-null by default; nullable only when truly optional |
