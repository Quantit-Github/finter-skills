# CLAUDE.md - Finter Skills Documentation Guide

This file provides guidance for creating and extending Claude Code skills in the finter-skills repository, based on the MECE (Mutually Exclusive, Collectively Exhaustive) and SSOT (Single Source of Truth) principles proven effective in finter-alpha.

## Overview

This repository contains Claude Code skills for the Finter platform. Each skill provides specialized capabilities through:

1. **Skill Documentation**: Workflow guides Claude reads during execution
2. **Reference Documentation**: Detailed API specs and conceptual guides
3. **Templates**: Ready-to-use code patterns and examples

## Documentation Architecture Principles

### MECE (Mutually Exclusive, Collectively Exhaustive)

Organize content so each topic lives in **exactly one place** and **all topics are covered**.

**Good Example** (finter-alpha structure):
```
finter-alpha/
├── references/framework.md      # WHAT: Concepts & rules
├── references/api_reference.md  # HOW: Function signatures
├── references/research_process.md  # WORKFLOW: Step-by-step process
└── references/troubleshooting.md   # DEBUG: Common mistakes
```

**Why it works**:
- `framework.md` = Concepts (NOT implementation details)
- `api_reference.md` = API specs (NOT workflow)
- `research_process.md` = Process (NOT API details)
- No overlap, full coverage

**Bad Example**:
```
references/
├── overview.md        # Contains: concepts + API + workflow (混재)
├── advanced.md        # Contains: some API + some debugging (중복)
└── guide.md           # Contains: workflow + concepts again (중복)
```

### SSOT (Single Source of Truth)

Each piece of information should be **defined once** and **referenced elsewhere**.

**Rule**: Define vs Reference vs Emphasize

```markdown
<!-- framework.md (Definition) -->
## Position Shifting
Always use `.shift(1)` to avoid look-ahead bias:
```python
return positions.shift(1)
```

<!-- SKILL.md (Emphasis) -->
**CRITICAL: Always shift positions**: `return positions.shift(1)`
See references/framework.md for details.

<!-- troubleshooting.md (Debug pattern) -->
❌ WRONG - Forgot to shift
See references/framework.md for the shift(1) rule.
```

**When duplication is acceptable**:
- Critical rules (safety): Repeat in SKILL.md, framework.md, troubleshooting.md
- Different contexts: Quick reference vs detailed explanation vs debugging

**When duplication is forbidden**:
- API signatures: Define ONCE in api_reference.md
- Data formats: Define ONCE in framework.md or universe_reference.md
- Complex procedures: Define ONCE in research_process.md

## Skill Documentation Structure

### Required Files

```
skill-name/
├── SKILL.md                    # Entry point (REQUIRED)
├── references/                 # Detailed documentation
│   ├── framework.md           # Core concepts
│   ├── api_reference.md       # API specifications
│   └── troubleshooting.md     # Common mistakes
├── templates/                  # Code examples
│   ├── examples/              # Complete implementations
│   └── patterns/              # Reusable building blocks
└── scripts/                    # Helper tools (optional)
```

### SKILL.md Structure

The entry point that Claude reads first. Must include:

```markdown
---
name: skill-name
description: When to use this skill (trigger phrases)
---

# Skill Title

Brief description

## ⚠️ CRITICAL RULES (MUST FOLLOW)

**Top 3-5 mistakes that break everything**
- Use code examples to show ❌ WRONG vs ✅ CORRECT

## 📋 Workflow

1. Step 1: What to do first
2. Step 2: ...
3. Step 3: ...

**⚠️ Key principle to remember**

## 🎯 First Steps

### Read the Framework First
**BEFORE coding, read `references/framework.md`**

### Find Your Template
**Review `templates/examples/` for similar patterns**

## 📚 Documentation

**Read these BEFORE coding:**
1. `references/framework.md` - Core concepts
2. `references/api_reference.md` - API usage

**Reference during coding:**
- `templates/examples/` - Complete examples

## ⚡ Quick Reference

Essential code snippets for copy-paste
```

