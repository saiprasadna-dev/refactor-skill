---
description: Re-architect one endpoint end-to-end (trace, pin behavior, restructure) without changing business logic
argument-hint: "<endpoint path, e.g. /search or /api/orders/{id}> [target notes]"
---

Re-architect the endpoint slice for: $ARGUMENTS

Follow the java-modernization skill's endpoint re-architecture playbook
(`references/endpoint-rearchitecture.md`) strictly, phase by phase:

1. **Trace (read-only).** Run the slice tracer from the skill directory:
   `python3 scripts/trace_endpoint.py <path> --root <project-root>`.
   Verify its map by reading the code, then complete it with what static
   analysis misses: aspects, interceptors, @ControllerAdvice handlers,
   security filter-chain rules for the path, config properties, DB schema
   behind the entities. Present the slice map before doing anything else.
2. **Capture the behavior contract** to
   `modernization/endpoints/<slug>.contract.md`: request contract,
   response contract per status code, security behavior, side effects
   (DB/messaging/external calls/caches), observed business rules, and
   non-functional behavior. Ambiguities go under "Open questions" as
   manual review items.
3. **Pin behavior with characterization tests** (MockMvc/WebTestClient,
   security cases, side-effect assertions) that pass against the
   UNTOUCHED code first. If the slice has no tests, this phase is
   mandatory and blocking.
4. **Re-architect within the contract**, in small always-green commits.
   Characterization tests stay unmodified and passing. Never: change
   status codes/response fields, move @Transactional boundaries, alter
   cache or query semantics, reorder side effects, weaken validation or
   security, or silently fix bugs — bugs found are recorded as manual
   review items and preserved bug-for-bug.
5. **Validate and report.** Full build + tests, compare test counts with
   baseline, review the diff against the forbidden list, and append an
   "Endpoint re-architecture" section to MODERNIZATION_REPORT.md.

If no endpoint path was given, list the application's endpoints (scan for
@RequestMapping/@GetMapping/etc.) and ask which slice to re-architect.

Respond in this order: Slice map, Behavior contract summary,
Characterization tests added, Changes made, Validation notes, Manual
review items.
