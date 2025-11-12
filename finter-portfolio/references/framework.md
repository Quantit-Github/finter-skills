# BasePortfolio Framework

Core concepts and rules for developing portfolio strategies with the BasePortfolio framework.

## Overview

BasePortfolio provides a simple interface for portfolio development. Implement a single method that returns weight DataFrame combining multiple alpha strategies.

## Core Structure

```python
from finter import BasePortfolio
from finter.data import ContentFactory
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class Portfolio(BasePortfolio):
    """Your portfolio strategy description"""

    # List of alpha strategies to combine
    alpha_list = [
        "us.compustat.stock.user.alpha1",
        "us.compustat.stock.user.alpha2",
        "us.compustat.stock.user.alpha3"
    ]

    def weight(self, start: int, end: int) -> pd.DataFrame:
        """
        Calculate portfolio weights for date range.

        Parameters
        ----------
        start : int
            Start date in YYYYMMDD format (e.g., 20240101)
        end : int
            End date in YYYYMMDD format (e.g., 20241231)

        Returns
        -------
        pd.DataFrame
            Weight DataFrame with:
            - Index: Trading dates
            - Columns: Alpha strategy names (from alpha_list)
            - Values: Weights (row sum should be ~1.0)
        """
        # Implementation here
        pass
```

## Required Rules

### 1. Class Name Must Be "Portfolio"

```python
# ✓ Correct
class Portfolio(BasePortfolio):
    pass

# ❌ Wrong - will not be recognized
class MyPortfolio(BasePortfolio):
    pass
```

### 2. Define alpha_list

The `alpha_list` class attribute specifies which alpha strategies to combine:

```python
class Portfolio(BasePortfolio):
    alpha_list = [
        "us.compustat.stock.ywcho.alphathon2_yw_di",
        "us.compustat.stock.jyjung.insur_spxndx_roe",
        "us.compustat.stock.sypark.US_BDC_v4"
    ]
```

### 3. Method Signature

Must accept `start` and `end` parameters:

```python
def weight(self, start: int, end: int) -> pd.DataFrame:
    pass
```

### 4. Normalize Weights

**CRITICAL**: Weights must sum to ~1.0 per row (date):

```python
# ❌ Wrong - weights not normalized
def weight(self, start, end):
    inv_volatility = 1 / volatility_df
    return inv_volatility.shift(1).loc[str(start):str(end)]  # Sum != 1.0!

# ✓ Correct - weights sum to 1.0
def weight(self, start, end):
    inv_volatility = 1 / volatility_df
    weights = inv_volatility.div(inv_volatility.sum(axis=1), axis=0)
    weights = weights.fillna(0)  # Handle NaN
    return weights.shift(1).loc[str(start):str(end)]  # Sum = 1.0!
```

### 5. Apply Shift (Usually)

**CRITICAL**: Use `.shift(1)` to avoid look-ahead bias for dynamic weights:

```python
# ❌ Wrong - using same day's data for return-based weights
def weight(self, start, end):
    rolling_return = alpha_return_df.rolling(20).mean()
    return rolling_return.loc[str(start):str(end)]  # Look-ahead bias!

# ✓ Correct - using previous day's data
def weight(self, start, end):
    rolling_return = alpha_return_df.rolling(20).mean()
    return rolling_return.shift(1).loc[str(start):str(end)]

# NOTE: Static weights (equal weight, fixed allocation) don't need shift
```

**When to use shift(1)?**
1. **Alpha return based weights**: MUST shift(1) - Today's return → Tomorrow's weight
2. **Volatility/statistics based weights**: Recommended shift(1) - Already lagged but shift for safety
3. **Static/fixed weights**: No shift needed - Fixed allocations don't change

### 6. Load Data with Buffer

Always load extra historical data for rolling calculations:

```python
def calculate_previous_start_date(start_date: int, lookback_days: int) -> int:
    """Calculate start date for preloading data"""
    start = datetime.strptime(str(start_date), "%Y%m%d")
    previous_start = start - timedelta(days=lookback_days)
    return int(previous_start.strftime("%Y%m%d"))

# ❌ Wrong - insufficient data
def weight(self, start, end):
    alpha_return_df = self.alpha_pnl_df('us_stock', start, end)
    volatility = alpha_return_df.rolling(126).std()  # Will have NaN at start!

# ✓ Correct - load with proper buffer
def weight(self, start, end):
    # For 126-day rolling window, add 126+ days buffer
    preload_start = calculate_previous_start_date(start, 365)
    alpha_return_df = self.alpha_pnl_df('us_stock', preload_start, end)
    volatility = alpha_return_df.rolling(126).std()  # No NaN!
```

Rule of thumb: buffer = 2x longest lookback period

## Loading Alpha Returns

Use `self.alpha_pnl_df()` to load alpha return data:

