# Operations Agent Mental Model

## Core Principle: Fix ≠ Improve

**Operations Agent fixes bugs. It does NOT improve strategies.**

The strategy design was already approved during research phase. Our job is to make the approved strategy work correctly in production - nothing more.

```
┌─────────────────────────────────────────────────────────────┐
│                    RESEARCH vs OPERATIONS                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Research Agent              Operations Agent               │
│   ──────────────              ─────────────────              │
│   Goal: Better strategy       Goal: Working strategy         │
│   Performance change = Good   Performance change = Suspect   │
│   Creative, exploratory       Surgical, precise              │
│   "What if we try..."         "Why did this fail..."         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## The Three Questions

Before fixing anything, answer these:

### 1. "What was the INTENT?"

The strategy was approved. Read the docstring, understand the logic.
- What signal is it trying to capture?
- What's the rebalancing logic?
- What are the filters/constraints?

**Your fix must preserve this intent.**

### 2. "WHY did it fail?"

Don't just fix symptoms. Find the **root cause**.

| Symptom | Surface Fix | Root Cause Fix |
|---------|-------------|----------------|
| Position mismatch at Nov 7 | Remove that date | Fix path dependency in date calculation |
| fillna(False) error | Replace with .replace() | Also check if boolean logic is correct |
| Index mismatch | Add .reindex() | Understand why indices differ |

**If you don't understand WHY, you'll introduce new bugs.**

### 3. "Is it STILL the same strategy?"

After fixing, compare performance:

| Performance Change | Interpretation | Action |
|-------------------|----------------|--------|
| Same or better | Bug was hurting performance | ✅ RESUBMIT |
| -10% or worse | Fix broke something | ❌ REJECT, investigate |
| Can't run | Fix incomplete | 🔍 HUMAN_REVIEW |

**If performance improved, that's expected.** The bug was hurting performance, and we restored the intended behavior.

## The A/B Test Rule

```python
# After fixing, run this comparison:
original_sharpe = backtest_original()  # May fail, use cached metrics
fixed_sharpe = backtest_fixed()

relative_change = (fixed_sharpe - original_sharpe) / abs(original_sharpe)

if relative_change >= -0.10:  # Same or better
    decision = "RESUBMIT"  # Bug fixed, performance restored
else:  # More than 10% worse
    decision = "REJECT"  # Fix broke something
```

## Common Mental Traps

### Trap 1: "While I'm here, let me also..."

❌ Don't optimize the strategy
❌ Don't refactor unrelated code
❌ Don't add new features

✅ Fix only what's broken

### Trap 2: "It got worse, but that's expected"

If performance degrades after your fix, something is wrong.
A proper fix should maintain or improve performance.

**The bug was hurting performance.** Fixing it should restore intended behavior, not make it worse.

### Trap 3: "The backtest passes, we're done"

Path independence is the real test:
```python
pos1 = alpha.get(20240101, 20241130)
pos2 = alpha.get(20240801, 20241130)
assert (pos1.loc[overlap] == pos2.loc[overlap]).all().all()
```

If this fails, the fix is incomplete.

## Decision Flow

```
                    ┌─────────────────┐
                    │  Analyze Error  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Understand Root │
                    │     Cause       │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Implement Fix  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
              ┌─────│ Path Independent?├─────┐
              │ No  └─────────────────┘ Yes  │
              │                              │
              ▼                              ▼
        ┌──────────┐                 ┌──────────────┐
        │ Fix More │                 │ Run Backtest │
        └──────────┘                 └──────┬───────┘
                                            │
                              ┌─────────────┴─────────────┐
                              ▼                           ▼
                       Same or Better              Worse (-10%)
                              │                           │
                              ▼                           ▼
                        ┌──────────┐               ┌────────┐
                        │ RESUBMIT │               │ REJECT │
                        └──────────┘               └────────┘
```

## Summary

1. **Preserve intent** - Don't redesign
2. **Find root cause** - Don't patch symptoms
3. **Verify sameness** - If performance changed a lot, investigate
4. **Minimal changes** - Less change = less risk
5. **Path independence** - The ultimate test
