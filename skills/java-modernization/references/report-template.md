# Migration Report Template

Write the final report to `MODERNIZATION_REPORT.md` in the target
repository's root (or the path the user requests). Fill every section; write
"None" rather than omitting a section, so the report is auditable.

```markdown
# Modernization Report

## Source project summary

<!-- What the application is, build tool, module layout, entry points. -->

## Versions before and after

| Component        | Before | After |
|------------------|--------|-------|
| Java             |        |       |
| Spring Boot      |        |       |
| Spring Framework |        |       |
| Build tool       |        |       |
| Hibernate/JPA    |        |       |
| JUnit            |        |       |
| Mockito          |        |       |

## Modules affected

<!-- Per module: what changed and why. -->

## Files changed

<!-- Grouped by category: build files, source, tests, config, docs. -->

## Dependency upgrades

<!-- Old coordinate/version → new coordinate/version, and the reason. -->

## Framework migrations

<!-- javax→jakarta, security config rewrite, Hibernate 5→6, JUnit 4→5, etc. -->

## Compile/test issues fixed

<!-- Each error encountered and how it was resolved. -->

## Manual review items

<!-- Anything that could affect behavior and was deliberately NOT changed,
     plus security findings flagged instead of fixed. -->

## Behavior-preservation notes

<!-- Evidence that business logic is unchanged: test results before/after,
     API contracts verified, areas intentionally left untouched. -->
```

## Reporting rules

- Every flagged manual review item from the modernization phases must appear
  in **Manual review items** — nothing gets silently dropped.
- Record test counts and results before and after the migration in
  **Behavior-preservation notes**; a drop in discovered tests is a red flag
  that must be explained.
- If test coverage was reduced anywhere, state where and why.
