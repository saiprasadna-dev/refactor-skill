#!/usr/bin/env bash
# Sync every source-of-truth skill (skills/*) into the local Claude Code
# installation directory (.claude/skills/). Run after editing anything
# under skills/.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p .claude/skills
for src in skills/*/; do
  name="$(basename "$src")"
  rm -rf ".claude/skills/$name"
  cp -R "$src" ".claude/skills/$name"
  echo "Synced skills/$name -> .claude/skills/$name"
done
