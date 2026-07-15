---
name: java-modernization
description: >-
  Enterprise Java modernization skill for analyzing, upgrading, refactoring,
  validating, and documenting Java and Spring Boot applications while
  preserving business logic exactly. Includes a searchable local knowledge
  base of version compatibility, deprecated API replacements, and the full
  javax-to-jakarta package map. Use when a Java project needs a Java version
  upgrade (8/11/17 to 21), a Spring Boot 2.x to 3.x upgrade, a
  javax-to-jakarta migration, Maven/Gradle or dependency modernization,
  deprecated API replacement, build or test fixes after migration, safe
  behavior-preserving refactoring, endpoint-by-endpoint re-architecture
  (trace an endpoint like /search end-to-end, pin its behavior, then
  restructure), or a migration report and upgrade plan. Works best for
  multi-module Maven or Gradle projects.
---

# Java Modernization

Modernize any Java or Spring Boot codebase **without changing business
logic**. Technical implementation may change; business rules, workflows,
calculations, API contracts, persistence behavior, validations, security
behavior, and domain outcomes must remain identical unless the user
explicitly approves a required compatibility change.

## When to apply

Use this skill for: Java version upgrades, Spring Boot upgrades, Maven or
Gradle upgrades, dependency modernization, deprecated API replacement,
build or test fixes after migration, safe refactoring without changing
business behavior, and migration reports or upgrade planning.

Works for any Java application — Spring Boot monoliths, multi-module Maven
projects, Gradle applications, microservices, REST APIs, JPA/Hibernate
apps, messaging-based systems, and domain-heavy enterprise platforms
(travel, finance, insurance, ecommerce, healthcare, CRM, …). **Never assume
a specific domain.**

Do NOT use this skill to implement new features, change domain behavior, or
redesign architecture — those are out of scope.

## Rule categories by priority

| Priority | Category | Key rule | Anti-pattern to prevent |
|---|---|---|---|
| P1 (critical) | Behavior preservation | Business logic, API contracts, validations, and security rules stay exactly equivalent; anything uncertain becomes a manual review item | "Improving" a calculation, removing a validation, silently changing a route matcher |
| P2 (critical) | Build integrity | The project compiles after every major step; never stack broken changes | Big-bang edits across modules with a broken build in between |
| P3 (high) | Framework compatibility | javax→jakarta, Spring Security 6 config, Hibernate 6, Boot 3 property renames — done mechanically per the knowledge base | Renaming JDK `javax.*` packages that must stay; hand-rolled security rewrites |
| P4 (high) | Dependency alignment | Versions come from the Spring Boot BOM wherever possible; explicit pins removed, conflicts resolved | Pinning random "latest" versions; duplicate javax+jakarta artifacts on the classpath |
| P5 (high) | Test integrity | Test counts compared before/after; JUnit 4→5 migrated without silent discovery loss | Surefire silently running 0 tests after upgrade |
| P6 (medium) | Security review | Hardcoded secrets, vulnerable libs, weak crypto found and flagged; fixed only when behavior-safe | "Fixing" security by changing auth behavior without approval |
| P7 (medium) | Safe refactoring | Only exact-behavior refactors: constructor injection, java.time, SLF4J, try-with-resources, modern syntax | Style rewrites of working code; records/text blocks where serialization or output changes |
| P8 (low) | Documentation | Migration report generated per template; every flagged item recorded | Finishing without an auditable report |

## Knowledge base search

A local, dependency-free search tool answers version and migration
questions with evidence instead of guesses. Requires Python 3.x (try
`python3`, then `python`, then `py -3`).

```bash
python3 scripts/search.py "<query>" [--domain compat|deprecated|jakarta|all] [--format ascii|md|json] [--top N]
```

| Domain | Data | Ask it things like |
|---|---|---|
| `compat` | `data/version-compatibility.csv` — legacy/minimum/target versions for ~30 components | "junit", "gradle", "lombok", "spring cloud" |
| `deprecated` | `data/deprecated-apis.csv` — old API → replacement with behavior-risk rating | "SimpleDateFormat", "WebSecurityConfigurerAdapter", "PowerMock" |
| `jakarta` | `data/javax-jakarta-map.csv` — which `javax.*` packages migrate and which must stay | "javax.sql", "javax.validation", "javax.annotation" |

Consult `compat` before setting any dependency version, `deprecated` before
replacing any API, and `jakarta` before renaming any `javax` import. Rows
marked `behavior_risk: high` or `action: KEEP` are stop signs: flag for
manual review instead of auto-fixing, and never migrate a KEEP package.

If a search returns no results, retry with broader terms and `--domain all`.
If it still returns nothing, say the knowledge base has no entry and reason
from the repository's actual code — never fabricate a version number.

## Endpoint slice tracer

For re-architecture work scoped to an endpoint, a second dependency-free
tool maps the full vertical slice:

```bash
python3 scripts/trace_endpoint.py <endpoint-path> [--root DIR] [--format ascii|md|json] [--depth N]
# e.g. python3 scripts/trace_endpoint.py /search --root /path/to/project
```

It finds the controller handler for the path (combining class-level and
method-level mappings, including `{path-variables}`), walks the dependency
graph through services, interface→implementation bindings, repositories,
entities, Feign/Rest clients, and messaging, and reports:

- **behavior markers that must be preserved** — `@Transactional`,
  `@PreAuthorize`/`@Secured`, `@Valid`, `@Cacheable`, listeners, retries
