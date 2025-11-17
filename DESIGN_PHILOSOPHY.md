# Design Philosophy: MECE + SSOT Approach

This document explains the design philosophy behind our skill documentation approach and how it differs from Anthropic's official skill-creator.

## TL;DR

**Anthropic's skill-creator**: General-purpose skill creation tool with automation scripts
**Our CLAUDE.md**: Documentation-heavy skill architecture guide with MECE + SSOT principles

Both are excellent for their respective use cases. We built CLAUDE.md because Finter skills are documentation-heavy research platform guides that require strong structural consistency.

---

## Core Design Principles

### 1. MECE (Mutually Exclusive, Collectively Exhaustive)

**Each topic lives in exactly one place, and all topics are covered.**

Example from finter-alpha:
```
✓ framework.md: BaseAlpha concepts and rules
✓ api_reference.md: Function signatures and parameters
✓ troubleshooting.md: Common mistakes and debugging
✓ research_process.md: Step-by-step research workflow

❌ NOT: Everything mixed in one giant SKILL.md
```

### 2. SSOT (Single Source of Truth)

**Define once, reference elsewhere.**

Example:
```
framework.md (DEFINE):
  "CRITICAL: Use .shift(1) to avoid look-ahead bias"
  [Full explanation with code]

SKILL.md (EMPHASIZE):
  "ALWAYS shift positions: return positions.shift(1)"
  See references/framework.md for details.

troubleshooting.md (DEBUG):
  "❌ WRONG - Forgot to shift"
  See references/framework.md for the shift(1) rule.
```

**Definition once, referenced everywhere.**

---

## Comparison with Anthropic's skill-creator

### Philosophy

| Aspect | Anthropic | Ours |
|--------|-----------|------|
| **Core Concept** | Progressive Disclosure (3-tier loading) | MECE + SSOT (structural consistency) |
| **Focus** | Token efficiency & automation | Content organization & quality |
| **Target** | All domains (PDF, BigQuery, brand guidelines) | Documentation-heavy platforms (Finter) |
| **Approach** | Process-driven (6-step workflow) | Architecture-driven (templates + decision trees) |

### Structure

| Feature | Anthropic | Ours |
|---------|-----------|------|
| **Automation** | ✅ init_skill.py, package_skill.py, validate.py | ❌ Manual (guided by templates) |
| **Structure Template** | ⚠️ Abstract (4 patterns to choose from) | ✅ Concrete (copy-paste ready) |
| **Extending Guide** | ❌ Step 6: "Iterate" (vague) | ✅ Decision flowchart (specific) |
| **Quality Control** | ⚠️ Mechanical (YAML validation only) | ✅ Manual checklist (MECE/SSOT/Usability) |
| **Examples** | ⚠️ Generic placeholders | ✅ Real-world (finter-alpha as canonical) |

### Progressive Disclosure (Anthropic's Strength)

```
1. Metadata (name + description)    ← Always in context (~100 words)
2. SKILL.md body                     ← When skill triggers (<5k words)
3. Bundled resources                 ← As needed (unlimited)
```

**Key insight**: Scripts can be executed without loading into context.

**Our implementation**: We adopted this but focused on organizing resources within tier 2-3 (references/ structure).

### Resource Classification

**Anthropic (by context usage)**:
```
scripts/     → Execute without reading (context-free)
references/  → Load into context (documentation)
assets/      → Use in output (templates, images)
```

**Ours (by responsibility)**:
```
references/
├── framework.md        # Concepts (WHAT)
├── api_reference.md    # Specifications (HOW)
├── troubleshooting.md  # Debugging (WHY FAIL)
└── research_process.md # Workflow (WHEN)

templates/
├── examples/           # Complete implementations
└── patterns/           # Reusable components
```

**Both valid**: Anthropic optimizes for token efficiency, we optimize for findability.

---

## When to Use Which Approach

### Use Anthropic's skill-creator When:

✅ **Script-heavy skills** (PDF manipulation, image processing)
- Most functionality is in executable scripts
- SKILL.md is just coordination logic

✅ **Asset-heavy skills** (brand guidelines, templates)
- Primary value is in assets/ directory
- Documentation is minimal

✅ **Quick utilities** (one-off company tools)
- Short lifecycle, simple structure
- Automation scripts save time

✅ **Diverse domains** (no pattern across skills)
- Each skill is completely different
- Generic template is appropriate

**Example**: PDF editor, PowerPoint template inserter, company logo manager

---

### Use Our CLAUDE.md Approach When:

✅ **Documentation-heavy skills** (research platforms, frameworks)
- Complex conceptual hierarchy
- Extensive API documentation
- Multiple workflow guides

✅ **Long-term projects** (evolving platforms)
- Continuous extension expected
- Multiple contributors
- Consistency critical

