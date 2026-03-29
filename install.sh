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
    echo "Cloning codeprobe-claude..."
    git clone --quiet https://github.com/nishilbhave/codeprobe-claude.git "$TMPDIR/codeprobe-claude"
    SCRIPT_DIR="$TMPDIR/codeprobe-claude"
    trap "rm -rf '$TMPDIR'" EXIT
fi

echo "Installing codeprobe-claude..."

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
    echo "⚠️  Python 3 not found. /codeprobe health stats will be unavailable."
fi

echo ""
echo "Installation complete! Available commands:"
echo "  /codeprobe audit <path>         Full code audit"
echo "  /codeprobe quick <path>         Top 5 issues"
echo "  /codeprobe health <path>        Codebase vitals"
echo "  /codeprobe solid <path>         SOLID principles check"
echo "  /codeprobe security <path>      Security audit"
echo "  /codeprobe smells <path>        Code smells detection"
echo "  /codeprobe architecture <path>  Architecture analysis"
echo "  /codeprobe patterns <path>      Design patterns analysis"
echo "  /codeprobe performance <path>   Performance audit"
echo "  /codeprobe errors <path>        Error handling audit"
echo "  /codeprobe tests <path>         Test quality audit"
echo "  /codeprobe framework <path>     Framework best practices"
