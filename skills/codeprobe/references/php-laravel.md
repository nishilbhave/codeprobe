# PHP & Laravel Reference Guide

## Eloquent ORM

### N+1 Query Detection

| Anti-pattern | Correct Pattern | Why |
|---|---|---|
| Accessing `$post->comments` inside a loop without eager loading | `Post::with('comments')->get()` | Each loop iteration fires a separate SQL query |
| Nested eager loads missing: `$post->comments->user` | `Post::with('comments.user')->get()` | Second-level relations need dot notation |
| Lazy loading left enabled in production | Set `Model::preventLazyLoading(!app()->isProduction())` in `AppServiceProvider` | Catches N+1 in dev, avoids exceptions in prod |

```php
// BAD: N+1 — fires 1 + N queries
$posts = Post::all();
foreach ($posts as $post) {
    echo $post->author->name; // query per post
}

// GOOD: eager load — fires 2 queries total
$posts = Post::with('author')->get();
foreach ($posts as $post) {
    echo $post->author->name;
}
```

### Model Configuration

| What to Check | Flag If | Correct Pattern |
|---|---|---|
| `$casts` property | Date or JSON columns accessed without casting | Define `$casts` for all non-string columns |
| `$fillable` / `$guarded` | Neither is defined on a model | Always define `$fillable` (prefer allowlist over `$guarded`) |
| Accessors using old syntax | `getNameAttribute()` style in Laravel 9+ | Use `Attribute::make(get: fn () => ...)` |
| Missing `$table` on non-conventional names | Table name doesn't follow plural snake_case of class | Explicitly set `$table` |

```php
// BAD: no casts, old accessor syntax
class Order extends Model
{
    public function getTotalAttribute($value)
    {
        return $value / 100;
    }
}

// GOOD: modern casts and accessor
class Order extends Model
{
    protected $fillable = ['user_id', 'total', 'metadata', 'completed_at'];

    protected $casts = [
        'total' => 'integer',
        'metadata' => 'array',
        'completed_at' => 'datetime',
    ];

    protected function total(): Attribute
    {
        return Attribute::make(
            get: fn (int $value) => $value / 100,
            set: fn (float $value) => (int) ($value * 100),
        );
    }
}
```

### Query Scopes

```php
// BAD: duplicated where clauses across the codebase
User::where('status', 'active')->where('verified', true)->get();

// GOOD: reusable scope
class User extends Model
{
    public function scopeActive(Builder $query): Builder
    {
        return $query->where('status', 'active')->where('verified', true);
    }
}
User::active()->get();
```

### Raw Queries

| Flag | Reason | Fix |
|---|---|---|
| `DB::raw()` with interpolated variables | SQL injection risk | Use parameter binding: `DB::raw('YEAR(?) = ?', [$col, $year])` |
| `whereRaw()` when query builder works | Unnecessary complexity | Use `whereDate()`, `whereIn()`, etc. |
| `DB::select("SELECT * FROM ...")` | Bypasses Eloquent benefits | Use query builder or Eloquent unless truly needed |

---

## Controllers

### Thin Controller Principles

| Anti-pattern | Correct Pattern |
|---|---|
| Validation logic inline in controller | Use Form Request classes (`php artisan make:request`) |
| Business logic in controller methods | Delegate to service or action classes |
| Controller method > 20 LOC | Extract into service/action |
| Raw DB queries in controllers | Use repository or Eloquent model methods |

```php
// BAD: fat controller
public function store(Request $request)
{
    $request->validate(['email' => 'required|email']);
    $user = User::create($request->all());
    Mail::to($user)->send(new WelcomeEmail($user));
    event(new UserRegistered($user));
    return redirect('/dashboard');
}

// GOOD: thin controller + form request + service
public function store(StoreUserRequest $request, UserRegistrationService $service)
{
    $user = $service->register($request->validated());
    return redirect('/dashboard');
}
```

### Route Model Binding

```php
// BAD: manual find + null check
public function show(Request $request, $id)
{
    $post = Post::find($id);
    if (!$post) {
        abort(404);
    }
}

// GOOD: route model binding
public function show(Post $post)
{
    return view('posts.show', compact('post'));
}
```

---

## Service Container & Dependency Injection

| Pattern | When to Use | Anti-pattern |
|---|---|---|
| Constructor injection | Services, repositories, actions | Calling `app()` or `resolve()` inside methods |
| Interface binding | When swapping implementations (payment gateways, mail providers) | Hardcoding concrete class references |
| Facades | Quick prototyping, simple cases | Using facades in domain/service layer where DI is better |
| Service providers | Registering bindings, bootstrapping | Registering bindings in controllers or models |

```php
// BAD: service locator pattern
class OrderService
{
    public function process(Order $order)
    {
        $payment = app(PaymentGateway::class); // hidden dependency
        $mailer = resolve('mailer');            // untestable
    }
}

// GOOD: constructor injection
class OrderService
{
    public function __construct(
        private readonly PaymentGatewayInterface $payment,
        private readonly MailerInterface $mailer,
    ) {}
}
```

