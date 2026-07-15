#!/usr/bin/env python3
"""Batch refactoring planner for endpoint hotspots (god files).

Finds files that define many endpoints (or lots of code around them),
clusters those endpoints into proposed modules, and emits a phased,
safest-first extraction plan. Companion to trace_endpoint.py — reuses its
route detection, dependency walking, and marker scanning, so it supports
the same languages and frameworks (Java/Kotlin, JS/TS, Python, Go, C#,
Ruby, PHP).

Static, stdlib-only, heuristic: output is a plan to verify and refine,
not an instruction to follow blindly.

Usage:
  python3 scripts/plan_refactor.py [--root DIR] [--file PATH] [--format ascii|md|json]

Modes:
  (default)      hotspot inventory: every route-defining file ranked by
                 endpoint count and size, hotspots flagged
  --file PATH    full decomposition plan for one file: endpoint clusters,
                 risk notes, pinning requirements, extraction order

Examples:
  python3 scripts/plan_refactor.py --root .
  python3 scripts/plan_refactor.py --root . --file src/app.js --format md
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trace_endpoint as te  # noqa: E402

READ_VERBS = {"GET", "HEAD", "OPTIONS", "ANY"}
GENERIC_PREFIXES = {"api", "rest", "v1", "v2", "v3", "internal", "public"}


def cluster_key(route_path, level=0):
    segs = [s for s in route_path.strip("/").split("/")
            if s and not te.PARAM_TOKEN_RE.fullmatch(s)]
    while segs and segs[0].lower() in GENERIC_PREFIXES:
        segs = segs[1:]
    if not segs:
        return "root"
    return segs[min(level, len(segs) - 1)].lower()


def routes_by_file(repo):
    grouped = defaultdict(list)
    for r in te.find_routes(repo):
        grouped[r["file"]].append(r)
    return grouped


def is_hotspot(routes, loc):
    return len(routes) >= 4 or (len(routes) >= 2 and loc >= 200)


def inventory(repo):
    rows = []
    for path, routes in routes_by_file(repo).items():
        loc = repo.files[path].count("\n") + 1
        rows.append({
            "file": repo.rel(path),
            "endpoints": len(routes),
            "loc": loc,
            "hotspot": is_hotspot(routes, loc),
            "methods": sorted({r["method"] for r in routes}),
        })
    rows.sort(key=lambda r: (-r["endpoints"], -r["loc"]))
    return rows


def plan_file(repo, target, depth):
    grouped = routes_by_file(repo)
    if target not in grouped:
        return None
    routes = sorted(grouped[target], key=lambda r: r["line"])
    text = repo.files[target]

    clusters = defaultdict(list)
    for r in routes:
        clusters[cluster_key(r["path"])].append(r)
    # A file dedicated to one resource collapses into a single cluster;
    # sub-cluster by the next path segment so the plan stays actionable.
    if len(clusters) == 1 and len(routes) > 5:
        parent = next(iter(clusters))
        clusters = defaultdict(list)
        for r in routes:
            sub = cluster_key(r["path"], level=1)
            clusters[parent if sub == parent else f"{parent}/{sub}"].append(r)

    slice_files = te.walk({target}, repo, depth)
    preserve, effects = {}, {}
    for info in slice_files.values():
        preserve.update(info["preserve"])
        effects.update(info["side_effects"])
    tests = te.find_tests(repo, set(slice_files))

    cluster_list = []
    for name, eps in clusters.items():
        read_only = all(e["method"] in READ_VERBS for e in eps)
        cluster_list.append({
            "cluster": name,
            "endpoints": [{"method": e["method"], "path": e["path"], "line": e["line"]}
                          for e in eps],
            "read_only": read_only,
            "suggested_module": name if name != "root" else "core",
        })
    # safest-first: read-only clusters, then fewest endpoints
    cluster_list.sort(key=lambda c: (not c["read_only"], len(c["endpoints"]), c["cluster"]))

    return {
        "file": repo.rel(target),
        "loc": text.count("\n") + 1,
        "endpoint_count": len(routes),
        "clusters": cluster_list,
        "shared_slice_files": [repo.rel(p) for p in slice_files],
        "preserve_markers": preserve,
        "side_effects": effects,
        "tests": tests,
        "phases": [
            {"phase": i + 1,
             "cluster": c["cluster"],
             "endpoints": len(c["endpoints"]),
             "action": (f"Pin every endpoint in '{c['cluster']}' with characterization tests, "
                        f"then extract them into module '{c['suggested_module']}' "
                        "(route file + handler/controller + service as needed), leaving "
                        "delegating stubs in the original file until the phase is green.")}
            for i, c in enumerate(cluster_list)
        ],
    }


# ------------------------------------------------------------------ output --
def render_inventory_ascii(rows):
    out = ["Endpoint hotspot inventory", "=" * 72,
           f"{'endpoints':>9}  {'loc':>6}  {'hotspot':>7}  file"]
    for r in rows:
        flag = "  YES" if r["hotspot"] else "     "
        out.append(f"{r['endpoints']:>9}  {r['loc']:>6}  {flag:>7}  {r['file']}")
    hot = [r for r in rows if r["hotspot"]]
    out.append("")
    if hot:
        out.append(f"{len(hot)} hotspot file(s). Plan each with: "
                   "plan_refactor.py --file <path> — then run the decomposition "
                   "playbook cluster by cluster.")
    else:
        out.append("No hotspot files detected (thresholds: >=4 endpoints, or >=2 "
                   "endpoints in a 200+ line file).")
    return "\n".join(out)


def render_plan_ascii(plan):
    out = [f"Decomposition plan for {plan['file']}  "
           f"({plan['endpoint_count']} endpoints, {plan['loc']} lines)", "=" * 72]
    for c in plan["clusters"]:
        kind = "read-only" if c["read_only"] else "read/write"
        out.append(f"CLUSTER '{c['cluster']}'  ({len(c['endpoints'])} endpoints, {kind})"
                   f"  ->  proposed module: {c['suggested_module']}")
        for e in c["endpoints"]:
            out.append(f"    {e['method']:6} {e['path']}   (line {e['line']})")
    out.append("")
    if plan["preserve_markers"]:
        out.append("Preserve across the whole file (verify per endpoint during pinning):")
        for meaning, ev in plan["preserve_markers"].items():
            out.append(f"    ! {meaning}   ({ev})")
    if plan["side_effects"]:
        out.append("Side effects in the slice:")
        for meaning, ev in plan["side_effects"].items():
            out.append(f"    ~ {meaning}   ({ev})")
    out.append("")
    if plan["tests"]:
        out.append("Existing tests touching the slice:")
        for t, covers in plan["tests"].items():
            out.append(f"    {t}  covers {', '.join(covers)}")
    else:
        out.append("WARNING: no tests touch this slice — every cluster must be pinned "
                   "with characterization tests before its extraction phase.")
    out.append("")
    out.append("Extraction phases (safest first — read-only and smallest clusters lead):")
    for p in plan["phases"]:
        out.append(f"  Phase {p['phase']}: [{p['cluster']}] {p['action']}")
    return "\n".join(out)


def render_plan_md(plan):
    out = [f"# Decomposition plan: `{plan['file']}`",
           f"\n{plan['endpoint_count']} endpoints, {plan['loc']} lines\n",
           "## Clusters\n"]
    for c in plan["clusters"]:
        kind = "read-only" if c["read_only"] else "read/write"
        out.append(f"### `{c['cluster']}` → module `{c['suggested_module']}` ({kind})\n")
        out.append("| Method | Path | Line |")
        out.append("|---|---|---|")
        for e in c["endpoints"]:
            out.append(f"| {e['method']} | `{e['path']}` | {e['line']} |")
        out.append("")
    if plan["preserve_markers"]:
        out.append("## Preserve markers\n")
        out += [f"- **{m}** (`{ev}`)" for m, ev in plan["preserve_markers"].items()]
    if plan["side_effects"]:
        out.append("\n## Side effects\n")
        out += [f"- {m} (`{ev}`)" for m, ev in plan["side_effects"].items()]
    out.append("\n## Existing tests\n")
    if plan["tests"]:
        out += [f"- `{t}` covers {', '.join(covers)}" for t, covers in plan["tests"].items()]
    else:
        out.append("**None — every cluster must be pinned before its extraction phase.**")
    out.append("\n## Extraction phases (safest first)\n")
    out += [f"{p['phase']}. **{p['cluster']}** — {p['action']}" for p in plan["phases"]]
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="Plan batch endpoint refactoring.")
    parser.add_argument("--root", default=".", help="project root to scan (default: cwd)")
    parser.add_argument("--file", help="plan decomposition of this route-defining file "
                                       "(path relative to root, or absolute)")
    parser.add_argument("--format", choices=["ascii", "md", "json"], default="ascii")
    parser.add_argument("--depth", type=int, default=6, help="dependency depth (default 6)")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        sys.exit(2)
    repo = te.Repo(root)
    if not repo.files:
        print(f"error: no source files found under {root}", file=sys.stderr)
        sys.exit(2)

    if args.file:
        target = Path(args.file)
        target = (root / target).resolve() if not target.is_absolute() else target.resolve()
        plan = plan_file(repo, target, args.depth)
        if plan is None:
            print(f"error: no routes detected in {args.file}. Run without --file "
                  "for the inventory of route-defining files.", file=sys.stderr)
            sys.exit(1)
        if args.format == "json":
            print(json.dumps(plan, indent=2, ensure_ascii=False))
        elif args.format == "md":
            print(render_plan_md(plan))
        else:
            print(render_plan_ascii(plan))
    else:
        rows = inventory(repo)
        if not rows:
            print("No routes detected in this repository.", file=sys.stderr)
            sys.exit(1)
        if args.format == "json":
            print(json.dumps(rows, indent=2, ensure_ascii=False))
        else:
            print(render_inventory_ascii(rows))


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(0)
