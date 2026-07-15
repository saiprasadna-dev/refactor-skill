# refactor-skill

Reusable [Claude Code](https://claude.com/claude-code) skills for safe,
behavior-preserving refactoring of enterprise codebases.

## Skills

### java-modernization

Analyze, upgrade, refactor, validate, and document any Java or Spring Boot
application **while preserving business logic exactly**. Works best for
multi-module Maven or Gradle projects, especially legacy-to-modern upgrades:

- Java 8/11/17 → Java 21
- Spring Boot 2.x → 3.x
- javax → jakarta migrations
- Maven/Gradle and dependency modernization
- Deprecated API replacement, build/test fixes after migration
- Migration reports and upgrade planning

See [java-modernization/SKILL.md](java-modernization/SKILL.md) for the full
skill definition, plus:

- [references/upgrade-guides.md](java-modernization/references/upgrade-guides.md)
  — version-specific migration checklists (Java 21, Spring Boot 3, jakarta,
  Hibernate 6, JUnit 5)
- [references/report-template.md](java-modernization/references/report-template.md)
  — required structure for the final modernization report

## Installation

Copy the skill directory into the skills location Claude Code reads from:

**Per project** (checked into the target repo, shared with the team):

```bash
mkdir -p .claude/skills
cp -r path/to/refactor-skill/java-modernization .claude/skills/
```

**Personal** (available in all your projects):

```bash
mkdir -p ~/.claude/skills
cp -r path/to/refactor-skill/java-modernization ~/.claude/skills/
```

Claude Code discovers the skill automatically from its `SKILL.md`
frontmatter and triggers it when a task matches (e.g. "upgrade this service
to Spring Boot 3", "migrate this project to Java 21"). You can also invoke
it explicitly with `/java-modernization`.

## Design principles

- **Business logic is untouchable.** Pricing, workflows, API contracts,
  validations, and domain rules stay exactly as they are; anything that
  might change behavior is flagged for manual review instead of applied.
- **Assess and plan before editing.** The first pass over a repository is
  read-only.
- **Small, compiling steps.** Changes land module by module and the build
  must stay green after each major step.
- **Auditable output.** Every run ends with a migration report covering
  versions, files changed, fixes applied, and manual review items.
