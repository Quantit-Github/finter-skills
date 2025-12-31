#!/bin/bash
# Finter Skills Installer for Claude Code
# Usage: /path/to/finter-skills/install.sh

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Target is current working directory
TARGET_DIR="$(pwd)"
CLAUDE_DIR="$TARGET_DIR/.claude"
SKILLS_DIR="$CLAUDE_DIR/skills"

echo "Installing Finter skills to: $TARGET_DIR"
echo ""

# 1. Setup Python environment with uv
echo "Setting up Python environment..."
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

if [ ! -f "$TARGET_DIR/pyproject.toml" ]; then
    echo "  Initializing uv project..."
    uv init --no-readme
fi

echo "  Adding finter package..."
uv add finter

echo "  Syncing dependencies..."
uv sync

echo ""

# 2. Setup Claude skills
echo "Setting up Claude skills..."
mkdir -p "$CLAUDE_DIR"

if [ -d "$SKILLS_DIR" ]; then
    echo "  Warning: $SKILLS_DIR already exists. Updating..."
    rm -rf "$SKILLS_DIR"
fi

mkdir -p "$SKILLS_DIR"
for skill in finter-data finter-alpha finter-portfolio finter-portfolio-agent finter-insight finter-operations; do
    if [ -d "$SCRIPT_DIR/$skill" ]; then
        cp -r "$SCRIPT_DIR/$skill" "$SKILLS_DIR/"
        echo "  Copied: $skill"
    fi
done

echo ""

# 3. Copy CLAUDE.md
echo "Setting up CLAUDE.md..."
if [ -f "$TARGET_DIR/CLAUDE.md" ]; then
    echo "  Warning: CLAUDE.md exists. Backing up to CLAUDE.md.bak"
    mv "$TARGET_DIR/CLAUDE.md" "$TARGET_DIR/CLAUDE.md.bak"
fi
cp "$SCRIPT_DIR/CLAUDE.md" "$TARGET_DIR/CLAUDE.md"
echo "  Copied: CLAUDE.md"

echo ""
echo "Done! Now run 'claude' and start asking:"
echo ""
echo "   What PER data is available for Korean stocks?"
echo "   Create a momentum alpha for us_stock"
echo "   How do I load crypto data?"
echo ""
