#!/usr/bin/env bash
# Sync the source-of-truth skill (skills/) into the local Claude Code
# installation directory (.claude/skills/). Run after editing anything
# under skills/java-modernization/.
set -euo pipefail
cd "$(dirname "$0")/.."

rm -rf .claude/skills/java-modernization
mkdir -p .claude/skills
cp -R skills/java-modernization .claude/skills/

echo "Synced skills/java-modernization -> .claude/skills/java-modernization"
