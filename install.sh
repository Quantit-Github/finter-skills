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

# Create .claude directory
mkdir -p "$CLAUDE_DIR"

# Copy or link skills
if [ -d "$SKILLS_DIR" ]; then
    echo "Warning: $SKILLS_DIR already exists. Skipping skills copy."
else
    # Copy skill directories (exclude install.sh, README.md, etc.)
    mkdir -p "$SKILLS_DIR"
    for skill in finter-data finter-alpha finter-portfolio finter-portfolio-agent finter-insight finter-operations; do
        if [ -d "$SCRIPT_DIR/$skill" ]; then
            cp -r "$SCRIPT_DIR/$skill" "$SKILLS_DIR/"
            echo "  Copied: $skill"
        fi
    done
fi

# Copy CLAUDE.md
if [ -f "$TARGET_DIR/CLAUDE.md" ]; then
    echo "Warning: CLAUDE.md already exists. Skipping."
else
    cp "$SCRIPT_DIR/CLAUDE.md" "$TARGET_DIR/CLAUDE.md"
    echo "  Copied: CLAUDE.md"
fi

echo ""
echo "Done! Now you can run 'claude' and ask about Finter data."
echo ""
echo "Example questions:"
echo "  - finter에 한국주식 PER 데이터 있어?"
echo "  - us_stock universe에서 momentum alpha 만들어줘"
echo "  - crypto 데이터 어떻게 로드해?"
