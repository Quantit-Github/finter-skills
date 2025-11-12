# Data Preprocessing for Portfolio Construction

Guide to cleaning and preparing alpha return data before calculating portfolio weights.

## Overview

Alpha return data from `alpha_pnl_df()` often contains artifacts and requires preprocessing before use in weight calculations. This guide covers essential preprocessing steps.

---

## 1. Understanding Alpha Returns

### Data Format

```python
alpha_return_df = self.alpha_pnl_df('us_stock', 19980101, 20241231)

# Result: DataFrame
# - Index: Trading dates
# - Columns: Alpha strategy names
# - Values: Daily returns with 1.0 as baseline
```

### Return Convention

**CRITICAL**: Alpha returns use 1.0 as baseline (NOT 0.0):
- `1.0` = no change (0% return)
- `1.01` = +1% return
- `0.99` = -1% return
- `1.10` = +10% return

**Converting to standard returns** (if needed):
```python
# Convert to 0-baseline
standard_returns = alpha_return_df - 1.0

# Convert back to 1-baseline
alpha_returns = standard_returns + 1.0
```

---

## 2. Handling Consecutive 1's (CRITICAL)

### Problem

Alpha returns may have long sequences of 1.0 (no change) due to:
- Alpha not trading on certain days
- Data quality issues
- Position holding periods

These consecutive 1's create artifacts in rolling calculations:
- **Volatility underestimation**: Rolling std() is too low
- **Correlation distortion**: Artificial high correlation
- **Weight miscalculation**: Risk parity weights become wrong

### Solution

**Always clean consecutive 1's before calculating rolling metrics:**

```python
# Identify consecutive 1's
find_1 = (alpha_return_df == 1) & (alpha_return_df.shift(1) == 1)

# Replace with NaN, then forward-fill (keep first 5)
alpha_return_df = alpha_return_df.mask(find_1, np.nan).ffill(limit=5)
```

### How It Works

```python
# Original data:
# 2024-01-01    1.02
# 2024-01-02    1.00  ← First 1, keep
# 2024-01-03    1.00  ← Consecutive, replace with NaN
# 2024-01-04    1.00  ← Consecutive, replace with NaN
# 2024-01-05    1.00  ← Consecutive, replace with NaN
# 2024-01-06    1.01

# After mask:
# 2024-01-01    1.02
# 2024-01-02    1.00  ← Kept (first occurrence)
# 2024-01-03    NaN   ← Masked
# 2024-01-04    NaN   ← Masked
# 2024-01-05    NaN   ← Masked
# 2024-01-06    1.01

# After ffill(limit=5):
# 2024-01-01    1.02
# 2024-01-02    1.00
# 2024-01-03    1.00  ← Forward filled (count 1)
# 2024-01-04    1.00  ← Forward filled (count 2)
# 2024-01-05    1.00  ← Forward filled (count 3)
# 2024-01-06    1.01
```

**Why limit=5?**
- Allows short holding periods (5 days)
- Prevents long sequences from dominating
- Balance between keeping real data and removing artifacts

### Complete Example

```python
def weight(self, start: int, end: int) -> pd.DataFrame:
    # Load alpha returns
    preload_start = calculate_previous_start_date(start, 365)
    alpha_return_df = self.alpha_pnl_df('us_stock', preload_start, end)

    # CRITICAL: Clean consecutive 1's BEFORE any calculations
    find_1 = (alpha_return_df == 1) & (alpha_return_df.shift(1) == 1)
    alpha_return_df = alpha_return_df.mask(find_1, np.nan).ffill(limit=5)

    # Now calculate rolling metrics (volatility, correlation, etc.)
    volatility_df = alpha_return_df.rolling(126).std()
    # ... rest of weight calculation
```

---

## 3. Handling NaN Values

### Sources of NaN

