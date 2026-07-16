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

### Execution policy: all layers, dedicated classes, test-first

**All layers.** "Refactor this endpoint end-to-end" means changing every
layer the slice touches — route registration, controller/handler, DTOs/
serialization, service, domain logic, data access, and wiring/config. Do
not stop at the controller: a refactor that cleans the top layer and
leaves the endpoint's service and data-access code tangled has not
delivered the slice. The tracer's slice map is the checklist — every file
in it is either refactored, replaced by a new dedicated class, or
explicitly recorded as "left as-is because <reason>".

**Heavy shared classes → create your own.** When the endpoint depends on
a heavy class (lots of code, used by other endpoints — a god service,
mega-repository, or utility dump), do NOT restructure that class in
place; other endpoints depend on it and are not pinned. Instead:

1. Create new, dedicated class(es) for this endpoint's slice (e.g.
   extract `SearchService` + `SearchRepository` out of a 2000-line
   `AppService`), named for the capability, in the target architecture's
   shape.
2. Move the exact logic paths this endpoint exercises into them —
   copy semantics verbatim, no "improvements" during the move.
3. Point this endpoint at the new classes; other endpoints keep using
   the old heavy class untouched. Delete the moved code from the heavy
   class only when nothing else calls it (dead-code check), otherwise
   leave it and record the duplication as a tracked item for the next
   slice.
4. The heavy class shrinks slice by slice (strangler fig) — never in one
   big rewrite.

**Test-first, and tests for everything.** The strict order is:

1. Characterization tests (Phase 3) written FIRST and green against the
   untouched code — this is what "make it work before changes" means.
2. Refactor, layer by layer, keeping the suite green after each move.
3. Every new class created gets its own unit tests (its public methods,
   edge cases, and error paths), and every changed layer gets tests that
   cover the change — new code without tests does not land.
4. Finish with the full suite green and the characterization tests
   UNMODIFIED — proving behavior after the refactor equals behavior
   before it.

### Allowed structural moves

Behavior identical by construction or proven by the pinned tests:

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
