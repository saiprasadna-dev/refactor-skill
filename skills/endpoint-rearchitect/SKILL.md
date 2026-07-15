---
name: endpoint-rearchitect
description: >-
  Language-agnostic endpoint re-architecture skill. Given one endpoint (e.g.
  /search), trace it end-to-end through routes, controllers/handlers,
  services, data access, external calls, and messaging; pin its current
  behavior as a contract with characterization tests; then restructure the
  slice without changing business logic. Includes a universal static tracer
  supporting Java/Kotlin (Spring, JAX-RS, Ktor), JavaScript/TypeScript
  (Express, Hono, NestJS, Fastify, Next.js), Python (FastAPI, Flask,
  Django), Go (Gin, Echo, Chi, Fiber, net/http), C# (ASP.NET Core), Ruby
  (Rails, Sinatra), and PHP (Laravel, Symfony). Also handles god files —
  one file defining many endpoints with lots of code — via a batch
  planner that clusters all endpoints and phases their extraction. Use
  when a project needs re-architecture, endpoint-scoped refactoring,
  splitting a large file with many routes, layering cleanup, or a safe
  restructuring plan in any language.
---

# Endpoint Re-Architect

Re-architect one endpoint slice at a time — **in any language or
framework** — without changing business logic. The unit of work is the
vertical slice: HTTP layer → routing → handler/controller → services →
domain logic → data access → external calls → messaging → configuration →
tests.

The golden rule: **behavior is pinned before anything moves.** No
structural change happens until the slice's current behavior is captured
as a contract and locked by characterization tests that pass against the
untouched code.

## When to apply

- "Re-architect this project / this endpoint"
- "Restructure /search end-to-end"
- "This file has lots of endpoints and too much code — refactor all of it"
- Layering cleanup (fat controllers, tangled services, no seams)
- Preparing a slice for extraction (modularization, strangler-fig)
- Any structural refactor where behavior must provably not change

Not for: new features, behavior changes, performance tuning that alters
observable semantics — those need explicit user approval per change.

## The universal tracer

`scripts/trace_endpoint.py` — static, stdlib-only Python 3, no
dependencies (try `python3`, then `python`, then `py -3`):

```bash
python3 scripts/trace_endpoint.py <endpoint-path> [--root DIR] [--format ascii|md|json] [--depth N]
python3 scripts/trace_endpoint.py / --list-routes --root DIR   # inventory every detected route
```

It detects routes across frameworks (Spring/JAX-RS/Ktor annotations,
Express/Hono/Koa/Fastify calls with `use`/`route` mount-prefix resolution
for both ESM and CommonJS, NestJS decorators, Next.js/SvelteKit file-based
routes, FastAPI `include_router` prefixes, Flask blueprints, Django URLs,
Gin/Echo/Chi/Fiber/net-http, ASP.NET attributes and minimal APIs, Rails,
Sinatra, Laravel, Symfony), then walks the dependency graph from the
handler using language-appropriate resolution (ESM/CommonJS imports,
Python imports, Java/Kotlin/C# type references with interface→impl
lookup, Go internal packages, Ruby/PHP conventions).

For every file in the slice it reports:

- **preserve markers** — auth/authorization, validation, transaction
  boundaries, caching, retry/circuit-breaker, idempotency
- **side effects** — database access, external HTTP, messaging/queues,
  email/SMS, object storage, schedulers, consumers
- **existing tests** touching the slice — and a loud warning when none exist

Trust model: the tracer is heuristic. Always verify its map by reading the
code, and complete it with what static analysis can't see — AOP/aspects,
DI wiring in config, middleware applied by path pattern, reflection,
dynamic routing, database triggers. If it finds no route, run
`--list-routes` and locate the handler manually before concluding anything.

## The batch planner (god files / many endpoints)

`scripts/plan_refactor.py` — same stack support, for refactoring ALL
endpoints at once:

```bash
python3 scripts/plan_refactor.py --root DIR                    # hotspot inventory
python3 scripts/plan_refactor.py --root DIR --file src/app.js  # decomposition plan
```

The inventory ranks every route-defining file by endpoint count and size
and flags hotspots. The per-file plan clusters the endpoints by path
resource (sub-clustering when a file is all one resource), marks each
cluster read-only or read/write, aggregates preserve markers / side
effects / existing tests, and orders extraction phases **safest first**.
When the work is "refactor all these endpoints", follow
[references/godfile-decomposition.md](references/godfile-decomposition.md):
plan → map shared state and helpers → contract + pin per cluster →
extract cluster by cluster (delegating mounts, identical registration
order, full suite after every phase) → retire the god file and report.

## Workflow

Follow the five phases in
[references/rearchitecture-playbook.md](references/rearchitecture-playbook.md):

1. **Trace** the slice (read-only) with the tracer; verify and complete
   the map manually. Present the map before doing anything else.
2. **Capture the behavior contract** to
   `modernization/endpoints/<slug>.contract.md` in the target repo:
   request/response per status code, auth behavior, side effects, observed
   business rules, non-functional behavior. Ambiguities become "Open
   questions" — manual review items, never assumptions.
3. **Pin behavior with characterization tests** using the stack's native
   test harness (see the playbook's per-stack table). Tests must pass
   against the untouched code first. A slice with zero tests gets no
   structural change until pinned — blocking.
4. **Re-architect within the contract** in small always-green commits.
   Characterization tests stay unmodified and passing. Never change status
   codes or response shapes, move transaction boundaries, alter cache or
   query semantics, reorder side effects, weaken validation or auth, or
   silently fix bugs — pin bugs bug-for-bug and record them.
5. **Validate and report**: full build and test suite, compare test counts
   with the baseline, review the diff against the forbidden list, append
   an "Endpoint re-architecture" section to `MODERNIZATION_REPORT.md`.

Scale to a whole application slice by slice; when endpoints share a
service, trace and pin every sharing endpoint before restructuring the
shared code.

## Success criteria

- Business logic provably unchanged (characterization tests unmodified,
  green before and after)
- The slice map and behavior contract are committed artifacts
- Build green; test count did not drop unexplained
- Every ambiguity and discovered bug recorded as a manual review item

## Operating style

Evidence over memory: the tracer, the code, and the tests are the sources
of truth. Small safe steps over big rewrites. When equivalence can't be
proven, flag it — don't change it.