```python
# Get alpha returns (1.0 = no change, 1.01 = 1% return)
alpha_return_df = self.alpha_pnl_df('us_stock', 19980101, 20241231)

# Result: DataFrame
# - Index: Trading dates
# - Columns: Alpha names from alpha_list
# - Values: Daily returns (1.0 = no change)
```

**CRITICAL**: Alpha returns use 1.0 as baseline (not 0.0):
- 1.0 = no change (0% return)
- 1.01 = +1% return
- 0.99 = -1% return

## Data Preprocessing

**Always clean consecutive 1's** (data artifacts):

```python
alpha_return_df = self.alpha_pnl_df('us_stock', preload_start, end)

# Handle consecutive 1's (no change sequences)
find_1 = (alpha_return_df == 1) & (alpha_return_df.shift(1) == 1)
alpha_return_df = alpha_return_df.mask(find_1, np.nan).ffill(limit=5)

# Now calculate rolling metrics
volatility_df = alpha_return_df.rolling(126).std()
```

See `preprocessing.md` for detailed guide.

## Weight DataFrame Format

The returned DataFrame must follow this format:

```python
# Example weight DataFrame:
#             alpha1  alpha2  alpha3
# 2024-01-01   0.33    0.33    0.34   ← sum = 1.0
# 2024-01-02   0.40    0.30    0.30   ← sum = 1.0
# 2024-01-03   0.35    0.35    0.30   ← sum = 1.0

# Requirements:
# 1. Index: Trading dates (datetime or int YYYYMMDD)
# 2. Columns: Alpha names (strings)
# 3. Values: Weights (floats, 0.0 to 1.0)
# 4. Row sum: ~1.0 (allow 0.99-1.01 for rounding)
# 5. No NaN values in final output
```

## Complete Minimal Example

Here's a complete working equal-weight portfolio:

```python
from finter import BasePortfolio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def calculate_previous_start_date(start_date: int, lookback_days: int) -> int:
    """Calculate start date for preloading data"""
    start = datetime.strptime(str(start_date), "%Y%m%d")
    previous_start = start - timedelta(days=lookback_days)
    return int(previous_start.strftime("%Y%m%d"))

class Portfolio(BasePortfolio):
    alpha_list = [
        "us.compustat.stock.ywcho.alphathon2_yw_di",
        "us.compustat.stock.jyjung.insur_spxndx_roe",
        "us.compustat.stock.sypark.US_BDC_v4"
    ]

    def weight(self, start: int, end: int) -> pd.DataFrame:
        # Load alpha returns with buffer
        preload_start = calculate_previous_start_date(start, 365)
        alpha_return_df = self.alpha_pnl_df('us_stock', preload_start, end)

        # Clean consecutive 1's
        find_1 = (alpha_return_df == 1) & (alpha_return_df.shift(1) == 1)
        alpha_return_df = alpha_return_df.mask(find_1, np.nan).ffill(limit=5)

        # Equal weight: 1/N
        n_alphas = len(self.alpha_list)
        weights = pd.DataFrame(
            1.0 / n_alphas,
            index=alpha_return_df.index,
            columns=alpha_return_df.columns
        )

        # No shift needed for static weights
        return weights.loc[str(start):str(end)]
```

## Validation Checklist

Before saving portfolio.py, verify:

1. **Class name**: `Portfolio` (not MyPortfolio)
2. **Method name**: `weight` (not get_weights)
3. **alpha_list**: Defined as class attribute
4. **Weight sum**: ~1.0 per row
   ```python
   weights.sum(axis=1).describe()  # mean should be ~1.0
   ```
5. **No NaN**: Final weights have no NaN
   ```python
   weights.isna().any().any()  # Should be False
   ```
6. **Shift applied**: For dynamic weights
   ```python
   return weights.shift(1).loc[str(start):str(end)]
   ```
7. **Date range**: Matches [start, end]
   ```python
   print(f"Date range: {weights.index[0]} to {weights.index[-1]}")
   ```

## Common Patterns

### Equal Weight
```python
n = len(self.alpha_list)
weights = pd.DataFrame(1.0/n, index=dates, columns=alpha_names)
return weights.loc[str(start):str(end)]  # No shift for static
```

### Risk Parity (Inverse Volatility)
```python
volatility_df = alpha_return_df.rolling(126).std()
inv_vol = 1 / volatility_df.replace(0, np.nan)
weights = inv_vol.div(inv_vol.sum(axis=1), axis=0).fillna(0)
return weights.shift(1).loc[str(start):str(end)]  # Shift!
```

### Return-based (Momentum)
```python
rolling_return = alpha_return_df.rolling(60).mean()
weights = rolling_return.div(rolling_return.sum(axis=1), axis=0)
return weights.shift(1).loc[str(start):str(end)]  # MUST shift!
```

## Next Steps

- **Learn algorithms**: Read `algorithms.md` for weight calculation methods
- **Data preprocessing**: Read `preprocessing.md` for data cleaning
- **See examples**: Check `templates/examples/` for complete code
- **Troubleshooting**: Read `troubleshooting.md` for common mistakes
