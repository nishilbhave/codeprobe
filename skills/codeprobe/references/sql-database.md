# SQL & Database Reference Guide

## Query Optimization

### WHERE Clause & Indexing

| Anti-pattern | Why It's Slow | Fix |
|---|---|---|
| `SELECT *` from large tables | Fetches unused columns, prevents covering indexes | Select only needed columns: `SELECT id, name, email` |
| Function on indexed column in WHERE | `WHERE YEAR(created_at) = 2025` cannot use index | Rewrite: `WHERE created_at >= '2025-01-01' AND created_at < '2026-01-01'` |
| `LIKE '%search%'` (leading wildcard) | Cannot use B-tree index | Use full-text index or `LIKE 'search%'` if prefix suffices |
| `OR` on different columns | Prevents single index usage | Use `UNION` or restructure query |
| Implicit type conversion | `WHERE varchar_col = 123` — casts every row | Match types: `WHERE varchar_col = '123'` |
| `NOT IN` with subquery that can return NULL | `NOT IN (NULL, ...)` is always empty set | Use `NOT EXISTS` instead |

### EXPLAIN Plan Reading

| What to Look For | Indicates Problem |
|---|---|
| `type: ALL` (full table scan) | Missing index for the WHERE/JOIN condition |
| `rows` estimate much larger than result | Poor selectivity or stale statistics |
| `Using filesort` | Sorting not covered by index — consider index on ORDER BY column |
| `Using temporary` | Temp table for GROUP BY/DISTINCT — consider covering index |
| `Select tables optimized away` | Query resolved entirely from index (good) |
| Nested loop join with large outer table | Consider join order or add index on join column |

### Join Optimization

| Anti-pattern | Fix |
|---|---|
| Joining on non-indexed column | Add index on the join column of the larger table |
| Cartesian product (missing JOIN condition) | Ensure every JOIN has an ON clause |
| Subquery in SELECT list (correlated) | Rewrite as JOIN to execute once |
| `JOIN` when `EXISTS` suffices (you only check existence) | `WHERE EXISTS (SELECT 1 FROM ...)` avoids materializing rows |

---

## N+1 Detection by ORM

### Patterns That Cause N+1

| Code Pattern | N+1 Trigger | Fix |
|---|---|---|
| Looping over results and accessing a relation | Each iteration fires a query for the relation | Eager load before the loop |
| Template rendering related objects | `{{ post.author.name }}` in template loops | Eager load in the query that feeds the template |
| Serializer accessing nested relations | JSON serialization triggers lazy loads per object | Load relations before serialization |

### Eager Loading by ORM

| ORM | Eager Load Syntax | Notes |
|---|---|---|
| Laravel Eloquent | `::with('relation')` | Use `::with(['rel1', 'rel2.nested'])` for multiple |
| Django ORM | `select_related('fk')` / `prefetch_related('m2m')` | `select_related` = SQL JOIN; `prefetch_related` = separate query |
| SQLAlchemy | `joinedload(Model.rel)` / `selectinload(Model.rel)` | Import from `sqlalchemy.orm` |
| Prisma | `include: { relation: true }` | Nested: `include: { posts: { include: { comments: true } } }` |
| ActiveRecord | `.includes(:relation)` | Also `.eager_load` (JOIN) and `.preload` (separate query) |

---

## Indexing Strategy

### Index Types & When to Use

| Index Type | Use When | Example |
|---|---|---|
| Single-column B-tree | Column appears in WHERE, ORDER BY, or JOIN | `CREATE INDEX idx_users_email ON users(email)` |
| Composite index | Multiple columns queried together | `CREATE INDEX idx_orders_user_status ON orders(user_id, status)` |
| Covering index | Query can be satisfied entirely from the index | Include all SELECT columns in the index |
| Partial/filtered index | Only a subset of rows is queried | `CREATE INDEX idx_active_users ON users(email) WHERE active = true` |
| Unique index | Enforce uniqueness constraint | `CREATE UNIQUE INDEX idx_users_email ON users(email)` |

