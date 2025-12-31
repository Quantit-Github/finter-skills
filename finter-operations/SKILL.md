# Finter Operations - Alpha Error Recovery

Fix failed alpha submissions by analyzing errors, debugging code, and verifying fixes.

## MENTAL MODEL (READ FIRST!)

**Core Principle: Fix ≠ Improve**

See `references/mental_model.md` for detailed explanation.

```
┌─────────────────────────────────────────────────────────────┐
│   Research Agent: "Better strategy"  →  Performance change = Success  │
│   Operations Agent: "Same strategy"  →  Performance change = Suspect  │
└─────────────────────────────────────────────────────────────┘
```

**Three Questions Before Fixing:**
1. "What was the INTENT?" → Preserve it
2. "WHY did it fail?" → Find root cause
3. "Is it STILL the same strategy?" → A/B test

## WORKFLOW

```
1. ANALYZE ERROR     → Read error log, identify root cause
2. LOAD ORIGINAL     → Original code is in ./original/am.py
3. FIX CODE          → Implement fix, save as alpha.py
4. FINALIZE_FIX      → Run finalize_fix.py (validation + A/B + decision)
```

## CRITICAL: Original Code Location

The original (failed) code is extracted to `./original/`:
- `./original/am.py` - The alpha code

**DO NOT modify files in ./original/** - use as reference only.

## Step 1: ANALYZE ERROR

Common error types and their causes:

| Error Type | Symptom | Root Cause |
|------------|---------|------------|
| **Position Mismatch** | "diff at YYYY-MM-DD" | Calculations depend on start date |
| **Code Pattern** | "forbidden pattern" | Using `.fillna(False)`, `.resample()` |
| **Index Mismatch** | "index alignment" | Calendar/date index issues |

### Position Mismatch (Most Common)

```
Variation Position (start, end):
  (20250801, 20251110)
Original Position (start, end):
  (20251107, 20251110)
```

**Cause**: Monthly rebalance dates depend on start date.
**Fix**: Use deterministic date calculation from full data range.

## Step 2: LOAD AND UNDERSTAND

```python
# Read the original code
with open('./original/am.py', 'r') as f:
    original_code = f.read()
print(original_code)
```

Understand:
- What is the strategy trying to do?
- Where does the path-dependency come from?

## Step 3: FIX THE CODE

### Position Mismatch Fixes

**Problem**: `resample('ME')` on sliced data
```python
# BAD - depends on start date
for month_end in close.loc[str(start):str(end)].resample('ME').last().index:
```

**Fix**: Use full data for rebalance dates
```python
# GOOD - deterministic from full data
all_trading_days = close.index  # Full data including buffer
for i, day in enumerate(all_trading_days):
    if i < len(all_trading_days) - 1:
        next_day = all_trading_days[i + 1]
        if day.month != next_day.month:
            monthly_dates.append(day)
```

**Problem**: `shift(1).fillna(0)` creates path dependency
```python
# The first day's position is always 0, which differs by start date
return positions.shift(1).fillna(0)
```

**Fix**: Build shift logic into position construction
```python
# Use strictly-before rebalance dates (d < day, not d <= day)
applicable_dates = [d for d in sorted_rebal_dates if d < day]
# No shift needed - logic is built in
return positions
```

### Code Pattern Fixes

| Forbidden | Replacement |
|-----------|-------------|
| `.fillna(False)` | `.replace(np.nan, False)` |
| `.fillna(True)` | `.replace(np.nan, True)` |
| `.resample()` | Manual date iteration |
| `pct_change()` | `pct_change(fill_method=None)` |

## Step 4: SAVE FIXED CODE

After implementing the fix, save it to alpha.py:

```python
# Save the fixed alpha code (already done if you wrote to alpha.py)
# Make sure the file exists before running finalize_fix.py
```

## Step 5: RUN FINALIZE_FIX

Run the finalize script using **Bash tool** (NOT subprocess in Jupyter cell):

```bash
python .claude/skills/finter-operations/scripts/finalize_fix.py \
    --original ./original/am.py \
    --fixed ./alpha.py \
    --universe id_stock
```

**IMPORTANT**: Use Bash tool directly, just like finter-alpha's finalize.py. Do NOT use subprocess in a Jupyter code cell.

This script does:
1. **Validates** fixed code (class name, positions, path independence)
2. **Runs A/B backtest** (original vs fixed Sharpe comparison)
3. **Decides**: RESUBMIT, REJECT, or HUMAN_REVIEW
4. **Saves** fix_report.json with decision

### Output

```
============================================================
  FINALIZE FIX - A/B COMPARISON
============================================================
  Original: ./original/am.py
  Fixed: ./alpha.py
  Universe: id_stock

────────────────────────────────────────────────────────────
  1. Validate Fixed Code
────────────────────────────────────────────────────────────
  Class name: ✓ OK
  Positions: ✓ 1234 days, 500 stocks
  Path independence: ✓ OK

────────────────────────────────────────────────────────────
  2. A/B Backtest Comparison
────────────────────────────────────────────────────────────
  Running fixed backtest...
  Fixed: Sharpe=0.745
  Running original backtest...
  Original: Sharpe=0.738

────────────────────────────────────────────────────────────
  3. Decision
────────────────────────────────────────────────────────────
  ✅ RESUBMIT
  Reason: Performance similar (+0.9%), bug fixed

============================================================
  SUMMARY
============================================================
  Sharpe: 0.738 → 0.745 (+0.007)

  ✅ DECISION: RESUBMIT
  Performance similar (+0.9%), bug fixed
```

### Output Files

- `fix_report.json` - Decision and comparison metrics
- `fix_comparison.png` - A/B comparison chart (Original vs Fixed)

## FIX DECISION (A/B Test Result)

| Decision | Condition | Action |
|----------|-----------|--------|
| ✅ **RESUBMIT** | Validation passed, performance same or better | Same model name, overwrite |
| ❌ **REJECT** | Performance -10% worse | Don't submit, investigate |
| 🔍 **HUMAN_REVIEW** | Validation failed or can't determine | Needs human intervention |

### Why "Better" is still RESUBMIT

If performance improves after fix, the bug was hurting performance.
That's expected - we're restoring the strategy to its intended behavior.

## RULES

1. **PRESERVE INTENT**: Fix the bug, don't redesign the strategy
2. **MINIMAL CHANGES**: Only change what's necessary
3. **CLASS NAME**: Must be `Alpha` (not MyAlpha, FixedAlpha, etc.)
4. **DOCUMENT**: Explain what was wrong and how you fixed it

## ERROR REFERENCE

See `references/common_errors.md` for detailed error patterns and solutions.
See `references/mental_model.md` for the Operations Agent mental model.
