# refactor-skill — modernization & re-architecture skills for Claude Code

Skills, agents, and commands for [Claude Code](https://claude.com/claude-code)
that modernize and re-architect codebases **while preserving business logic
exactly**. Two skills ship in this plugin:

- **endpoint-rearchitect** — language-agnostic: given one endpoint (e.g.
  `/search`), trace it end-to-end, pin its behavior, then restructure.
  Also decomposes god files — one file with many endpoints and lots of
  code — refactoring all of them cluster by cluster. Supports Java/Kotlin,
  JavaScript/TypeScript, Python, Go, C#, Ruby, PHP.
- **java-modernization** — deep Java/Spring specialization: version
  upgrades, Spring Boot 2→3, javax→jakarta, dependency alignment, with a
  searchable knowledge base.

## endpoint-rearchitect (any language)

The universal tracer (`skills/endpoint-rearchitect/scripts/trace_endpoint.py`,
stdlib-only Python 3) detects routes across frameworks — Spring, JAX-RS,
Ktor, Express, Hono, NestJS, Fastify, Next.js, FastAPI, Flask, Django,
Gin, Echo, Chi, Fiber, net/http, ASP.NET Core (attributes + minimal APIs),
Rails, Sinatra, Laravel, Symfony — resolving router mount prefixes (ESM
and CommonJS) and `include_router` prefixes. It walks the dependency graph
from the handler and reports every file in the slice with:

- **preserve markers**: auth, validation, transaction boundaries, caching,
  retries, idempotency
- **side effects**: database access, external HTTP, messaging, email/SMS,
  object storage, schedulers
- **existing tests** covering the slice — with a loud warning when none exist

```bash
cd skills/endpoint-rearchitect
python3 scripts/trace_endpoint.py /search --root /path/to/project
python3 scripts/trace_endpoint.py /api/orders/{id} --root . --format md
python3 scripts/trace_endpoint.py / --list-routes --root .   # route inventory
```

The skill then drives the 5-phase playbook: trace → behavior contract
(`modernization/endpoints/<slug>.contract.md`) → characterization tests
that pass on the untouched code → restructure in always-green commits →
validate and report. A slice with zero tests gets no structural change
until it is pinned.

**God files** (many endpoints + lots of code in one file) get the batch
planner:

```bash
python3 scripts/plan_refactor.py --root /path/to/project            # hotspot inventory
python3 scripts/plan_refactor.py --root . --file src/app.js         # decomposition plan
```

It clusters all endpoints in the file by resource, marks clusters
read-only vs read/write, and phases their extraction safest-first; the
god-file decomposition playbook then extracts cluster by cluster (pin →
extract → delegating mount → full suite → commit) until the file is just
a composition root.

## java-modernization (Java/Spring deep-dive)

Enterprise Java modernization: analyze, upgrade, refactor, validate, and
document any Java or Spring Boot application.

Covers the classic legacy-to-modern paths:

- **Java 8 / 11 / 17 → Java 21**
- **Spring Boot 2.x → 3.x** (Spring Framework 6, Spring Security 6)
- **javax → jakarta** namespace migration
- Hibernate 5 → 6, JUnit 4 → 5, Mockito, Jackson, Maven/Gradle plugin alignment
- Deprecated API replacement, dependency modernization, post-migration
  build/test fixes, migration reports and upgrade planning
- A Spring-specific slice tracer with interface→implementation and
  JPA-entity resolution

## What's inside

| Piece | Path | Purpose |
|---|---|---|
| **Skill: endpoint-rearchitect** | `skills/endpoint-rearchitect/SKILL.md` | Language-agnostic 5-phase re-architecture workflow with universal tracer |
| **Universal tracer** | `skills/endpoint-rearchitect/scripts/trace_endpoint.py` | Route detection + dependency walking + behavior markers for 7 languages / 20+ frameworks |
| **Batch planner** | `skills/endpoint-rearchitect/scripts/plan_refactor.py` | Hotspot inventory + god-file decomposition plans (clusters, risk, safest-first phases) |
| **Playbooks** | `skills/endpoint-rearchitect/references/` | Single-endpoint (trace → contract → pin → restructure → validate, per-stack test-harness table) and god-file decomposition |
| **Skill: java-modernization** | `skills/java-modernization/SKILL.md` | Priority rules, 5-step workflow (assess → plan → migrate → validate → report), behavior-preservation guardrails |
| **Knowledge base** | `skills/java-modernization/data/*.csv` | ~30-component version compatibility matrix, 30+ deprecated-API replacements with behavior-risk ratings, full javax→jakarta package map (including which packages must **stay** javax) |
| **Search engine** | `skills/java-modernization/scripts/search.py` | Dependency-free Python 3 search over the knowledge base (ascii / markdown / json output) |
| **Spring slice tracer** | `skills/java-modernization/scripts/trace_endpoint.py` | Spring-specific tracing with interface→impl and JPA-entity resolution |
| **References** | `skills/java-modernization/references/` | Upgrade checklists, the Java endpoint re-architecture playbook, and the migration-report template |
| **Slash commands** | `commands/` | `/rearchitect-endpoint /search` (any language) · `/decompose-file src/app.js` (refactor ALL endpoints in a god file) · `/java-endpoint /search` (Spring) · `/java-modernization` (full Java workflow) |
| **Agents** | `agents/` | `endpoint-tracer` (read-only slice mapping + behavior contract, any language) · `behavior-guardian` (characterization tests + behavior-change diff review, any language) · `java-modernizer` (end-to-end Java migrations) |
| **Plugin manifest** | `.claude-plugin/` | Marketplace-installable packaging |

## Installation

### Option 1 — Claude Code plugin marketplace (recommended)

```
/plugin marketplace add saiprasadna-dev/refactor-skill
/plugin install refactor-skill@refactor-skill
```

This installs both skills, the `/rearchitect-endpoint`,
`/java-modernization`, and `/java-endpoint` commands, and the
`endpoint-tracer`, `behavior-guardian`, and `java-modernizer` agents in
one step.

### Option 2 — Copy the skills into a project

```bash
git clone https://github.com/saiprasadna-dev/refactor-skill
mkdir -p your-project/.claude/skills
cp -R refactor-skill/skills/endpoint-rearchitect your-project/.claude/skills/
cp -R refactor-skill/skills/java-modernization  your-project/.claude/skills/
```

### Option 3 — Personal (all your projects)

```bash
mkdir -p ~/.claude/skills
cp -R refactor-skill/skills/endpoint-rearchitect ~/.claude/skills/
cp -R refactor-skill/skills/java-modernization  ~/.claude/skills/
```

## Usage

**Skill mode (auto-activate).** Just describe the task:

> "Re-architect the /search endpoint end to end" (any language)
> "Upgrade this service to Spring Boot 3 and Java 21"
> "Migrate javax to jakarta in the payments module"
> "Fix the build after the JUnit 5 upgrade"

**Workflow mode (slash commands).**

```
/rearchitect-endpoint /search          # any language / framework
/rearchitect-endpoint /api/orders/{id}
/decompose-file src/app.js             # refactor ALL endpoints in a god file
/decompose-file                        # scan the repo for hotspots first
/java-modernization Java 21 + Spring Boot 3
/java-modernization assess only
/java-endpoint /search                 # Spring-specific deep trace
```

**Endpoint re-architecture** (`/rearchitect-endpoint`, `/java-endpoint`)
runs a strict 5-phase playbook: trace the slice → capture the behavior
contract to `modernization/endpoints/<slug>.contract.md` → pin behavior
with characterization tests that pass on the untouched code → restructure
in small always-green commits with those tests unmodified → validate and
report. A slice with zero tests gets no structural change until it is
pinned.

**Agent mode.** Delegate to the subagents: `java-modernizer` for
long-running end-to-end upgrades, `endpoint-tracer` for read-only slice
mapping and behavior contracts, `behavior-guardian` for characterization
tests and behavior-change diff review.

**Trace an endpoint directly** (Python 3, no dependencies):

```bash
cd skills/endpoint-rearchitect          # any language
python3 scripts/trace_endpoint.py /search --root /path/to/project
python3 scripts/trace_endpoint.py / --list-routes --root /path/to/project

cd skills/java-modernization            # Spring deep trace
python3 scripts/trace_endpoint.py /api/orders/{id} --root . --format md
```

**Direct knowledge-base queries** (Python 3, no dependencies):

```bash
cd skills/java-modernization
python3 scripts/search.py "spring security"                      # everything relevant
python3 scripts/search.py "javax.sql" --domain jakarta           # migrate or keep?
python3 scripts/search.py "junit" --domain compat --format md    # version alignment
python3 scripts/search.py "SimpleDateFormat" --format json       # machine-readable
```

## Design principles

- **Business logic is untouchable.** Pricing, workflows, API contracts,
  validations, authorization, and domain rules stay exactly as they are.
  Anything that might change behavior is flagged as a manual review item
  instead of applied.
- **Evidence over memory.** Version numbers and migration decisions come
  from the knowledge base and the repository itself, never guesses.
- **Assess and plan before editing.** The first pass over a repository is
  strictly read-only.
- **Small, compiling steps.** Changes land module by module and the build
  must stay green after each major step; test counts are compared before
  and after.
- **Auditable output.** Every run ends with a `MODERNIZATION_REPORT.md`
  covering versions before/after, files changed, dependency upgrades,
  fixes applied, manual review items, and behavior-preservation notes.
- **Domain-agnostic.** Works for travel, finance, insurance, ecommerce,
  healthcare, CRM, or any other Java system — nothing is assumed.

## Repository layout

```
.
├── .claude-plugin/          # plugin.json + marketplace.json (plugin packaging)
├── .claude/skills/          # generated mirror — activates on direct clone
├── agents/                  # java-modernizer subagent
├── commands/                # /java-modernization slash command
├── scripts/                 # repo tooling (sync-skills.sh)
├── skills/                  # SOURCE OF TRUTH
│   ├── endpoint-rearchitect/
│   │   ├── SKILL.md
│   │   ├── references/      # language-agnostic playbook
│   │   └── scripts/         # universal trace_endpoint.py (7 languages)
│   └── java-modernization/
│       ├── SKILL.md
│       ├── data/            # searchable CSV knowledge base
│       ├── references/      # upgrade guides + report template
│       └── scripts/         # search.py + Spring trace_endpoint.py
├── skill.json               # skill metadata
└── CLAUDE.md                # development guidelines
```

Contributions: edit under `skills/`, run `bash scripts/sync-skills.sh`,
and keep versions aligned across `skill.json` and `.claude-plugin/*.json`
(see [CLAUDE.md](CLAUDE.md)).

## License

[MIT](LICENSE)
