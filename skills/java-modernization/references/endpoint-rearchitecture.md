# Endpoint Re-Architecture Playbook

End-to-end workflow for re-architecting a single endpoint slice (e.g.
`/search`) **without changing business logic**. The unit of work is the
vertical slice: HTTP layer → controller → services → domain logic →
persistence → external calls → messaging → configuration → tests.

The golden rule: **behavior is pinned before anything moves.** No
structural change happens until the slice's current behavior is captured
as a contract and locked by characterization tests.

## Phase 1 — Trace the slice (read-only)

Map every class the endpoint touches with the tracer:

```bash
python3 scripts/trace_endpoint.py /search --root /path/to/project
python3 scripts/trace_endpoint.py /api/orders/{id} --root . --format md
```

The tracer finds the handler (controller + method + HTTP verb), walks the
dependency graph (services, interface→implementation, repositories,
entities, Feign/Rest clients, messaging), flags behavior-critical markers
(`@Transactional`, `@PreAuthorize`, `@Valid`, `@Cacheable`, listeners,
external calls), and lists existing tests that touch the slice.

The tracer is static and heuristic — verify its map by reading the code.
Then complete it manually with things static analysis can miss:

- AOP aspects and interceptors that apply to the slice (pointcuts,
  `HandlerInterceptor`, filters, `@ControllerAdvice` exception handlers)
- Security filter-chain rules matching the endpoint's path pattern
- Configuration properties the slice reads (`@Value`,
  `@ConfigurationProperties`, feature flags)
- Database schema objects behind the entities (tables, constraints,
  triggers, migrations)
- Reflection, SpEL expressions, and dynamic bean lookups

## Phase 2 — Capture the behavior contract

Write the contract to `modernization/endpoints/<slug>.contract.md` in the
target repository (slug: `/api/search` → `api-search`). It must record,
from evidence in the code:

1. **Request contract** — verb(s), path (+ variables), query params,
   headers, request body schema, content types, every validation rule and
   its error response.
2. **Response contract** — status codes per outcome (success, validation
   failure, not-found, unauthorized, error), response body shape, headers,
   pagination/sorting semantics.
3. **Security behavior** — authentication requirements, roles/authorities,
   method-level rules, what anonymous callers get.
4. **Side effects** — DB reads/writes (which tables, in which
   transaction), messages published/consumed, external services called,
   caches read/written, emails/notifications, audit records.
5. **Business rules observed** — orderings, filters, calculations,
   defaults, edge-case handling — described as observed behavior, not as
   things to improve.
6. **Non-functional behavior worth preserving** — timeouts, retries,
   circuit breakers, rate limits, idempotency.

Anything ambiguous goes into the contract under **Open questions** and
becomes a manual review item — never a silent assumption.

## Phase 3 — Pin behavior with characterization tests

Before touching structure, lock the contract with tests that assert
**current** behavior exactly (golden-master style):

- `MockMvc` / `WebTestClient` tests per documented status code and
  response shape — including error and validation responses, byte-level
  where JSON shape matters.
- Security tests: authorized, unauthorized, and forbidden callers.
- Side-effect assertions: repository interactions, published messages
  (embedded broker or mocks), external calls (WireMock/MockRestServiceServer).
- If the slice has zero tests (the tracer warns about this), this phase is
  **mandatory and blocking** — no re-architecture on an unpinned slice.

Run them against the untouched code first: they must pass **before** the
refactor, or they are not characterizing reality.

## Phase 4 — Re-architect within the contract

Now restructure freely as long as every characterization test stays green
and unmodified:

Allowed structural moves:

- Split god-classes into cohesive services; introduce interfaces at seams
- Constructor injection; remove field injection and static lookups
- Extract the domain logic from controllers into services (thin
  controllers), or from repositories into services (thin repositories)
- Introduce DTOs at the boundary — only if the serialized JSON stays
  byte-compatible (field names, order-insensitive, nullability)
- Replace hand-rolled plumbing with framework equivalents (mappers,
  `@ControllerAdvice`, converters) when output is provably identical
- Package-by-feature reorganization, hexagonal/ports-and-adapters layering
- Modernize APIs per the skill's knowledge base (`scripts/search.py`)

Forbidden (flag instead):

- Changing any documented status code, response field, or error message
- Moving a `@Transactional` boundary (changes commit/rollback semantics)
- Changing `@Cacheable` keys/conditions, cache names, or TTL semantics
- Reordering side effects relative to the transaction (e.g. publishing a
  message before vs after commit)
- Changing query semantics — derived-query renames, fetch strategies
  (LAZY/EAGER), or JPQL rewrites that alter result order or N+1 behavior
  without proof of equivalence
- Removing or weakening validation and security rules
- "Fixing" bugs discovered along the way — record them as manual review
  items; a bug-for-bug-compatible refactor is the deliverable

Work in small commits, each leaving the build green and the
characterization tests untouched and passing.

## Phase 5 — Validate and report

- Full build + full test suite; compare discovered-test counts with the
  baseline.
- Diff review specifically for the forbidden list above.
- Append an **Endpoint re-architecture** section to
  `MODERNIZATION_REPORT.md`: the slice map (before/after), contract file
  location, characterization tests added, structural changes made, and
  every manual review item (including bugs found but deliberately
  preserved).

## Scaling up

Re-architect one endpoint slice at a time. When multiple endpoints share a
service, trace all of them first (`trace_endpoint.py` once per path),
merge the contracts, and pin every sharing endpoint before restructuring
the shared class. The whole-application re-architecture is just this loop
executed slice by slice, safest-first.
