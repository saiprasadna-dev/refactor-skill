---
description: Refactor ALL endpoints in a god file (or whole repo) into modules — planned, pinned, and extracted cluster by cluster without changing business logic
argument-hint: "[file path, e.g. src/app.js — omit to scan the whole repo for hotspots]"
---

Decompose endpoint hotspots for: $ARGUMENTS

Use the endpoint-rearchitect skill's god-file decomposition playbook
(`references/godfile-decomposition.md`) end to end:

1. **Inventory & plan.** From the skill directory run
   `python3 scripts/plan_refactor.py --root <project-root>` for the
   hotspot inventory. If a file was given (or once a hotspot is chosen),
   run `--file <path>` for its decomposition plan: endpoint clusters,
   read-only vs read/write, preserve markers, side effects, existing
   tests, and safest-first extraction phases. Review the proposed
   clusters against the actual code (shared helpers and module-level
   state can regroup them) and present the adjusted plan BEFORE changing
   anything. If no arguments and multiple hotspots exist, show the
   inventory and ask which file to decompose first.
2. **Map the shared ground (read-only):** module-level state, shared
   helpers, inline middleware, import-time side effects. Classify each as
   per-cluster, cross-cluster (extract first, pinned separately), or
   ambient (highest risk — document current timing).
3. **Contract + pin per cluster:** one behavior contract per cluster in
   `modernization/endpoints/<cluster-slug>.contract.md`; characterization
   tests passing against the untouched file first (stack-native harness).
   Zero-test clusters get no extraction until pinned — blocking.
4. **Extract cluster by cluster** in the planner's phase order: create
   the cluster module in the project's idiom, move the endpoints, leave a
   delegating mount in the original file, keep route/middleware
   registration order identical, run the FULL characterization suite, and
   commit — always green, pinned tests unmodified. Never duplicate shared
   state, never fix bugs silently (pin bug-for-bug and record them).
5. **Retire & report:** the original file ends as composition root (or is
   inlined); re-run the hotspot inventory for the before/after evidence;
   append a "God-file decomposition" section to MODERNIZATION_REPORT.md.

Respond in this order: Hotspot inventory, Decomposition plan (adjusted),
Shared-ground map, Per-phase progress (contracts, tests, extraction),
Validation notes, Manual review items.