**Design principles for SKILL.md**:
- **Scannable**: Use emojis, headers, clear sections
- **Critical first**: Most common mistakes at the top
- **Progressive disclosure**: Point to detailed docs, don't duplicate
- **Code-heavy**: Show more code, less prose

### references/ Directory

#### framework.md - Core Concepts

```markdown
# Framework Name

Core concepts and rules for using this framework.

## Overview
High-level introduction

## Core Structure
```python
# Minimal example showing structure
```

## Required Rules
### 1. Rule Name
Explanation + example

### 2. Another Rule
...

## Complete Minimal Example
```python
# Full working code
```

## See Also
- Links to other reference docs
```

**Responsibilities**:
- Define framework structure
- Explain constraints and requirements
- Provide conceptual understanding
- **NOT**: API details, workflow steps, debugging

#### api_reference.md - API Specifications

```markdown
# API Reference

Quick reference for functions and methods.

## ClassName

### Initialization
```python
# Constructor signature
```

### Key Methods

#### method_name(params)

Description

**Parameters:**
- param1: type - description

**Returns:** type - description

**Example:**
```python
# Usage example
```

## Common Operations

### Operation Category
```python
# Code patterns
```

## See Also
- Links to framework or examples
```

**Responsibilities**:
- Function signatures
- Parameter specifications
- Return value formats
- Common usage patterns
- **NOT**: Concepts, workflow, debugging

#### troubleshooting.md - Common Mistakes

```markdown
# Troubleshooting and Best Practices

Common mistakes, debugging strategies, and optimization tips.

## Common Mistakes

### 1. Most Critical Mistake

**Problem**: What goes wrong

```python
# ❌ WRONG - Why this fails
def bad_example():
    pass

# ✓ CORRECT - How to fix
def good_example():
    pass
```

**How to Detect:**
- Warning sign 1
- Warning sign 2

### 2. Another Common Mistake
...

## Performance Optimization

### 1. Optimization Category
```python
# ❌ SLOW
# ✓ FAST
```

## Debugging Strategies

### 1. How to Debug X
```python
# Debugging code
```

## See Also
- Links to framework
```

**Responsibilities**:
- Common error patterns
- Detection methods
- Performance tips
- **NOT**: Concepts, API specs

#### research_process.md (Optional)

For skills involving research/development workflow:

```markdown
# Research Guidelines

Systematic approach to [task].

## Process Overview

1. Step 1
2. Step 2
...

## 1. First Phase

### Questions to Answer
- Question 1?
- Question 2?

### Example Approach
```python
# Code example
```

## 2. Second Phase
...

## Final Checklist
- [ ] Checklist item 1
- [ ] Checklist item 2
```

**Responsibilities**:
- Step-by-step workflow
- Decision-making guidance
- Validation checklists
- **NOT**: API details, code reference

### templates/ Directory

```
templates/
├── examples/              # Complete end-to-end implementations
│   ├── basic_example.py
│   ├── advanced_example.py
│   └── special_case.py
│
└── patterns/              # Reusable building blocks
    ├── pattern_1.py
    └── pattern_2.py
```

**Examples** vs **Patterns**:
- **Examples**: Full working code users can copy-paste and modify
- **Patterns**: Functions/classes to import and combine

**Example structure**:
```python
"""
Brief description of what this example demonstrates.

Key features:
- Feature 1
- Feature 2

Usage:
    python templates/examples/basic_example.py
"""

from framework import BaseClass

# Helper function (if needed)
def helper():
    """Helper function description"""
    pass

# Main implementation
class Alpha(BaseClass):
    """
    Strategy description.

    This example shows:
    1. How to do X
    2. How to handle Y
    """

    def method(self, params):
        # Step 1: Descriptive comment
        step1_result = ...

        # Step 2: Another comment
        step2_result = ...

        return final_result

# Example usage
if __name__ == "__main__":
    # Demonstration code
    pass
```

## Creating a New Skill

### Step 1: Define Scope (MECE Check)

Ask yourself:
1. **What problem does this skill solve?** (one clear purpose)
2. **How is it different from existing skills?** (mutually exclusive)
3. **What topics must it cover?** (collectively exhaustive)