### Composite Index Column Order

The leftmost prefix rule: a composite index on `(a, b, c)` can satisfy queries on `(a)`, `(a, b)`, and `(a, b, c)` but NOT `(b)` or `(b, c)` alone.

| Query WHERE Clause | Index `(user_id, status, created_at)` Used? |
|---|---|
| `WHERE user_id = 1` | Yes (leftmost prefix) |
| `WHERE user_id = 1 AND status = 'active'` | Yes |
| `WHERE user_id = 1 AND status = 'active' AND created_at > '...'` | Yes (full index) |
| `WHERE status = 'active'` | No (missing leftmost column) |
| `WHERE user_id = 1 AND created_at > '...'` | Partial (uses user_id only, skips status) |

### Over-indexing Warnings

| Flag | Why |
|---|---|
| More than 6 indexes on a single table | Slows down INSERT/UPDATE/DELETE operations |
| Index on low-cardinality column (e.g., boolean) | Index scan is not faster than table scan for 2 distinct values |
| Redundant indexes (e.g., `(a)` and `(a, b)`) | The composite `(a, b)` already covers queries on `(a)` alone |
| Index on rarely-queried column | Write overhead without read benefit |

---

## Migration Patterns

### Safe Migration Sequence

For adding a NOT NULL column to a large production table:

1. **Add column as nullable**: `ALTER TABLE ADD COLUMN new_col TYPE NULL`
2. **Deploy code** that writes to the new column
3. **Backfill** existing rows in batches (not a single UPDATE)
4. **Add NOT NULL constraint** once all rows are populated
5. **Add default** if needed

| Dangerous Migration | Why | Safe Alternative |
|---|---|---|
| `ALTER TABLE ADD COLUMN col INT NOT NULL DEFAULT 0` on large table | Locks table for duration of backfill in some databases | Add nullable first, backfill in batches, then add constraint |
| `ALTER TABLE RENAME COLUMN` | Breaks running application code | Add new column, dual-write, migrate reads, drop old column |
| `DROP COLUMN` in a single deploy | Running code still references the column | Stop referencing the column first, deploy, then drop |
| Large data migration in a single transaction | Holds locks for minutes/hours | Batch process: `UPDATE ... WHERE id BETWEEN ? AND ? LIMIT 1000` |
| Adding index without `CONCURRENTLY` (PostgreSQL) | Locks table for writes during index build | `CREATE INDEX CONCURRENTLY` |

### Rollback Strategy

| Principle | Details |
|---|---|
| Every migration should be reversible | Write `down()` / rollback for every `up()` |
| Test rollback before deploying | Run `migrate:rollback` in staging |
| Data-destructive migrations need backup plan | Dropping columns/tables: ensure data is backed up or no longer needed |

---

## Transactions

### When to Use

| Scenario | Transaction Required | Why |
|---|---|---|
| Creating parent + children records | Yes | Partial creation leaves orphaned/incomplete data |
| Transfer between accounts (debit + credit) | Yes | Must be atomic — both or neither |
| Read-then-write (check then update) | Yes (with appropriate isolation) | Race condition without transaction |
| Single INSERT | Usually no | Single statement is atomic by itself |
| Bulk read-only queries | Depends | Use for consistent snapshot reads |

### Transaction Scope

| Anti-pattern | Why | Fix |
|---|---|---|
| Transaction wrapping an entire request | Holds locks too long; blocks other operations | Narrow the transaction to just the critical writes |
| External API call inside transaction | Network latency holds DB locks | Move API call outside the transaction |
| User interaction inside transaction | Transaction held open for seconds/minutes | Complete transaction before returning to user |

### Deadlock Prevention

| Practice | Details |
|---|---|
| Consistent lock ordering | Always lock tables/rows in the same order across all transactions |
| Short transactions | Minimize the window where locks are held |
| Avoid lock escalation | Update specific rows (`WHERE id = ?`), not ranges |
| Set lock timeout | `SET lock_timeout = '5s'` (PostgreSQL) to fail fast |

