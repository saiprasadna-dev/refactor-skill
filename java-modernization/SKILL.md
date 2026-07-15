---
name: java-modernization
description: >-
  Enterprise Java modernization skill for analyzing, upgrading, refactoring,
  validating, and documenting Java and Spring Boot applications while
  preserving business logic exactly. Use when a Java project needs a Java
  version upgrade (8/11/17 to 21), a Spring Boot 2.x to 3.x upgrade, a
  javax-to-jakarta migration, Maven/Gradle or dependency modernization,
  deprecated API replacement, build or test fixes after migration, safe
  behavior-preserving refactoring, or a migration report and upgrade plan.
  Works best for multi-module Maven or Gradle projects and legacy-to-modern
  upgrades.
---

# Java Modernization Skill

## Core mission

Modernize the codebase **without changing business logic**.

The highest priority is preserving existing behavior exactly. Technical
implementation may change, but business rules, workflows, calculations, API
contracts, persistence behavior, validations, security behavior, and domain
outcomes must remain unchanged unless the user explicitly approves a required
compatibility change.

## Non-negotiable rule

**Do not change business logic.** This means:

- Do not change pricing, booking, cancellation, tax, commission, payment,
  checkout, search, or domain-specific rules.
- Do not change workflows or user-visible behavior.
- Do not alter API contracts unless a framework migration requires an
  unavoidable compatibility fix.
- Do not modify database business rules or domain semantics.
- Do not remove validations, permissions, or authorization rules.
- Do not refactor for style if it risks behavior change.

If a change might affect behavior, **stop and flag it as a manual review
item** instead of applying it.

## Supported project types

This skill must work for any Java application, including:

- Spring Boot monoliths
- Multi-module Maven projects
- Gradle applications
- Microservices
- REST APIs
- JPA/Hibernate apps
- Messaging-based systems
- Internal enterprise platforms
- Domain-heavy systems such as travel, hotels, finance, insurance, ecommerce,
  healthcare, or CRM

Do not assume the project is hotel-related or domain-specific.

## Main responsibilities

1. Detect project structure automatically.
2. Identify Java, Spring Boot, Maven/Gradle, and dependency versions.
3. Build a modernization plan before making changes.
4. Apply changes incrementally, module by module.
5. Keep the code compiling after each major step.
6. Fix dependency conflicts, import issues, and compiler errors.
7. Update tests when framework upgrades require it.
8. Generate a clear migration report at the end.

## Workflow

Work through these phases in order. Do not skip the assessment or planning
phases, even for a seemingly simple upgrade.

### Phase 1: Assessment

Inspect the repository and identify:

- build tool (Maven or Gradle, wrapper versions)
- root modules and module graph
- application entry points
- Java version (compiler source/target/release, toolchains)
- Spring Boot version
- Spring Framework version
- dependency ecosystem (BOMs, parent POMs, version properties)
- test framework (JUnit 4/5, Mockito, Spring Test, Testcontainers)
- database layer (JPA/Hibernate versions, JDBC drivers, migrations)
- messaging layer (Kafka, JMS, RabbitMQ, etc.)
- any obvious deprecated APIs
- any risky compatibility hotspots

**Do not modify files during the first assessment pass unless explicitly
asked.**

### Phase 2: Planning

Create a phased modernization plan that prioritizes, in order:

1. build-breaking version upgrades
2. framework compatibility changes
3. dependency alignment
4. compiler fixes
5. test updates
6. safe refactoring
7. documentation and reporting

The plan must list:

- what will be changed
- what might break
- what needs manual review
- what will be left untouched

### Phase 3: Incremental modernization

Apply changes module by module, keeping the project compiling after each
major step. Follow the modernization rules below and the version-specific
guidance in [references/upgrade-guides.md](references/upgrade-guides.md).

### Phase 4: Validation

After every major change:

- verify the project structure still makes sense
- check for compile errors
- fix imports and package changes
- resolve dependency mismatches
- check failing tests
- continue only after the codebase is stable

If a full build command is available (`mvn verify`, `./gradlew build`),
prefer actually running it when the environment supports it; otherwise apply
it conceptually by tracing compilation and test impact.

### Phase 5: Reporting

Generate a migration report using the structure in
[references/report-template.md](references/report-template.md) and commit it
to the repository (e.g. `MODERNIZATION_REPORT.md`).

## Modernization rules

Allowed:

- upgrade Java versions
- upgrade Spring Boot and compatible libraries
- update Maven/Gradle plugins
- replace deprecated APIs with supported ones
- improve code readability where behavior stays identical
- modernize syntax where safe
- update tests for framework changes
- improve build configuration
- remove obsolete configuration

Not allowed:

- changing business logic
- changing domain behavior
- changing API behavior without approval
- altering calculation logic
- changing database business rules
- making speculative architecture rewrites
- rewriting working code just for style

## Safe refactoring guidelines

Prefer refactoring that preserves exact behavior:

- constructor injection instead of field injection
- `java.time` instead of legacy date APIs
- SLF4J over direct console logging
- better generics and type safety
- safe Stream usage
- null-safe improvements
- cleaner exception handling
- supported framework annotations
- supported JUnit/Mockito patterns
- safer resource handling (try-with-resources)

Use modern Java features only when they do not change behavior:

- lambdas
- switch expressions
- pattern matching
- records — only when immutability and serialization compatibility are safe
- text blocks — only when the produced output remains identical

## Testing workflow

Update or add tests only as needed to preserve confidence during
modernization:

- JUnit 4 → JUnit 5 migration
- Mockito compatibility
- Spring test annotations
- integration tests
- test utilities
- compatibility fixes for upgraded libraries

**Do not reduce test coverage** unless absolutely necessary and clearly
documented in the migration report.

## Security and dependency review

Look for:

- hardcoded secrets
- outdated vulnerable libraries
- weak crypto defaults
- unsafe deserialization
- risky serialization formats
- obsolete auth or security configuration

Fix security issues only when the fix does not alter business behavior;
otherwise flag them for manual review.

## Output format

Always respond in this order:

1. Assessment
2. Modernization plan
3. Changes made
4. Validation notes
5. Remaining risks or manual items
6. Final migration summary

The final migration report must follow
[references/report-template.md](references/report-template.md).

## Success criteria

The task is complete only when:

- business logic is preserved
- build configuration is updated
- the project is compatible with the target Java/Spring versions
- compile issues are fixed
- tests are updated where needed
- the repo has a clear modernization report

## Operating style

Be methodical. Be conservative. Be repository-aware. Use evidence from the
codebase, not guesses. Prefer small safe steps over large risky rewrites.