Example (finter-alpha vs finter-portfolio):
- finter-alpha: **Single** alpha strategy development
- finter-portfolio: **Multiple** alpha combination and optimization
- No overlap ✓

### Step 2: Create Directory Structure

```bash
mkdir -p skill-name/{references,templates/{examples,patterns},scripts}
touch skill-name/SKILL.md
touch skill-name/references/{framework.md,api_reference.md,troubleshooting.md}
```

### Step 3: Write SKILL.md (Entry Point)

Start with:
```markdown
---
name: skill-name
description: Use when user requests [trigger phrases]
---

# Skill Name

## ⚠️ CRITICAL RULES

Top 3 mistakes with ❌/✅ examples

## 📋 Workflow

1-2-3 steps

## 📚 Documentation

Point to references/
```

### Step 4: Separate Content by Responsibility

Use this decision tree:

```
Is it a concept/rule?
  → YES: references/framework.md

Is it an API specification?
  → YES: references/api_reference.md

Is it a workflow/process?
  → YES: references/research_process.md (or SKILL.md if short)

Is it a common mistake?
  → YES: references/troubleshooting.md

Is it working code?
  → YES: templates/examples/ or templates/patterns/
```

**Anti-pattern**: Mixing everything in one file
**Good pattern**: Each file has ONE clear purpose

### Step 5: Write References (SSOT)

For each reference document:

1. **Define** the concept once
2. Use cross-references:
   ```markdown
   For API details, see `api_reference.md`.
   For debugging, see `troubleshooting.md`.
   ```

### Step 6: Create Templates

Minimum 2-3 examples covering:
- Basic use case (80% of users start here)
- Common variations
- Edge cases (if applicable)

Each example should be **copy-pasteable** and **runnable**.

## Extending an Existing Skill

### Adding New Content

**Decision flowchart**:

```
Where does this content belong?

Is it a new concept?
  → Add section to references/framework.md
  → Update SKILL.md to reference it

Is it a new API?
  → Add to references/api_reference.md

Is it a new mistake pattern?
  → Add to references/troubleshooting.md

Is it a new example?
  → Add to templates/examples/
  → Update SKILL.md to list it

Is it a reusable pattern?
  → Add to templates/patterns/
```

### SSOT Check Before Adding

**Before writing new content, ask**:
1. Is this already documented somewhere? → Update existing, don't duplicate
2. Does this overlap with another file? → Choose ONE file, reference from others
3. Is this too detailed for SKILL.md? → Move to references/

**Example**:

```markdown
<!-- BAD: Duplicating API spec in SKILL.md -->
## Quick Reference
ContentFactory takes universe, start, end parameters...

<!-- GOOD: Reference only -->
## Quick Reference
**Essential imports:**
```python
from finter import BaseAlpha
```
For complete API, see `references/api_reference.md`.
```

### Updating Multiple Files

When adding a new feature that affects multiple files:

1. **Define** in appropriate reference (framework.md or api_reference.md)
2. **Mention** in SKILL.md with link
3. **Show example** in templates/examples/
4. **Add common mistakes** to troubleshooting.md (if applicable)

Example workflow for adding "new parameter validation":

```
1. references/framework.md: Define validation rules
2. SKILL.md: Add to Critical Rules with ❌/✅
3. templates/examples/: Update examples to show usage
4. troubleshooting.md: Add "Forgetting validation" to Common Mistakes
```

## MCP Documentation (for context)

Skills exist alongside MCP documentation (in parent project `finter-mcp/docs/finter/`). Understanding the relationship:

### MCP Docs vs Skill Docs

| MCP Docs (`docs/finter/`) | Skill Docs (`finter-skills/`) |
|--------------------------|-------------------------------|
| **Purpose**: Knowledge base for search | **Purpose**: Workflow guide for execution |
| **Consumer**: Hybrid search algorithm | **Consumer**: Claude during skill execution |
| **Format**: Structured + metadata | **Format**: Narrative + code examples |
| **Style**: What to do | **Style**: How to do it |
| **Metadata**: `_summaries.json` for search | **Metadata**: YAML frontmatter for activation |

