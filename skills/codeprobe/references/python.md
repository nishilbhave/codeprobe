# Python Reference Guide

## PEP 8 & Pythonic Code

### Naming Conventions

| Element | Convention | Flag If |
|---|---|---|
| Variables, functions | `snake_case` | `camelCase` or `mixedCase` used |
| Classes | `PascalCase` | `snake_case` or `ALLCAPS` used |
| Constants | `UPPER_SNAKE_CASE` | Mutable module-level variable pretending to be constant |
| Private members | `_leading_underscore` | `__double_leading` used without name-mangling intent |
| Modules, packages | `short_lowercase` | Hyphens in module names (`my-module`) |

### Pythonic Patterns

| Anti-pattern | Pythonic Alternative |
|---|---|
| `for i in range(len(items)):` then `items[i]` | `for item in items:` |
| Building list with loop + `append` | List comprehension: `[transform(x) for x in items]` |
| `if len(items) == 0:` | `if not items:` |
| `if x == True:` / `if x == None:` | `if x:` / `if x is None:` |
| Manual file open/close | Context manager: `with open(path) as f:` |
| String concatenation in a loop | `''.join(parts)` or f-strings |
| `dict.has_key(k)` or `k in dict.keys()` | `k in dict` |
| Nested `if` for guard clauses | Early return: `if not condition: return` |

```python
# BAD
result = []
for item in data:
    if item.active:
        result.append(item.name.upper())

# GOOD
result = [item.name.upper() for item in data if item.active]

# BAD
greeting = "Hello, " + name + "! You have " + str(count) + " messages."

# GOOD
greeting = f"Hello, {name}! You have {count} messages."
```

---

## Type Hints (Python 3.10+)

### Modern Syntax

| Old Style | Modern Style (3.10+) | Notes |
|---|---|---|
| `Optional[str]` | `str \| None` | PEP 604 union syntax |
| `Union[int, str]` | `int \| str` | Simpler union |
| `List[str]` | `list[str]` | PEP 585 built-in generics |
| `Dict[str, int]` | `dict[str, int]` | No import needed |
| `Tuple[int, ...]` | `tuple[int, ...]` | Built-in generic |

### Type Hint Best Practices

| What to Check | Flag If |
|---|---|
| Public function signatures | Missing return type annotation |
| `Any` usage | Used as a shortcut to avoid proper typing |
| Mismatch between annotation and runtime | Function annotated `-> str` but returns `None` without `\| None` |
| `TypedDict` for structured dicts | Raw `dict[str, Any]` for well-known shapes |
| Protocol classes | Using ABC when structural typing (Protocol) is sufficient |

```python
# BAD: no types, uses Any
def process(data: Any) -> Any:
    return data["name"]

# GOOD: typed with TypedDict
class UserData(TypedDict):
    name: str
    email: str
    age: int

def process(data: UserData) -> str:
    return data["name"]
```

---

## Django

### Model Design

| Anti-pattern | Correct Pattern | Why |
|---|---|---|
| Business logic in models > 50 LOC | Extract into service layer or manager | Models should handle data, not orchestration |
| `CharField` without `max_length` | Always specify `max_length` | Database constraint enforcement |
| No `__str__` method on model | Define `__str__` for admin and debugging | Avoids `<Object (1)>` display |
| `blank=True` without `null=True` on non-string fields | Add `null=True` for non-string nullable fields | String fields use `blank=True` only; others need both |
| No `Meta.ordering` or inconsistent ordering | Define default ordering or always use `.order_by()` | Prevents nondeterministic query results |

### QuerySet Optimization (N+1)

| Anti-pattern | Fix | When to Use |
|---|---|---|
| Accessing `obj.related_fk` in a loop | `queryset.select_related('related_fk')` | ForeignKey, OneToOneField (SQL JOIN) |
| Accessing `obj.related_set.all()` in a loop | `queryset.prefetch_related('related_set')` | ManyToMany, reverse ForeignKey (separate query) |
| Chaining `select_related` + `prefetch_related` wrong | `select_related` for FK/OneToOne; `prefetch_related` for M2M/reverse | Know which one to use |
| `queryset.count()` when you already fetched results | `len(queryset)` if already evaluated | Avoid extra COUNT query |

```python
# BAD: N+1 queries
for order in Order.objects.all():
    print(order.customer.name)       # FK hit per iteration
    print(order.items.count())       # M2M hit per iteration

# GOOD: eager loading
orders = Order.objects.select_related('customer').prefetch_related('items')
for order in orders:
    print(order.customer.name)       # no extra query
    print(order.items.count())       # no extra query (use len() for prefetched)
```

### Django Security

| What to Check | Flag If | Fix |
|---|---|---|
| Raw SQL | `raw()`, `extra()`, `RawSQL()` with user input | Use ORM queries or parameterized raw: `.raw('SELECT ... WHERE id = %s', [user_id])` |
| Form validation | Logic in view instead of form/serializer | Move validation to `Form.clean()` or `Serializer.validate()` |
| Middleware order | Auth middleware after view processing middleware | Auth must come before permission-dependent middleware |
| Signals | Heavy logic in signal handlers | Signals should be thin — dispatch to services |
| `@csrf_exempt` | Applied broadly or without justification | Only exempt webhook endpoints; document why |

---

## FastAPI

### Patterns to Check

| Anti-pattern | Correct Pattern | Why |
|---|---|---|
| Dict return type without Pydantic model | Define `response_model` with Pydantic class | No validation, no documentation |
| Sync endpoint doing I/O | Use `async def` + async DB driver | Blocks the event loop |
| No dependency injection for shared resources | Use `Depends()` for DB sessions, auth, config | Testability and lifecycle management |
| Missing status codes on responses | Set `status_code=201` for creation endpoints | Accurate HTTP semantics |
| Background task doing critical work | Use a task queue (Celery, arq) for reliable processing | Background tasks are fire-and-forget; no retry |

