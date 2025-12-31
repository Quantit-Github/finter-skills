#!/bin/bash
# Finter Skills Installer for Claude Code
# Usage: ./install.sh (run from finter-skills repo root)

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Target is workspace/ inside the repo
TARGET_DIR="$SCRIPT_DIR/workspace"
CLAUDE_DIR="$TARGET_DIR/.claude"
SKILLS_DIR="$CLAUDE_DIR/skills"

echo "Installing Finter skills to: $TARGET_DIR"
echo ""

# Create workspace directory
mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"

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

# Get API key
echo ""
echo -n "Enter your Finter API key: "
read -r FINTER_API_KEY

if [ -n "$FINTER_API_KEY" ]; then
    echo "FINTER_API_KEY=$FINTER_API_KEY" > "$TARGET_DIR/.env"
    echo "  Saved to .env"
else
    echo "  Skipped (no API key provided)"
fi

echo ""

# 2. Setup Claude skills (symlink to parent)
echo "Setting up Claude skills..."
mkdir -p "$CLAUDE_DIR"

if [ -L "$SKILLS_DIR" ] || [ -d "$SKILLS_DIR" ]; then
    echo "  Removing existing skills..."
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
    rm "$TARGET_DIR/CLAUDE.md"
fi
cp "$SCRIPT_DIR/CLAUDE.md" "$TARGET_DIR/CLAUDE.md"
echo "  Copied: CLAUDE.md"

echo ""
echo "Done! Starting Claude Code in workspace/..."
echo ""

claude