### When to Update MCP vs Skill

**Update MCP docs** when:
- Adding new API endpoints or data types
- Changing framework requirements (e.g., new mandatory methods)
- User needs to **discover** this through search

**Update Skill docs** when:
- Adding workflow guidance or best practices
- Providing code examples and templates
- User needs to **execute** this step-by-step

**Update both** when:
- Adding a major new feature (define in MCP, guide in Skill)

## Best Practices Summary

### Do's ✓

- **One topic, one file**: Each file has single clear purpose
- **Define once**: SSOT for specifications
- **Cross-reference**: Link between docs instead of duplicating
- **Code examples**: Show more code, less prose
- **Progressive disclosure**: SKILL.md → references/ → templates/
- **Scannable**: Use headers, emojis, bullet points
- **Critical first**: Most important mistakes at the top

### Don'ts ❌

- **Don't mix concerns**: Concepts + API + workflow in one file
- **Don't duplicate specs**: Define API signatures only once
- **Don't hide critical info**: Safety rules must be visible
- **Don't guess structure**: Use finter-alpha as template
- **Don't skip examples**: Every concept needs code example
- **Don't write novels**: Keep prose minimal, code maximal

## Quality Checklist

Before committing new/updated skill documentation:

### Structure
- [ ] SKILL.md exists with YAML frontmatter
- [ ] references/ contains framework.md, api_reference.md, troubleshooting.md
- [ ] templates/ contains at least 2 working examples
- [ ] Each file has ONE clear responsibility

### MECE
- [ ] No topic overlap between files (mutually exclusive)
- [ ] All topics covered (collectively exhaustive)
- [ ] Each concept lives in exactly ONE file

### SSOT
- [ ] API specs defined once in api_reference.md
- [ ] Concepts defined once in framework.md
- [ ] Other files reference, not duplicate

### Usability
- [ ] Critical mistakes listed in SKILL.md with ❌/✅ examples
- [ ] All code examples are copy-pasteable
- [ ] Cross-references use relative paths
- [ ] Examples are runnable and tested

### Completeness
- [ ] SKILL.md explains WHEN to use this skill
- [ ] framework.md explains WHAT the concepts are
- [ ] api_reference.md explains HOW to call functions
- [ ] troubleshooting.md explains WHY things fail

## Examples from finter-alpha

### Good MECE Separation

```
✓ SKILL.md: Critical rules + workflow overview
✓ framework.md: BaseAlpha concepts and structure
✓ api_reference.md: ContentFactory, Simulator API
✓ troubleshooting.md: Common mistakes and fixes
✓ research_process.md: Step-by-step research workflow

Each has distinct responsibility with no overlap.
```

### Good SSOT Implementation

```
framework.md (line 69):
  "CRITICAL: Use .shift(1) to avoid look-ahead bias"
  [Full explanation with code example]

SKILL.md (line 16):
  "ALWAYS shift positions: return positions.shift(1)"
  [Quick reminder, points to framework.md]

troubleshooting.md (line 7):
  "❌ WRONG - Forgot to shift"
  [Debug pattern, points to framework.md]
```

Definition once (framework.md), referenced elsewhere.

### Good Template Structure

```
templates/
├── examples/
│   ├── technical_analysis.py     # Momentum/technical
│   ├── multi_factor.py            # Multiple factors
│   ├── stock_selection.py         # Specific stocks
│   └── crypto_bitcoin.py          # Special case
│
└── patterns/
    ├── equal_weight.py            # Weighting logic
    ├── top_k_selection.py         # Selection logic
    └── rolling_rebalance.py       # Rebalancing logic
```

Examples are complete, patterns are composable.

## Conclusion

The finter-alpha skill demonstrates effective documentation through:

1. **Clear separation of concerns** (MECE)
2. **Single source of truth** (SSOT)
3. **Progressive disclosure** (entry → concepts → details → examples)
4. **Code-first approach** (templates + patterns)

Follow these principles when creating new skills or extending existing ones. When in doubt, reference finter-alpha structure as the canonical example.
