#!/usr/bin/env python3
"""Search the java-modernization knowledge base.

Stdlib only — no external dependencies. Works with python3 (or `py -3` on
Windows).

Usage:
  python3 scripts/search.py "<query>" [--domain DOMAIN] [--format FMT] [--top N]

Domains:
  compat      version-compatibility.csv  (which versions align with the target)
  deprecated  deprecated-apis.csv        (old API -> replacement, with risk)
  jakarta     javax-jakarta-map.csv      (javax package -> migrate or keep)
  all         search every domain (default)

Formats: ascii (default, terminal tables), md (markdown), json (machine-readable)

Examples:
  python3 scripts/search.py "spring security"
  python3 scripts/search.py "javax.sql" --domain jakarta
  python3 scripts/search.py "junit" --domain compat --format md
  python3 scripts/search.py "SimpleDateFormat" --format json
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DOMAINS = {
    "compat": "version-compatibility.csv",
    "deprecated": "deprecated-apis.csv",
    "jakarta": "javax-jakarta-map.csv",
}


def tokenize(text):
    return [t for t in re.findall(r"[a-z0-9.@]+", text.lower()) if t]


def score_row(tokens, row):
    """Simple TF scoring with a bonus for matches in the first (key) column."""
    values = list(row.values())
    key_field = (values[0] or "").lower()
    full_text = " ".join(v or "" for v in values).lower()
    score = 0
    for token in tokens:
        occurrences = full_text.count(token)
        if occurrences == 0:
            continue
        score += occurrences
        if token in key_field:
            score += 3
    # Require every token to appear somewhere for multi-word queries.
    if len(tokens) > 1 and not all(t in full_text for t in tokens):
        return 0
    return score


def search(query, domain, top):
    tokens = tokenize(query)
    if not tokens:
        return []
    selected = DOMAINS.items() if domain == "all" else [(domain, DOMAINS[domain])]
    hits = []
    for name, filename in selected:
        path = DATA_DIR / filename
        if not path.is_file():
            print(f"warning: missing data file {path}", file=sys.stderr)
            continue
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                s = score_row(tokens, row)
                if s > 0:
                    hits.append({"domain": name, "score": s, **row})
    hits.sort(key=lambda h: -h["score"])
    return hits[:top]


def render_ascii(hits):
    lines = []
    for hit in hits:
        fields = [(k, v) for k, v in hit.items() if k not in ("domain", "score") and v]
        width = max(len(k) for k, _ in fields)
        lines.append(f"[{hit['domain']}] (score {hit['score']})")
        for key, value in fields:
            lines.append(f"  {key.ljust(width)} : {value}")
        lines.append("-" * 72)
    return "\n".join(lines)


def render_md(hits):
    blocks = []
    for hit in hits:
        fields = [(k, v) for k, v in hit.items() if k not in ("domain", "score") and v]
        rows = "\n".join(f"| {k} | {v} |" for k, v in fields)
        blocks.append(
            f"**{hit['domain']}** (score {hit['score']})\n\n"
            f"| field | value |\n|---|---|\n{rows}\n"
        )
    return "\n".join(blocks)


def main():
    parser = argparse.ArgumentParser(description="Search the java-modernization knowledge base.")
    parser.add_argument("query", help="search terms, e.g. 'spring security' or 'javax.sql'")
    parser.add_argument("--domain", choices=[*DOMAINS, "all"], default="all")
    parser.add_argument("--format", choices=["ascii", "md", "json"], default="ascii")
    parser.add_argument("--top", type=int, default=10, help="max results (default 10)")
    args = parser.parse_args()

    hits = search(args.query, args.domain, args.top)
    if not hits:
        print(f"No results for '{args.query}' in domain '{args.domain}'. "
              "Try broader terms or --domain all.", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(hits, indent=2, ensure_ascii=False))
    elif args.format == "md":
        print(render_md(hits))
    else:
        print(render_ascii(hits))


if __name__ == "__main__":
    main()
