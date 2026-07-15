# Endpoint Re-Architecture Playbook (any language)

End-to-end workflow for re-architecting a single endpoint slice without
changing business logic. Language- and framework-agnostic; per-stack
specifics are tabled where they differ.

## Phase 1 — Trace the slice (read-only)

```bash
python3 scripts/trace_endpoint.py /search --root /path/to/project
python3 scripts/trace_endpoint.py / --list-routes --root /path/to/project
```

Verify the tracer's map by reading every listed file, then complete it
with what static analysis misses:

| Invisible to static tracing | Where to look |
|---|---|
| AOP / aspects / decorators applied externally | aspect configs, DI container setup |
| Middleware applied by path pattern | app bootstrap, security config, API gateway config |
| Global error handlers / exception mappers | `@ControllerAdvice`, Express error middleware, Hono `onError`, Django middleware, Rails `rescue_from` |
| Config the slice reads | env files, `@Value`/`process.env`/`os.environ`/`settings`, feature flags |
| Database schema behind the models | migrations, DDL, triggers, constraints |
| Serializer behavior | global JSON settings (naming strategy, null handling, date formats) |
| Dynamic dispatch | reflection, service locators, string-keyed handler maps |

## Phase 2 — Capture the behavior contract

Write to `modernization/endpoints/<slug>.contract.md` (slug: `/api/search`
→ `api-search`), from evidence only:

1. **Request contract** — verb(s), path (+ params), query params, headers,
   body schema, content types, every validation rule and its exact error
   response.
2. **Response contract** — status code per outcome; response body shape
   (field names, casing, null vs absent); headers; pagination/ordering
   semantics.
3. **Auth behavior** — what anonymous, authenticated, and unauthorized
   callers each get.
4. **Side effects** — DB reads/writes (tables + transaction scope),
   messages published, external services called, caches touched,
   emails/notifications, audit records — and their ORDER.
5. **Business rules observed** — filters, orderings, calculations,
   defaults, edge cases — described as observed, not as things to improve.
6. **Non-functional behavior** — timeouts, retries, idempotency, rate
   limits.

Ambiguities go under **Open questions** as manual review items — never
resolved by assumption.

## Phase 3 — Pin behavior with characterization tests

Golden-master style: assert what the code DOES today, including behavior
that looks wrong (record the suspected bug as a manual review item and pin
it bug-for-bug). Tests must pass against the untouched code before any
refactor starts.

Per-stack harnesses for HTTP-level characterization:

| Stack | Harness |
|---|---|
| Java/Kotlin (Spring) | `MockMvc` / `WebTestClient`, `@SpringBootTest`, Testcontainers for the DB |
| JS/TS (Express/Fastify) | `supertest` against the app instance |
| JS/TS (Hono, incl. Cloudflare Workers) | `app.request('/path')` in Vitest, D1/R2 stubs or miniflare |
| NestJS | `@nestjs/testing` + `supertest` |
| Python (FastAPI) | `TestClient(app)` (httpx) |
| Python (Flask) | `app.test_client()` |
| Python (Django) | `django.test.Client` / DRF `APIClient` |
| Go | `net/http/httptest` against the router |
| C# (ASP.NET Core) | `WebApplicationFactory<TEntryPoint>` |
| Ruby (Rails) | request specs (`rspec-rails`) |
| PHP (Laravel) | `$this->getJson(...)` feature tests |

Cover, at minimum: each documented status code, the exact response shape
for success and each error, auth matrix (anonymous / authorized /
forbidden), and side-effect assertions (DB rows, published messages via
test brokers or fakes, external calls via WireMock / nock / responses /
httptest fakes).

If the slice has **zero tests** (the tracer warns loudly), this phase is
mandatory and blocking — no structural change lands on an unpinned slice.

## Phase 4 — Re-architect within the contract

Allowed structural moves (behavior identical by construction or proven by
the pinned tests):

- Split god-classes/modules into cohesive units; introduce interfaces/
  ports at seams
- Thin controllers/handlers: move domain logic into services
- Introduce DTOs/serializers at the boundary — only if the wire format
  stays byte-compatible
- Replace hand-rolled plumbing with framework equivalents when output is
  provably identical
- Package-by-feature reorganization; hexagonal/ports-and-adapters layering
- Dependency injection instead of globals/singletons/static lookups

Forbidden (flag as manual review items instead):

- Changing any documented status code, response field, or error message
- Moving a transaction boundary (commit/rollback scope changes)
- Changing cache keys, conditions, names, or TTLs
- Reordering side effects relative to the transaction or to each other
- Changing query semantics — result order, filtering, lazy/eager loading,
  N+1 profile — without proof of equivalence
- Removing or weakening validation or auth
- "Fixing" bugs found along the way — the deliverable is bug-for-bug
  compatible

Work in small commits; after each one the build is green and the
characterization tests are untouched and passing.

## Phase 5 — Validate and report

- Full build + full test suite; compare discovered-test counts with the
  baseline (a silent drop is a red flag that must be explained).
- Review the final diff specifically against the forbidden list.
- Append an **Endpoint re-architecture** section to
  `MODERNIZATION_REPORT.md`: slice map before/after, contract file
  location, characterization tests added, structural changes, and every
  manual review item (including preserved bugs).

## Scaling up

The whole-application re-architecture is this loop run slice by slice,
safest-first. When multiple endpoints share code, trace all of them,
merge their contracts, and pin every sharing endpoint before
restructuring the shared unit.
