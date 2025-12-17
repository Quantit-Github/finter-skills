# Finter Insight Skill

Generate novel research hypotheses by analyzing past research and avoiding duplicates.

## When to Use

Use this skill when generating new research topics for the Fund Manager.

## Workflow

```
1. Think of topic idea
2. Run search_research.py to check for similar past research
3. Based on results:
   - High similarity (>0.7): IMPROVE existing or pick different topic
   - Medium similarity (0.4-0.7): Review context, differentiate approach
   - Low similarity (<0.4): Proceed as novel topic
4. Generate insights.json with related_research field
```

## Scripts

### search_research.py - Check for Similar Research

**ALWAYS run this before finalizing a topic idea.**

**Run locally using Bash tool (NOT Jupyter):**

```bash
# Basic search
python .claude/skills/finter-insight/scripts/search_research.py "momentum strategy on kr_stock"

# Filter by universe
python .claude/skills/finter-insight/scripts/search_research.py "value investing" --universe us_stock

# Get more results
python .claude/skills/finter-insight/scripts/search_research.py "volatility" --top 10
```

**Output interpretation:**
- `similarity > 0.7`: Very similar - consider improving instead of new
- `similarity 0.4-0.7`: Related - review for context and differentiate
- `similarity < 0.4`: Novel - but still check the results for useful insights

## Output Format

When generating `insights.json`, include `related_research` for each hypothesis:

```json
{
  "completely_new": [
    {
      "topic": "Acoustic Damping in Price Discovery",
      "universe": "kr_stock",
      "hypothesis": "...",
      "related_research": {
        "checked": true,
        "similar_count": 2,
        "max_similarity": 0.45,
        "differentiation": "Prior work focused on volatility magnitude, this focuses on propagation speed"
      }
    }
  ]
}
```

## Key Rules

1. **ALWAYS search before generating** - No exceptions
2. **High similarity = pivot or improve** - Don't suggest duplicate research
3. **Include related_research field** - Show you checked
4. **Learn from failures** - If similar research failed, explain why yours is different