```python
# BAD: no validation, no response model, sync I/O
@app.post("/users")
def create_user(request: Request):
    data = request.json()
    user = db.execute(f"INSERT INTO users ...")  # SQL injection + sync
    return {"id": user.id}

# GOOD: Pydantic models, async, dependency injection
class CreateUserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr

class UserResponse(BaseModel):
    id: int
    name: str
    email: str

@app.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    payload: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
):
    user = User(**payload.model_dump())
    db.add(user)
    await db.commit()
    return user
```

---

## Flask

### Application Factory Pattern

| Anti-pattern | Correct Pattern |
|---|---|
| Global `app = Flask(__name__)` at module level | Use `create_app()` factory function |
| Circular imports from app module | Use blueprints to organize routes |
| Config hardcoded in source | Load from environment or config object |

```python
# BAD: global app, no factory
app = Flask(__name__)
app.config["SECRET_KEY"] = "hardcoded-secret"

@app.route("/")
def index():
    return "hello"

# GOOD: factory pattern
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    from .routes import main_bp
    app.register_blueprint(main_bp)

    return app
```

---

## Error Handling

| Anti-pattern | Why | Correct Pattern |
|---|---|---|
| Bare `except:` | Catches `SystemExit`, `KeyboardInterrupt`, everything | `except Exception:` at minimum |
| `except Exception as e: pass` | Silently swallows all errors | Log the error or re-raise |
| Overly broad try block | Masks which operation failed | Narrow the try to the specific risky call |
| No custom exception hierarchy | All errors look the same to callers | Create domain-specific exception classes |
| String formatting in log call | Formatted even if log level is disabled | Use lazy formatting: `logger.error("Failed for %s", user_id)` |

```python
# BAD
try:
    user = get_user(id)
    orders = get_orders(user)
    report = generate_report(orders)
    send_email(user, report)
except:
    pass

# GOOD
try:
    user = get_user(id)
except UserNotFoundError:
    logger.warning("User %s not found", id)
    raise

try:
    report = generate_report(get_orders(user))
except ReportGenerationError as e:
    logger.error("Report generation failed for user %s: %s", id, e)
    raise
```

---

## Performance

| Anti-pattern | Why | Better Pattern |
|---|---|---|
| `list(range(1_000_000))` when iterating | Materializes entire list in memory | Use `range()` directly — it's a lazy iterator |
| List comprehension for large datasets | Builds full list in memory | Generator expression: `(x for x in items)` |
| Missing `__slots__` on data-heavy classes | Each instance carries a `__dict__` overhead | Add `__slots__` for memory-critical classes |
| Global mutable state | Thread-safety issues, hidden dependencies | Pass state explicitly or use dependency injection |
| String concatenation in loop | Quadratic time complexity | `''.join()` or `io.StringIO` |
| Repeated attribute lookups in hot loop | Dot lookups add overhead | Assign to local: `_len = len` before loop |

---

## Testing

### pytest Patterns

| What to Check | Flag If | Best Practice |
|---|---|---|
| Test naming | `test1`, `test_it_works` | Name describes behavior: `test_expired_token_returns_401` |
| Fixtures | Setup duplicated across tests | Extract to `@pytest.fixture` |
| Parametrize | Multiple test functions with same logic, different inputs | Use `@pytest.mark.parametrize` |
| Mocking | Mocking the function under test | Mock external dependencies, not the subject |
| Assertions | Single `assert True` or bare `assert` | Assert specific values and error messages |
| Test isolation | Tests depend on execution order | Each test must be independently runnable |

```python
# BAD: duplicated setup, vague name, weak assertion
def test_user():
    user = User(name="Alice", email="alice@example.com")
    db.session.add(user)
    db.session.commit()
    assert user.id

def test_user2():
    user = User(name="Bob", email="bob@example.com")
    db.session.add(user)
    db.session.commit()
    assert user.id

# GOOD: fixture, parametrize, clear naming
@pytest.fixture
def make_user(db_session):
    def _make(name="Alice", email="alice@example.com"):
        user = User(name=name, email=email)
        db_session.add(user)
        db_session.commit()
        return user
    return _make

@pytest.mark.parametrize("name,email", [
    ("Alice", "alice@example.com"),
    ("Bob", "bob@example.com"),
])
def test_created_user_has_id(make_user, name, email):
    user = make_user(name=name, email=email)
    assert user.id is not None
    assert user.name == name
```

---

## Security

| Vulnerability | Detection Signal | Fix |
|---|---|---|
| SQL injection | `cursor.execute(f"SELECT ... {user_input}")` | Use parameterized queries: `cursor.execute("SELECT ... WHERE id = %s", (user_id,))` |
| Path traversal | `open(base_path + user_input)` | Validate and sanitize path; use `pathlib.Path.resolve()` and check it starts with allowed base |
| SSRF | `requests.get(user_provided_url)` without validation | Validate URL scheme and host against allowlist |
| Pickle deserialization | `pickle.loads(untrusted_data)` | Never unpickle untrusted data; use JSON or a safe alternative |
| `eval()` / `exec()` | Called with any user-influenced input | Almost never needed; use `ast.literal_eval()` for safe subset |
| Hardcoded secrets | `API_KEY = "sk-live-..."` in source files | Use environment variables or secrets manager |
| `DEBUG = True` in production | Django `settings.py` or `.env` with `DEBUG=True` | Ensure `DEBUG = False` in production settings |
