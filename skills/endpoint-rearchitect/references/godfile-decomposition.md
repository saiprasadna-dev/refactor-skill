# God-File Decomposition Playbook

Workflow for a file that defines **many endpoints with lots of code in one
place** — the "god file" (one `server.js`/`app.py`/`MainController.java`
holding a whole API). The goal is to refactor ALL of its endpoints into
cohesive modules without changing business logic.

This is the batch form of the single-endpoint playbook
(`rearchitecture-playbook.md`): the same trace → contract → pin →
restructure → validate loop, run cluster by cluster, with the god file
shrinking to a facade and then disappearing.

## Phase 0 — Inventory and plan

```bash
python3 scripts/plan_refactor.py --root .                     # hotspot inventory
python3 scripts/plan_refactor.py --root . --file src/app.js   # decomposition plan
```

The planner clusters the file's endpoints by path resource (sub-clustering
by the next segment when the file is all one resource), marks each cluster
read-only or read/write, aggregates the file's preserve markers and side
effects, lists existing tests, and orders extraction phases **safest
first** — read-only and smallest clusters lead, so the process is
practiced on low-risk slices before touching the write paths.

Review the proposed clusters against domain knowledge: the planner groups
by URL shape, but two endpoints sharing helper functions or module-level
state belong in the same phase even if their paths differ. Read the god
file and adjust cluster membership before starting.

## Phase 1 — Map the shared ground (read-only)

God files hide coupling that per-endpoint tracing misses. Before touching
anything, inventory the file's shared internals:

- module-level state (connections, caches, counters, singletons)
- helper functions and which endpoints call them
- shared middleware defined inline
- module-level side effects that run at import/startup time
- shared configuration reads

Classify each shared item: **per-cluster** (used by one cluster — moves
with it), **cross-cluster** (used by several — extract to a shared module
FIRST, in its own pinned step), or **ambient** (import-time effects —
these are the highest-risk items; document exactly when they run today,
because moving code between files changes import order).

## Phase 2 — Contract per cluster

For each cluster, capture the behavior contract exactly as in the
single-endpoint playbook Phase 2, one contract file per cluster:
`modernization/endpoints/<cluster-slug>.contract.md`. Shared-helper
behavior (e.g. a common error format) is documented once and referenced.

## Phase 3 — Pin per cluster

Characterization tests per cluster (per-stack harness table in the
single-endpoint playbook), passing against the untouched god file first.
Pin the cross-cluster helpers with direct unit tests too — they are about
to be moved.

A cluster with zero tests gets no extraction until pinned. It is fine —
and normal — for pinning to be most of the total effort.

## Phase 4 — Extract cluster by cluster

Follow the planner's phase order. For each phase:

1. Extract cross-cluster shared code needed by this cluster into its
   shared module (if not already done in an earlier phase).
2. Create the cluster's module: route registrations + handler/controller +
   service, in the project's idiom (Express `Router`, Hono sub-app +
   `app.route`, FastAPI `APIRouter` + `include_router`, Spring
   `@RestController` per resource, Go sub-router, ASP.NET controller).
3. Move the cluster's endpoints into it. In the god file, replace the
   moved code with a **delegating registration** (mount the new module) —
   the god file becomes a composition root, not a code host.
4. Keep route paths, methods, middleware order, and registration ORDER
   identical — route matching can be order-sensitive (first-match wins in
   Express/Hono; overlapping patterns in many routers).
5. Run the full characterization suite — not just this cluster's tests;
   extraction can break siblings through shared state or import order.
6. Commit. The build is green and every pinned test passes unmodified
   after every phase.

Forbidden during extraction (same list as the single-endpoint playbook,
plus god-file specifics):

- changing route registration order or middleware attachment order
- turning module-level state into per-module copies (a shared counter,
  cache, or connection must remain shared — extract it, don't duplicate it)
- moving import-time side effects without documenting the timing change
- merging "duplicate-looking" helpers that differ subtly — pin first,
  merge later as its own reviewed step
- fixing bugs found along the way — pin bug-for-bug, record as manual
  review items

## Phase 5 — Retire the god file and report

When every cluster is extracted, the god file should contain only
bootstrap + mounting. Either keep it as the explicit composition root or
inline it into the app entry point. Then:

- full build + full suite; compare test counts to the Phase 3 baseline
- re-run `plan_refactor.py --root .` — the file should no longer be a
  hotspot; attach before/after inventories to the report
- append a **God-file decomposition** section to
  `MODERNIZATION_REPORT.md`: before/after structure, per-phase commits,
  contracts written, tests added, manual review items (including preserved
  bugs and import-order notes)

## Multiple god files

Run the inventory once, then decompose one file at a time, safest first
(fewest write endpoints, most existing tests). Shared code between god
files is extracted in the earliest phase that needs it and pinned once.
