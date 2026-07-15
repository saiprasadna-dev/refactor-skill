# Development guidelines

This repository packages the **java-modernization** skill for Claude Code
as a plugin (marketplace-installable) and as a plain copyable skill.

## Source of truth

- `skills/java-modernization/` is the single source of truth for the skill
  (SKILL.md, references/, data/, scripts/).
- `.claude/skills/java-modernization/` is a generated mirror so that
  cloning this repo into a project activates the skill directly. **Never
  edit it by hand** — edit `skills/` and run `scripts/sync-skills.sh`.

## Making changes

1. Edit files under `skills/java-modernization/`, `agents/`, or `commands/`.
2. Run `bash scripts/sync-skills.sh` to regenerate `.claude/skills/`.
3. Test the search tool:
   `python3 skills/java-modernization/scripts/search.py "junit" --domain compat`
   (stdlib only — do not add external Python dependencies).
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
