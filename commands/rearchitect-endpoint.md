---
description: Re-architect one endpoint end-to-end in any language (trace, pin behavior, restructure) without changing business logic
argument-hint: "<endpoint path, e.g. /search or /api/orders/{id}> [notes]"
---

Re-architect the endpoint slice for: $ARGUMENTS

Use the endpoint-rearchitect skill (language-agnostic) and follow its
`references/rearchitecture-playbook.md` phase by phase:

1. **Trace (read-only).** From the skill directory run
   `python3 scripts/trace_endpoint.py <path> --root <project-root>`
   (works for Java/Kotlin, JS/TS, Python, Go, C#, Ruby, PHP). If no route
   matches, run `--list-routes` and locate the handler manually. Verify
   the map by reading the code and complete it with what static analysis
   misses (middleware by path pattern, global error handlers, DI/config
   wiring, DB schema). Present the slice map before doing anything else.
2. **Capture the behavior contract** to
   `modernization/endpoints/<slug>.contract.md`: request/response per
   status code, auth behavior, side effects and their order, observed
   business rules, non-functional behavior. Ambiguities → "Open
   questions" / manual review items.
3. **Pin behavior with characterization tests** using the stack's native
   harness (MockMvc, supertest, Hono app.request, FastAPI TestClient,
   httptest, WebApplicationFactory, rspec request specs, Laravel feature
   tests — see the playbook table). Tests must pass on the UNTOUCHED code
   first. Zero-test slices: this phase is mandatory and blocking.
4. **Re-architect within the contract** in small always-green commits.
   Execution policy (binding):
   - **All layers.** Refactor every layer the slice touches — route,
     controller/handler, DTOs, service, domain, data access, wiring. The
     tracer's slice map is the checklist: each file in it is refactored,
     replaced by a new dedicated class, or explicitly recorded as left
     as-is with a reason. Do not stop at the controller.
   - **Heavy shared classes:** if a service/repository the endpoint uses
     is heavy and shared by other endpoints, do NOT restructure it in
     place — create new dedicated class(es) for this slice, move the
     exact logic verbatim (no improvements during the move), point this
     endpoint at them, leave other callers untouched, and delete moved
     code from the old class only when provably dead (strangler fig).
   - **Tests first, tests for everything:** characterization tests are
     already green on the untouched code (Phase 3); keep the suite green
     after each move; write unit tests for every new class and every
     changed layer — new code without tests does not land; finish with
     the full suite green and characterization tests UNMODIFIED.
   Never change status codes/response shapes, move transaction
   boundaries, alter cache or query semantics, reorder side effects,
   weaken validation or auth, or silently fix bugs (pin them bug-for-bug
   and record them).
5. **Validate and report.** Full build + tests, compare test counts to
   baseline, review the diff against the forbidden list, append an
   "Endpoint re-architecture" section to MODERNIZATION_REPORT.md.

If no endpoint path was given, run the tracer with `--list-routes`,
show the route inventory, and ask which slice to re-architect.

Respond in this order: Slice map, Behavior contract summary,
Characterization tests added, Changes made, Validation notes, Manual
review items.
