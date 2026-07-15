# Java Modernization — Claude Code skill, agent & plugin

Enterprise Java modernization intelligence for [Claude Code](https://claude.com/claude-code)
and compatible AI agents. Analyze, upgrade, refactor, validate, and document
**any** Java or Spring Boot application — **while preserving business logic
exactly**.

Covers the classic legacy-to-modern paths:

- **Java 8 / 11 / 17 → Java 21**
- **Spring Boot 2.x → 3.x** (Spring Framework 6, Spring Security 6)
- **javax → jakarta** namespace migration
- Hibernate 5 → 6, JUnit 4 → 5, Mockito, Jackson, Maven/Gradle plugin alignment
- Deprecated API replacement, dependency modernization, post-migration
  build/test fixes, migration reports and upgrade planning

## What's inside

| Piece | Path | Purpose |
|---|---|---|
| **Skill** (auto-activates) | `skills/java-modernization/SKILL.md` | Priority rules, 5-step workflow (assess → plan → migrate → validate → report), behavior-preservation guardrails |
| **Knowledge base** | `skills/java-modernization/data/*.csv` | ~30-component version compatibility matrix, 30+ deprecated-API replacements with behavior-risk ratings, full javax→jakarta package map (including which packages must **stay** javax) |
| **Search engine** | `skills/java-modernization/scripts/search.py` | Dependency-free Python 3 search over the knowledge base (ascii / markdown / json output) |
| **References** | `skills/java-modernization/references/` | Path-specific upgrade checklists and the required migration-report template |
| **Slash command** | `commands/java-modernization.md` | `/java-modernization` — run the full workflow on the current repo |
| **Agent** | `agents/java-modernizer.md` | `java-modernizer` subagent for end-to-end delegated migrations |
| **Plugin manifest** | `.claude-plugin/` | Marketplace-installable packaging |

## Installation

### Option 1 — Claude Code plugin marketplace (recommended)

```
/plugin marketplace add saiprasadna-dev/refactor-skill
/plugin install java-modernization@refactor-skill
```

This installs the skill, the `/java-modernization` command, and the
`java-modernizer` agent in one step.

### Option 2 — Copy the skill into a project

```bash
git clone https://github.com/saiprasadna-dev/refactor-skill
mkdir -p your-project/.claude/skills
cp -R refactor-skill/skills/java-modernization your-project/.claude/skills/
```

### Option 3 — Personal (all your projects)

```bash
mkdir -p ~/.claude/skills
cp -R refactor-skill/skills/java-modernization ~/.claude/skills/
```

## Usage

**Skill mode (auto-activate).** Just describe the task in a Java repo:

> "Upgrade this service to Spring Boot 3 and Java 21"
> "Migrate javax to jakarta in the payments module"
> "Fix the build after the JUnit 5 upgrade"

**Workflow mode (slash command).**

```
/java-modernization Java 21 + Spring Boot 3
/java-modernization assess only
```

**Agent mode.** Delegate the whole migration to the `java-modernizer`
subagent for long-running, end-to-end upgrades.

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
├── skills/
│   └── java-modernization/  # SOURCE OF TRUTH
│       ├── SKILL.md
│       ├── data/            # searchable CSV knowledge base
│       ├── references/      # upgrade guides + report template
│       └── scripts/         # search.py
├── skill.json               # skill metadata
└── CLAUDE.md                # development guidelines
```

Contributions: edit under `skills/`, run `bash scripts/sync-skills.sh`,
and keep versions aligned across `skill.json` and `.claude-plugin/*.json`
(see [CLAUDE.md](CLAUDE.md)).

## License

[MIT](LICENSE)
