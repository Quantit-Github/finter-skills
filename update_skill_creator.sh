#!/bin/bash
set -e

# Update skill-creator from Anthropic's skills repository

echo "Updating skill-creator from Anthropic skills repository..."

# Create temp directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Clone Anthropic skills repo
echo "Cloning Anthropic skills repository..."
git clone --depth 1 https://github.com/anthropics/skills.git "$TEMP_DIR"

# Remove old skill-creator
echo "Removing old skill-creator..."
rm -rf skill-creator

# Copy new skill-creator
echo "Copying new skill-creator..."
cp -r "$TEMP_DIR/skill-creator" .

echo "✓ skill-creator updated successfully!"
echo ""
echo "Review the changes and commit:"
echo "  git add skill-creator"
echo "  git commit -m 'Update skill-creator from Anthropic'"
echo "  git push"
