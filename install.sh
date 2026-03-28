#!/bin/bash
set -e

SKILLS_DIR="$HOME/.claude/skills"
FROM_CURL=false

# Detect if running via curl pipe (no script file on disk)
if [ -t 0 ] || [ -f "$0" ]; then
    # Running directly -- use script's directory
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
else
    # Running via curl | bash -- clone to temp dir
    FROM_CURL=true
    TMPDIR=$(mktemp -d)
    echo "Cloning code-review-claude..."
    git clone --quiet https://github.com/nishilbhave/code-review-claude.git "$TMPDIR/code-review-claude"
    SCRIPT_DIR="$TMPDIR/code-review-claude"
    trap "rm -rf '$TMPDIR'" EXIT
fi

echo "Installing code-review-claude..."

# Create skills directory if needed
mkdir -p "$SKILLS_DIR"

# Install each skill
for skill_dir in "$SCRIPT_DIR"/skills/*/; do
    skill_name=$(basename "$skill_dir")
    target="$SKILLS_DIR/$skill_name"

    if [ -e "$target" ]; then
        if [ -t 0 ]; then
            echo "⚠️  $target already exists. Overwrite? (y/N)"
            read -r response
            if [[ ! "$response" =~ ^[Yy]$ ]]; then
                echo "Skipping $skill_name"
                continue
            fi
        fi
        rm -rf "$target"
    fi

    if [ "$FROM_CURL" = true ]; then
        # Copy when installed via curl (temp dir gets cleaned up)
        cp -r "$skill_dir" "$target"
    else
        # Symlink when installed locally (stays up to date with repo)
        ln -s "$skill_dir" "$target"
    fi
    echo "✅ Installed $skill_name"
done

# Check Python
if command -v python3 &>/dev/null; then
    echo "✅ Python 3 found: $(python3 --version)"
else
    echo "⚠️  Python 3 not found. /probe health stats will be unavailable."
fi

echo ""
echo "Installation complete! Available commands:"
echo "  /probe audit <path>         Full code audit"
echo "  /probe quick <path>         Top 5 issues"
echo "  /probe health <path>        Codebase vitals"
echo "  /probe solid <path>         SOLID principles check"
echo "  /probe security <path>      Security audit"
echo "  /probe smells <path>        Code smells detection"
echo "  /probe architecture <path>  Architecture analysis"
echo "  /probe patterns <path>      Design patterns analysis"
echo "  /probe performance <path>   Performance audit"
echo "  /probe errors <path>        Error handling audit"
echo "  /probe tests <path>         Test quality audit"
echo "  /probe framework <path>     Framework best practices"