---

## Common Anti-patterns

| Anti-pattern | Detection Signal | Why It's Wrong | Fix |
|---|---|---|---|
| Storing queryable data as JSON blob | `JSON` column queried with `JSON_EXTRACT` in WHERE | Cannot be indexed efficiently; slow queries at scale | Normalize into columns or a related table |
| Entity-Attribute-Value (EAV) pattern | Table with `entity_id`, `attribute_name`, `attribute_value` columns | Destroys type safety, makes queries complex, cannot use constraints | Use concrete columns or `jsonb` with GIN index for truly dynamic data |
| Polymorphic association without proper FK | `commentable_type` + `commentable_id` without DB-level FK | No referential integrity; orphaned records possible | Use separate join tables per type or a shared base table with FKs |
| Missing foreign keys | Related tables without FK constraints | Orphaned records accumulate silently | Add FK constraints with appropriate ON DELETE behavior |
| Soft delete without index | `deleted_at` column but queries don't filter on it | Every query must add `WHERE deleted_at IS NULL` | Add partial index on `deleted_at IS NULL` and ensure all queries filter |
| `ENUM` in database | Column uses database-level ENUM type | Schema changes require migration; limited portability | Use `VARCHAR` with application-level validation or a lookup table |

---

## Performance Patterns

### Pagination

| Method | Pros | Cons | Use When |
|---|---|---|---|
| Offset-based: `LIMIT 20 OFFSET 100` | Simple, supports jump-to-page | Slow for deep pages (scans skipped rows) | Total items < 10K, UI needs page numbers |
| Cursor-based: `WHERE id > ? LIMIT 20` | Consistent performance at any depth | No jump-to-page, cursor must be opaque | Large datasets, infinite scroll, APIs |

```sql
-- BAD: offset pagination on page 500
SELECT * FROM orders ORDER BY id LIMIT 20 OFFSET 10000;
-- Scans 10,020 rows, discards 10,000

-- GOOD: cursor pagination
SELECT * FROM orders WHERE id > 9980 ORDER BY id LIMIT 20;
-- Seeks directly to the cursor position
```

### Batch Processing

| Anti-pattern | Fix |
|---|---|
| `UPDATE users SET status = 'inactive'` on 1M rows | Batch: `UPDATE users SET status = 'inactive' WHERE id BETWEEN ? AND ? LIMIT 1000` |
| Loading entire table into application memory | Use cursor/chunk: Django `.iterator()`, Laravel `chunk()`, SQLAlchemy `yield_per()` |
| `COUNT(*)` on a table with millions of rows | Use approximate count: `pg_class.reltuples` (PostgreSQL) or cache the count |

### Materialized Views

| Use When | Notes |
|---|---|
| Complex aggregation queries run repeatedly | Pre-compute and refresh on schedule |
| Dashboard statistics | Refresh every N minutes instead of computing live |
| Reporting queries that JOIN multiple large tables | Single materialized result is faster to query |

---

## Data Integrity

### Constraints Checklist

| Constraint | Flag If Missing | Why |
|---|---|---|
| Foreign keys | Related tables have no FK constraints | Orphaned data, broken references |
| NOT NULL | Column allows NULL but business logic never expects NULL | Null propagation bugs, ambiguous queries |
| UNIQUE | Business-unique columns (email, slug) lack unique constraint | Duplicate records that application code doesn't catch |
| CHECK | Numeric ranges or status values have no CHECK constraint | Invalid data enters the database |
| DEFAULT | Columns without defaults that are always populated | INSERT failures when application code doesn't supply value |

```sql
-- BAD: no constraints
CREATE TABLE orders (
    id SERIAL,
    user_id INTEGER,
    status TEXT,
    total NUMERIC
);

-- GOOD: proper constraints
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled')),
    total NUMERIC(10,2) NOT NULL CHECK (total >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status) WHERE status NOT IN ('delivered', 'cancelled');
```