- Alpha not available on certain dates
- Newly added alphas (no historical data)
- Data quality issues
- After preprocessing (masked consecutive 1's)

### Strategy 1: Forward Fill

Fill missing values with last known value:

```python
# Fill NaN with forward fill
alpha_return_df = alpha_return_df.ffill()

# Or with limit
alpha_return_df = alpha_return_df.ffill(limit=5)
```

**When to use**: Holding period logic (alpha continues previous position)

### Strategy 2: Fill with 1.0 (No Change)

Assume no change when data is missing:

```python
# Fill NaN with 1.0 (no change)
alpha_return_df = alpha_return_df.fillna(1.0)
```

**When to use**: Default assumption of flat position

### Strategy 3: Drop NaN

Remove dates with any NaN:

```python
# Drop rows with any NaN
alpha_return_df = alpha_return_df.dropna()
```

**When to use**: Require complete data for all alphas (intersection dates only)

### Recommended Approach

```python
# Step 1: Clean consecutive 1's
find_1 = (alpha_return_df == 1) & (alpha_return_df.shift(1) == 1)
alpha_return_df = alpha_return_df.mask(find_1, np.nan).ffill(limit=5)

# Step 2: Handle remaining NaN
# Option A: Forward fill short gaps
alpha_return_df = alpha_return_df.ffill(limit=10)

# Option B: Fill remaining with 1.0
alpha_return_df = alpha_return_df.fillna(1.0)
```

---

## 4. Handling Zero/Near-Zero Volatility

### Problem

Zero or very low volatility causes issues:
- **Division by zero**: In risk parity (1/volatility)
- **Extreme weights**: Near-zero volatility → huge weight
- **Unstable optimization**: MVO breaks with singular covariance

### Solution 1: Replace Zero with NaN

```python
# Replace zero volatility with NaN
volatility_df = alpha_return_df.rolling(126).std()
adjusted_volatility = volatility_df.replace(0, np.nan)

# Then inverse
inv_volatility = 1 / adjusted_volatility
```

### Solution 2: Add Epsilon

```python
# Add small constant to avoid division by zero
epsilon = 1e-6
inv_volatility = 1 / (volatility_df + epsilon)
```

### Solution 3: Floor Volatility

```python
# Set minimum volatility threshold
min_vol = 0.001  # 0.1%
volatility_df = volatility_df.clip(lower=min_vol)
inv_volatility = 1 / volatility_df
```

### Recommended Approach

```python
# Calculate volatility
volatility_df = alpha_return_df.rolling(126).std()

# Replace zero with NaN (cleanest approach)
adjusted_volatility = volatility_df.replace(0, np.nan)

# Calculate inverse
inv_volatility = 1 / adjusted_volatility

# Normalize (NaN will be handled here)
weights = inv_volatility.div(inv_volatility.sum(axis=1), axis=0)

# Fill any remaining NaN with 0 or equal weight
weights = weights.fillna(0)
# or
# weights = weights.fillna(1.0 / len(self.alpha_list))
```

---

## 5. Date Range and Buffer

### Problem

Rolling calculations need historical data before the start date:
- 126-day volatility needs 126 days of history
- 252-day correlation needs 252 days of history
- Without buffer → NaN at beginning of period

### Solution: Preload with Buffer

```python
def calculate_previous_start_date(start_date: int, lookback_days: int) -> int:
    """Calculate start date for preloading data based on lookback period"""
    start = datetime.strptime(str(start_date), "%Y%m%d")
    previous_start = start - timedelta(days=lookback_days)
    return int(previous_start.strftime("%Y%m%d"))

def weight(self, start: int, end: int) -> pd.DataFrame:
    # Calculate buffer (2x longest lookback + 250 safety margin)
    lookback_days = 126  # 6-month volatility
    buffer_days = lookback_days * 2 + 250

    # Preload with buffer
    preload_start = calculate_previous_start_date(start, buffer_days)
    alpha_return_df = self.alpha_pnl_df('us_stock', preload_start, end)

    # Calculate rolling metrics
    volatility_df = alpha_return_df.rolling(lookback_days).std()

    # ... calculate weights ...

    # Return only requested date range
    return weights.loc[str(start):str(end)]
```

### Buffer Rules of Thumb

| Calculation | Lookback | Recommended Buffer |
|------------|----------|-------------------|
| 60-day metrics | 60 | 120 + 250 = 370 |
| 126-day metrics | 126 | 252 + 250 = 502 |
| 252-day metrics | 252 | 504 + 250 = 754 |

**Simple rule**: `buffer = 2 * lookback + 250`

---

## 6. Weight Normalization

### Problem

Weights must sum to 1.0 per row (date) for proper portfolio construction.

### Solution

```python
# Calculate raw weights (e.g., inverse volatility)
inv_volatility = 1 / adjusted_volatility

# Normalize to sum to 1.0 per row
weights = inv_volatility.div(inv_volatility.sum(axis=1), axis=0)

# Handle NaN (row sum was zero or NaN)
weights = weights.fillna(0)
# or equal weight:
# weights = weights.fillna(1.0 / len(self.alpha_list))
```

### Validation

Always validate weight normalization:

```python
# Check weight sum
weight_sum = weights.sum(axis=1)
print(f"Weight sum stats:\n{weight_sum.describe()}")

# Acceptable range: 0.99 to 1.01 (allow for rounding errors)
assert (weight_sum >= 0.99).all() and (weight_sum <= 1.01).all(), "Weights don't sum to 1!"
```

---

## 7. Complete Preprocessing Template

Here's a complete preprocessing workflow:

```python
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

def calculate_previous_start_date(start_date: int, lookback_days: int) -> int:
    """Calculate start date for preloading data"""
    start = datetime.strptime(str(start_date), "%Y%m%d")
    previous_start = start - timedelta(days=lookback_days)
    return int(previous_start.strftime("%Y%m%d"))

def weight(self, start: int, end: int) -> pd.DataFrame:
    # Step 1: Calculate buffer
    lookback_days = 126  # Adjust based on your metrics
    buffer_days = lookback_days * 2 + 250

    # Step 2: Load data with buffer
    preload_start = calculate_previous_start_date(start, buffer_days)
    alpha_return_df = self.alpha_pnl_df('us_stock', preload_start, end)

    # Step 3: Clean consecutive 1's (CRITICAL!)
    find_1 = (alpha_return_df == 1) & (alpha_return_df.shift(1) == 1)
    alpha_return_df = alpha_return_df.mask(find_1, np.nan).ffill(limit=5)

    # Step 4: Handle remaining NaN
    alpha_return_df = alpha_return_df.ffill(limit=10).fillna(1.0)

    # Step 5: Calculate rolling metrics
    volatility_df = alpha_return_df.rolling(
        window=lookback_days,
        min_periods=lookback_days
    ).std()

    # Step 6: Handle zero volatility
    adjusted_volatility = volatility_df.replace(0, np.nan)

    # Step 7: Calculate raw weights
    inv_volatility = 1 / adjusted_volatility

    # Step 8: Normalize weights
    weights = inv_volatility.div(inv_volatility.sum(axis=1), axis=0)
    weights = weights.fillna(0)

    # Step 9: Apply shift (if needed) and slice date range
    return weights.shift(1).loc[str(start):str(end)]
```

---

## 8. Validation Checklist

Before finalizing your portfolio, validate preprocessing:

```python
# Check 1: No NaN in final weights
assert not weights.isna().any().any(), "NaN found in weights!"

# Check 2: Weights sum to ~1.0
weight_sum = weights.sum(axis=1)
assert (weight_sum >= 0.99).all() and (weight_sum <= 1.01).all(), "Weights don't sum to 1!"

# Check 3: Date range correct
assert weights.index[0] >= start, f"Weights start before {start}"
assert weights.index[-1] <= end, f"Weights end after {end}"

# Check 4: Reasonable weight range
assert weights.min().min() >= -0.01, "Negative weights found!"  # Allow small negative due to rounding
assert weights.max().max() <= 1.01, "Weights exceed 100%!"

print("✓ All preprocessing validation checks passed!")
```

---

## Next Steps

- **Learn algorithms**: Read `algorithms.md` for weight calculation methods
- **See examples**: Check `templates/examples/` for complete implementations
- **Troubleshooting**: Read `troubleshooting.md` for common issues