---

## Security

### Mass Assignment

| Flag | Severity | Fix |
|---|---|---|
| `$request->all()` passed to `create()` / `update()` | Critical | Use `$request->only([...])` or `$request->validated()` |
| Model missing both `$fillable` and `$guarded` | Major | Define `$fillable` with explicit field list |
| `$guarded = []` (empty guard) | Critical | Use `$fillable` instead — allowlist is safer |

### Environment & Configuration

| Anti-pattern | Why It Breaks | Correct Pattern |
|---|---|---|
| `env('APP_KEY')` called in application code | Returns `null` after `config:cache` | Use `config('app.key')` — `env()` only in config files |
| Hardcoded credentials in config files | Leaked in version control | Use `env()` in config, keep secrets in `.env` |
| `APP_DEBUG=true` in production `.env` | Leaks stack traces and internal paths | Set `APP_DEBUG=false` in production |

### CSRF

| Flag | Context |
|---|---|
| Form without `@csrf` directive | Any Blade form with `method="POST"` |
| Route excluded from CSRF without justification | `VerifyCsrfToken::$except` should only list webhook endpoints |

---

## Queues & Jobs

| What to Check | Flag If | Why |
|---|---|---|
| Long-running operations in request cycle | Email sending, PDF generation, API calls to external services in controllers | Should be dispatched as queued jobs |
| Job missing `$tries` | No retry configuration | Add `public int $tries = 3;` |
| Job missing `$timeout` | Could run indefinitely | Add `public int $timeout = 60;` |
| Non-idempotent job | Running the job twice causes duplicate side effects | Design jobs to be safely re-runnable |
| Missing `$backoff` | Retries hit immediately | Add `public int $backoff = 30;` or exponential array |

```php
// BAD: blocking the request
public function store(Request $request)
{
    $order = Order::create($request->validated());
    $pdf = PDF::generate($order);               // slow
    Mail::to($order->user)->send(new Invoice($pdf)); // slow
    return response()->json($order);
}

// GOOD: queue the slow work
public function store(Request $request)
{
    $order = Order::create($request->validated());
    GenerateInvoiceJob::dispatch($order);
    return response()->json($order, 201);
}
```

---

## Events & Observers

| Pattern | Use When | Anti-pattern |
|---|---|---|
| Events + Listeners | Side effects that other modules care about (notifications, audit logging) | Putting the side effect logic directly in the controller |
| Observers | Simple model lifecycle hooks (setting defaults on `creating`) | Heavy business logic in observers — makes flow invisible |
| Direct call | Single, obvious consequence with no other subscribers | Using events when there is only one listener and always will be |

**Flag:** Observer methods exceeding 10 LOC or calling external services. Observers should be thin; extract heavy logic into dedicated listener classes.

---

## PHP 8.x Modern Features

| Old Pattern | Modern Alternative | Min Version |
|---|---|---|
| `switch` with `return` in each case | `match` expression | PHP 8.0 |
| Constructor + property assignment boilerplate | Constructor promotion: `public function __construct(private readonly string $name)` | PHP 8.0 |
| String status constants `'pending'`, `'active'` | Backed enums: `enum Status: string { case Pending = 'pending'; }` | PHP 8.1 |
| `@var` docblock type declarations | Native property types + `readonly` | PHP 8.1 |
| Nullable type `?string` in newer code | Union type `string|null` (stylistic, both valid) | PHP 8.0 |
| Named arguments missing on ambiguous calls | Use named arguments: `new CacheItem(key: 'user', ttl: 3600)` | PHP 8.0 |

---

## Testing

| What to Check | Flag If | Best Practice |
|---|---|---|
| Test type | Feature tests testing internal method logic | Feature tests hit HTTP endpoints; unit tests test isolated logic |
| Database state | Tests leave data behind affecting other tests | Use `RefreshDatabase` or `DatabaseTransactions` trait |
| Factories | `User::create([...])` with inline data in tests | Use model factories: `User::factory()->create()` |
| Assertions | Only asserting status code | Assert response structure, database state, and side effects |
| Mocking | Mocking the class under test | Mock dependencies, not the subject |

```php
// BAD: no factory, no database cleanup, weak assertions
public function test_user_creation()
{
    $response = $this->post('/users', ['name' => 'Test', 'email' => 'test@test.com']);
    $this->assertEquals(200, $response->status());
}

// GOOD: factory, RefreshDatabase, strong assertions
public function test_user_creation(): void
{
    $payload = User::factory()->make()->toArray();

    $response = $this->postJson('/users', $payload);

    $response->assertCreated()
        ->assertJsonStructure(['data' => ['id', 'name', 'email']]);
    $this->assertDatabaseHas('users', ['email' => $payload['email']]);
}
```
