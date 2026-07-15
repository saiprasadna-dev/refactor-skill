# Development guidelines

This repository packages two Claude Code skills as one plugin
(marketplace-installable) and as plain copyable skills:
**endpoint-rearchitect** (language-agnostic endpoint re-architecture) and
**java-modernization** (Java/Spring upgrades).

## Source of truth

- `skills/<name>/` directories are the single source of truth
  (SKILL.md, references/, data/, scripts/).
- `.claude/skills/` is a generated mirror so that cloning this repo into a
  project activates the skills directly. **Never edit it by hand** — edit
  `skills/` and run `scripts/sync-skills.sh` (syncs every skill).

## Making changes

1. Edit files under `skills/`, `agents/`, or `commands/`.
2. Run `bash scripts/sync-skills.sh` to regenerate `.claude/skills/`.
3. Test the tools (stdlib only — do not add external Python dependencies):
   `python3 skills/java-modernization/scripts/search.py "junit" --domain compat`
   `python3 skills/endpoint-rearchitect/scripts/trace_endpoint.py / --list-routes --root <sample>`
   `python3 skills/endpoint-rearchitect/scripts/plan_refactor.py --root <sample>`
   The universal tracer and batch planner must keep passing against
   fixtures in at least TS/Hono, JS/Express (CommonJS), Java/Spring,
   Python/FastAPI, Go/Gin, and a single-file god-file app. JS/Go route
   detection must reject non-route `.get('key')` lookups (paths start
   with `/`).
4. Keep versions in sync across `skill.json`,
   `.claude-plugin/plugin.json`, and `.claude-plugin/marketplace.json`.

## Data files

- `data/*.csv` rows must stay factual and verifiable; never add guessed
  version numbers.
- `javax-jakarta-map.csv`: packages marked `KEEP` are JDK packages —
  adding a MIGRATE row requires checking it actually moved to jakarta.
- `deprecated-apis.csv`: `behavior_risk` is load-bearing — `high` means
  the skill flags instead of auto-fixing.

## Conventions

- The skill must stay domain-agnostic: no hotel/travel/finance-specific
  rules in skill text.
- The core invariant is behavior preservation; any new guidance that could
  change runtime behavior must route through the manual-review mechanism.
