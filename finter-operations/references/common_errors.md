# Common Alpha Submission Errors

## 1. Position Mismatch (Start Dependency)

### Error Message
```
Variation Position (start, end):
  (20250801, 20251110)
Original Position (start, end):
  (20251107, 20251110)

diff at 2025-11-07 00:00:00, amount is 100000000.0
```

### Root Causes

#### 1.1 resample() on Sliced Data
```python
# BAD - month-end dates depend on start
for month_end in close.loc[str(start):str(end)].resample('ME').last().index:
    ...
```

**Fix**: Calculate month-ends from FULL data (including buffer)
```python
# GOOD - deterministic month-ends
all_trading_days = close.index  # Full data
monthly_dates = []
for i, day in enumerate(all_trading_days[:-1]):
    if day.month != all_trading_days[i + 1].month:
        monthly_dates.append(day)
```

#### 1.2 shift(1).fillna(0) Edge Case
```python
# The first day is always 0 after shift
return positions.shift(1).fillna(0)
```

When start=2025-11-07:
- Day 0 (2025-11-07): 0 (from fillna)
- Day 1 (2025-11-08): Real position

When start=2025-08-01:
- Day 0 (2025-08-01): 0 (from fillna)
- Day N (2025-11-07): Inherited position (NOT 0!)

**Fix**: Build shift logic into position construction
```python
# Use rebalance dates STRICTLY BEFORE position date
applicable = [d for d in rebal_dates if d < day]  # Note: < not <=
if applicable:
    positions.loc[day, selected] = weight
# No shift needed!
return positions
```

#### 1.3 Cumulative Operations
```python
# BAD - cumsum depends on start
signals = returns.cumsum()
```

**Fix**: Use rolling windows or fixed anchors
```python
# GOOD - fixed window
signals = returns.rolling(60).sum()
```

### Path Independence Test
```python
pos1 = alpha.get(20240101, 20241130)
pos2 = alpha.get(20240801, 20241130)

# Compare overlap
overlap = pos1.loc['20240801':].index
diff = (pos1.loc[overlap] - pos2.loc[overlap]).abs().sum().sum()
assert diff < 1e-6, f"Path dependent! diff={diff}"
```

---

## 2. Code Pattern Errors

### Error Message
```
Forbidden pattern detected: fillna(False)
```

### Forbidden Patterns

| Pattern | Issue | Replacement |
|---------|-------|-------------|
| `.fillna(False)` | Type coercion | `.replace(np.nan, False)` |
| `.fillna(True)` | Type coercion | `.replace(np.nan, True)` |
| `.fillna(0)` | Sometimes OK | `.replace(np.nan, 0)` if bool context |
| `pct_change()` | Deprecated fill | `pct_change(fill_method=None)` |
| `.resample()` | Often path-dependent | Manual iteration |

### Code Fix Script
```python
import re

def fix_code_patterns(code: str) -> str:
    # Fix fillna patterns
    code = re.sub(r'\.fillna\(False\)', '.replace(np.nan, False)', code)
    code = re.sub(r'\.fillna\(True\)', '.replace(np.nan, True)', code)

    # Fix pct_change
    code = re.sub(r'\.pct_change\(\)', '.pct_change(fill_method=None)', code)
    code = re.sub(
        r'\.pct_change\((\d+)\)',
        r'.pct_change(\1, fill_method=None)',
        code
    )

    return code
```

---

## 3. Index Mismatch

### Error Message
```
Index alignment error: expected 252 trading days, got 250
```

### Root Causes

#### 3.1 Missing Calendar Alignment
```python
# BAD - assumes indices match
result = df1 * df2  # May have different indices
```

**Fix**: Explicit reindex
```python
# GOOD - align to common index
common_idx = df1.index.intersection(df2.index)
result = df1.loc[common_idx] * df2.loc[common_idx]
```

#### 3.2 Holiday Handling
```python
# BAD - assumes all dates exist
positions.loc['2024-01-01'] = weight  # May be holiday
```

**Fix**: Use trading calendar
```python
# GOOD - only use valid trading days
trading_days = close.index
for day in trading_days:
    positions.loc[day] = weight
```

---

## 4. Data Type Errors

### Error Message
```
TypeError: unsupported operand type(s) for *: 'float' and 'bool'
```

### Root Cause
Mixing boolean and numeric operations after fillna(False).

**Fix**: Explicit type conversion
```python
# Convert bool to int before arithmetic
mask = (condition).astype(int)
result = values * mask
```

---

## Quick Diagnosis Checklist

| Symptom | Likely Cause | Check |
|---------|--------------|-------|
| "diff at date X" | Path dependency | Is there resample()? cumsum()? |
| "forbidden pattern" | Code pattern | Search for fillna, pct_change |
| "index alignment" | Calendar issue | Check .reindex(), date handling |
| Random position flips | Bool/float mix | Check fillna(False) usage |
