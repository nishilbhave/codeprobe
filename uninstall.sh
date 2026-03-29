#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$HOME/.claude/skills"

echo "Uninstalling codeprobe-claude..."

for skill_dir in "$SCRIPT_DIR"/skills/*/; do
    skill_name=$(basename "$skill_dir")
    target="$SKILLS_DIR/$skill_name"

    if [ -L "$target" ]; then
        rm "$target"
        echo "✅ Removed $skill_name"
    elif [ -e "$target" ]; then
        echo "⚠️  $target exists but is not a symlink — skipping"
    fi
done

echo "Uninstall complete."