✅ **Related skill families** (alpha, portfolio, risk management)
- Shared structure across skills
- Common patterns and conventions
- MECE ensures no gaps/overlaps

✅ **Quality-critical domains** (quantitative research, compliance)
- Accuracy and consistency required
- SSOT prevents conflicting information

**Example**: finter-alpha, finter-portfolio, quant research platforms

---

## Real-World Impact: Finter Skills

### finter-alpha Structure

```
finter-alpha/
├── SKILL.md (Entry point)
│   ├── ⚠️ CRITICAL RULES (top 3-5 mistakes)
│   ├── 📋 Workflow (DATA FIRST)
│   └── ⚡ Quick Reference (copy-paste snippets)
│
├── references/ (MECE separation)
│   ├── framework.md (Concepts: BaseAlpha, position DataFrame)
│   ├── api_reference.md (API: ContentFactory, Simulator)
│   ├── troubleshooting.md (Debug: look-ahead bias, NaN handling)
│   └── research_process.md (Workflow: hypothesis → backtest → validation)
│
└── templates/ (Progressive complexity)
    ├── examples/ (Complete strategies)
    └── patterns/ (Reusable blocks)
```

**MECE ensures**:
- No overlap between framework.md and api_reference.md
- All topics covered (concepts, API, debugging, workflow)

**SSOT ensures**:
- "Look-ahead bias prevention" defined once in framework.md
- Other files reference it, not redefine

---

### finter-portfolio Structure

```
finter-portfolio/
├── references/
│   ├── framework.md (BasePortfolio concepts)
│   ├── algorithms.md (Equal Weight, Risk Parity, MVO) ← NEW!
│   ├── preprocessing.md (Consecutive 1's handling) ← NEW!
│   └── backtesting.md (get() auto-provided by BasePortfolio)
```

**Why algorithms.md is separate**:
- MECE: Algorithm selection (WHAT to choose) ≠ Framework concepts (HOW to implement)
- SSOT: Each algorithm's formula and code lives in one place

**Why preprocessing.md is separate**:
- MECE: Data cleaning ≠ Weight calculation ≠ Framework concepts
- Portfolio-specific concern (alpha strategies don't have consecutive 1's issue)

**Result**: Adding new algorithm = one section in algorithms.md, no other files touched.

---

## Combining Both Approaches

The two philosophies are complementary:

```
┌────────────────────────────────────┐
│ Progressive Disclosure             │ ← From Anthropic
│ (Token efficiency)                 │   Keep SKILL.md lean
│                                    │   Use references/ wisely
├────────────────────────────────────┤
│ MECE + SSOT                        │ ← Our contribution
│ (Structural consistency)           │   Organize references/
│                                    │   Prevent duplication
├────────────────────────────────────┤
│ Automation Tools                   │ ← From Anthropic
│ (init, validate, package)          │   Speed up creation
│                                    │   Enforce standards
└────────────────────────────────────┘
```

**Best of both worlds**:
1. Use init_skill.py to bootstrap
2. Apply MECE/SSOT when organizing references/
3. Use quality checklist before packaging
4. Package with package_skill.py

---

## Evolution Path

### Where Anthropic Excels

- ✅ Automation (scripts reduce manual work)
- ✅ Validation (mechanical checks prevent errors)
- ✅ Flexibility (works for any domain)

### Where We Improve

- ✅ Structure clarity (concrete templates, not abstract patterns)
- ✅ Extension guidance (decision trees for adding content)
- ✅ Quality standards (MECE/SSOT checklists)
- ✅ Domain optimization (tailored for documentation-heavy skills)

### Future Integration

Ideal next steps:
1. **Create init_finter_skill.py**: Generate finter-specific structure automatically
2. **Extend validate.py**: Add MECE/SSOT checks beyond YAML validation
3. **Template library**: Pre-built references/ files for common patterns
4. **Migration guide**: Convert Anthropic-style skills to MECE/SSOT structure

---

## Conclusion

**Anthropic's skill-creator is a general-purpose tool** for creating any skill quickly with automation.

**Our CLAUDE.md is a specialized guide** for creating documentation-heavy skills with structural rigor.

Both solve different problems:
- Anthropic: "How do I create a skill fast?"
- Ours: "How do I organize complex documentation well?"

For Finter's quantitative research platform, the documentation quality and consistency provided by MECE + SSOT principles are essential. The structural clarity enables:
- Multiple contributors maintaining consistency
- Easy extension without breaking existing structure
- Clear answers to "where does this content go?"
- No conflicting information across documents

The tradeoff is less automation and more manual curation, which is acceptable for our use case where documentation quality directly impacts research effectiveness.

---

## Related Reading

- **CLAUDE.md**: Practical guide for creating/extending Finter skills
- **finter-alpha/**: Canonical example demonstrating MECE + SSOT
- **finter-portfolio/**: Second example showing pattern consistency
- **Anthropic skill-creator**: Original skill creation framework
