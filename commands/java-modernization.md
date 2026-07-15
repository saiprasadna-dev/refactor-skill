---
description: Run the Java modernization workflow (assess, plan, migrate, validate, report) on the current repository
argument-hint: "[target, e.g. 'Java 21 + Spring Boot 3' | 'assess only' | module path]"
---

Run the java-modernization skill workflow on this repository.

Target / scope requested by the user: $ARGUMENTS

If no target was given, first run the read-only assessment, then propose a
target (typically Java 21 + Spring Boot 3.x) and the phased plan, and wait
for confirmation before modifying any file.

Follow the skill strictly:

1. **Assessment (read-only):** build tool, modules, entry points, Java /
   Spring Boot / Spring Framework versions, dependency ecosystem, test
   framework, database and messaging layers, deprecated APIs, risk
   hotspots. No file modifications in this pass.
2. **Plan:** phased (build-breaking upgrades → framework compatibility →
   dependency alignment → compiler fixes → test updates → safe refactoring
   → reporting), listing what changes, what might break, what needs manual
   review, what stays untouched.
3. **Migrate incrementally,** module by module, keeping the build green.
   Consult the skill's knowledge base (`scripts/search.py`, domains:
   compat / deprecated / jakarta) before setting versions, replacing APIs,
   or renaming javax imports. Flag high-risk entries instead of auto-fixing;
   never migrate javax packages marked KEEP.
4. **Validate** after every major step: compile, run tests, compare
   discovered-test counts before and after.
5. **Report:** write MODERNIZATION_REPORT.md per the skill's template.

Non-negotiable: do not change business logic, domain behavior, API
contracts, calculations, database business rules, validations, or
authorization rules. Anything that might affect behavior becomes a manual
review item, not a change.

Respond in this order: Assessment, Modernization plan, Changes made,
Validation notes, Remaining risks or manual items, Final migration summary.
