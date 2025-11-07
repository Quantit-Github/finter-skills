# Finter Skills

This repository contains Claude Code skills for Finter MCP server.

## Skills

### finter-alpha

Alpha generation skill for Finter research platform.

### skill-creator

Skill creator tool from Anthropic's official skills repository. This helps create new Claude Code skills.

## Usage

This repository is meant to be used as a git submodule in the finter-mcp project.

```bash
git submodule add git@github.com:Quantit-Github/finter-skills.git submodule/finter-skills
```

## Updating skill-creator

The `skill-creator` tool is synced from [Anthropic's skills repository](https://github.com/anthropics/skills). To update it to the latest version:

```bash
./update_skill_creator.sh
```

This will:
1. Clone the latest Anthropic skills repository
2. Replace the local `skill-creator` directory with the latest version
3. You can then review changes and commit

After running the script, commit and push the changes:

```bash
git add skill-creator
git commit -m "Update skill-creator from Anthropic"
git push
```

Then update the submodule in finter-mcp:

```bash
cd /path/to/finter-mcp
git submodule update --remote submodule/finter-skills
git add submodule/finter-skills
git commit -m "Update finter-skills submodule"
```