- **side effects** — external HTTP calls, Kafka/Rabbit/JMS publishing,
  direct SQL, email
- **existing tests touching the slice** — the current safety net; it warns
  loudly when a slice has none

The tracer is static and heuristic: always verify its map by reading the
code, and complete it with what static analysis misses (aspects,
interceptors, `@ControllerAdvice`, security filter-chain rules, config
properties, DB schema).

## Workflow

### Step 1 — Assessment (read-only)

Inspect the repository and identify: build tool and wrapper versions, root
modules and module graph, application entry points, Java version
(compiler release/toolchain), Spring Boot and Spring Framework versions,
dependency ecosystem (BOMs, parent POMs, version properties), test
framework, database layer, messaging layer, obvious deprecated APIs, and
risky compatibility hotspots.

**Do not modify files during this pass unless explicitly asked.**

### Step 2 — Planning

Produce a phased plan prioritizing: (1) build-breaking version upgrades,
(2) framework compatibility changes, (3) dependency alignment,
(4) compiler fixes, (5) test updates, (6) safe refactoring,
(7) documentation and reporting.

The plan must list what will be changed, what might break, what needs
manual review, and what will be left untouched. Get versions from the
`compat` domain, not from memory.

### Step 3 — Incremental modernization

Apply changes module by module, keeping the build green after each major
step. Follow [references/upgrade-guides.md](references/upgrade-guides.md)
for the path-specific checklists (Java 21, Spring Boot 3, javax→jakarta,
Hibernate 6, JUnit 5, dependency alignment).

Allowed: upgrading Java/Spring Boot/libraries/plugins, replacing deprecated
APIs with supported ones, behavior-identical readability improvements,
updating tests for framework changes, improving build configuration,
removing obsolete configuration.

Not allowed: changing business logic or domain behavior, changing API
behavior without approval, altering calculation logic, changing database
business rules, speculative architecture rewrites, rewriting working code
for style.

Prefer refactors that preserve exact behavior: constructor injection over
field injection, `java.time` over legacy date APIs, SLF4J over console
logging, better generics and type safety, safe Stream usage, null-safe
improvements, cleaner exception handling, supported framework annotations,
supported JUnit/Mockito patterns, try-with-resources. Modern Java features
(lambdas, switch expressions, pattern matching, records, text blocks) only
where behavior — including serialization shape and produced output — is
provably identical.

### Step 4 — Validation

After every major change: verify the project structure still makes sense,
check for compile errors, fix imports and package changes, resolve
dependency mismatches, check failing tests, and continue only once stable.
Prefer actually running the build (`mvn verify`, `./gradlew build`) when
the environment supports it. Compare discovered-test counts before and
after — a drop is a red flag that must be explained.

### Step 5 — Reporting

Write `MODERNIZATION_REPORT.md` using
[references/report-template.md](references/report-template.md). Every
flagged manual review item must appear in it — nothing is silently dropped.

## Endpoint re-architecture workflow

When the task is to re-architect a specific endpoint (e.g. "restructure
/search end-to-end"), switch to the playbook in
[references/endpoint-rearchitecture.md](references/endpoint-rearchitecture.md):

1. **Trace the slice** (read-only) with `scripts/trace_endpoint.py`, then
   verify and complete the map manually.
2. **Capture the behavior contract** to
   `modernization/endpoints/<slug>.contract.md` in the target repo:
   request/response contracts per status code, security behavior, side
   effects, observed business rules, non-functional behavior. Ambiguities
   become "Open questions" / manual review items.
3. **Pin behavior with characterization tests** that pass against the
   untouched code first. A slice with zero tests gets no structural change
   until it is pinned — this phase is blocking.
4. **Re-architect within the contract** in small always-green commits.
   Characterization tests stay unmodified and passing. Never change status
   codes or response fields, move `@Transactional` boundaries, alter cache
   or query semantics, reorder side effects, weaken validation or
   security, or silently fix bugs — pin bugs bug-for-bug and record them
   as manual review items.
5. **Validate and report**: full build and tests, compare test counts to
   the baseline, review the diff against the forbidden list, and append an
   "Endpoint re-architecture" section to `MODERNIZATION_REPORT.md`.

Scale to a whole application by repeating slice by slice; when endpoints
share a service, trace and pin all sharing endpoints before restructuring
the shared class.

## Testing rules

Update or add tests only as needed to preserve confidence: JUnit 4 → 5,
Mockito compatibility, Spring test annotations, integration tests, test
utilities, compatibility fixes for upgraded libraries. **Do not reduce test
coverage** unless absolutely necessary and clearly documented in the report.

## Security review

Look for hardcoded secrets, outdated vulnerable libraries, weak crypto
defaults, unsafe deserialization, risky serialization formats, and obsolete
auth configuration. Fix only when the fix cannot alter business behavior;
otherwise flag for manual review.

## Output format

Always respond in this order:

1. Assessment
2. Modernization plan
3. Changes made
4. Validation notes
5. Remaining risks or manual items
6. Final migration summary

## Success criteria

Complete only when: business logic is preserved, build configuration is
updated, the project is compatible with the target Java/Spring versions,
compile issues are fixed, tests are updated where needed, and the repo has
a clear modernization report.

## Operating style

Be methodical. Be conservative. Be repository-aware. Use evidence from the
codebase and the knowledge base, not guesses. Prefer small safe steps over
large risky rewrites. When in doubt, flag — don't change.
