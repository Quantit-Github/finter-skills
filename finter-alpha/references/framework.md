# BaseAlpha Framework

Core concepts and rules for developing alpha strategies with the BaseAlpha framework.

## Overview

BaseAlpha provides a simple interface for alpha development. Implement a single method that returns position DataFrame.

## Core Structure

```python
from finter import BaseAlpha
from finter.data import ContentFactory
import pandas as pd
from helpers import get_start_date

class Alpha(BaseAlpha):
    """Your strategy description"""

    def get(self, start: int, end: int, **kwargs) -> pd.DataFrame:
        """
        Generate alpha positions for date range.

        Parameters
        ----------
        start : int
            Start date in YYYYMMDD format (e.g., 20240101)
        end : int
            End date in YYYYMMDD format (e.g., 20241231)
        **kwargs : dict
            Strategy parameters for customization

        Returns
        -------
        pd.DataFrame
            Position DataFrame with:
            - Index: Trading dates
            - Columns: Stock tickers (FINTER IDs)
            - Values: Position sizes (money allocated, row sum ≤ 1e8)
        """
        # Implementation here
        pass
```

## Required Rules

### 1. Class Name Must Be "Alpha"

```python
# ✓ Correct
class Alpha(BaseAlpha):
    pass

# ❌ Wrong - will not be recognized
class MyAlpha(BaseAlpha):
    pass
```

### 2. Method Signature

Must accept `start` and `end` parameters:

```python
def get(self, start: int, end: int, **kwargs) -> pd.DataFrame:
    pass
```

### 3. Always Shift Positions

**CRITICAL**: Use `.shift(1)` to avoid look-ahead bias:

```python
# ❌ Wrong - using same day's signal
def get(self, start, end):
    momentum = close.pct_change(20)
    positions = (momentum > 0).astype(float) * 1e8 / 10
    return positions.loc[str(start):str(end)]  # Look-ahead bias!

# ✓ Correct - using previous day's signal
def get(self, start, end):
    momentum = close.pct_change(20)
    positions = (momentum > 0).astype(float) * 1e8 / 10
    return positions.shift(1).loc[str(start):str(end)]
```

### 4. Load Data with Buffer

Always load extra historical data for calculations:

```python
from helpers import get_start_date

# ❌ Wrong - insufficient data
def get(self, start, end):
    cf = ContentFactory("kr_stock", start, end)  # Not enough history
    momentum = close.pct_change(60)  # Will have NaN at start

# ✓ Correct - load with proper buffer
def get(self, start, end):
    # Rule of thumb: buffer = 2x longest lookback + 250 days
    cf = ContentFactory("kr_stock", get_start_date(start, 60 * 2 + 250), end)
    momentum = close.pct_change(60)  # Has enough history
```

### 5. Respect Position Constraints

Row sum ≤ 1e8 (total AUM):

```python
# Validate your positions
row_sums = positions.sum(axis=1)
assert (row_sums <= 1e8).all(), f"Row sums exceed AUM: {row_sums.max()}"
```

## Position Value Semantics

**IMPORTANT**: Positions represent **absolute holding amounts**, not signals.

```python
# Position values:
# 1e8 = Hold 100% of AUM in that stock
# 5e7 = Hold 50% of AUM
# 0 = No position (cash or fully sold)
```

### Position Continuity

Positions are **持续的** - you must specify position size **every day**:

```python
# Example: Buy and hold Samsung, then partially sell
positions = pd.DataFrame({
    'SAMSUNG': [0,    1e8,  1e8,  1e8,  0.5e8, 0    ],
}, index=[         'D1', 'D2', 'D3', 'D4', 'D5', 'D6'])

# Interpretation:
# D1: No position (cash)
# D2: Buy Samsung with 100% AUM
# D3-D4: Hold Samsung at 100%
# D5: Reduce to 50% AUM (sell half)
# D6: Exit position completely (sell remaining)
```

**Key Concept**: This is NOT a signal (1/-1), it's the actual position size you want to hold.

## Return DataFrame Format

```python
# Example valid positions DataFrame
positions = pd.DataFrame({
    'STOCK_A': [5e7, 3e7, 2e7],
    'STOCK_B': [3e7, 5e7, 4e7],
    'STOCK_C': [2e7, 2e7, 4e7]
}, index=['2024-01-01', '2024-01-02', '2024-01-03'])

# Row sums: 1e8, 1e8, 1e8 ✓
```

**Requirements:**
- **Index**: Trading dates (datetime or string format)
- **Columns**: Stock tickers (FINTER IDs)
- **Values**: Position sizes in monetary units
- **Constraint**: Row sum ≤ 1e8 (100 million = total AUM)

## Data Loading

### Using ContentFactory

```python
from finter.data import ContentFactory
from helpers import get_start_date

# Initialize
cf = ContentFactory(
    universe="kr_stock",  # or "us_stock", "btcusdt_spot_binance"
    start=get_start_date(start, buffer=365),
    end=end
)

# Load data
close = cf.get_df("price_close")
volume = cf.get_df("volume")
pbr = cf.get_df("pbr")
```

### Common Data Items

```python
# Price data
close = cf.get_df("price_close")
open_price = cf.get_df("price_open")

# Volume and market cap
volume = cf.get_df("volume")
market_cap = cf.get_df("market_cap")

# Financial ratios
per = cf.get_df("per")   # Price-to-Earnings
pbr = cf.get_df("pbr")   # Price-to-Book
roe = cf.get_df("roe")   # Return on Equity
```

## Complete Minimal Example

```python
from finter import BaseAlpha
from finter.data import ContentFactory
import pandas as pd
from helpers import get_start_date


class Alpha(BaseAlpha):
    """Simple momentum strategy."""

    def get(self, start: int, end: int, period: int = 20) -> pd.DataFrame:
        # Load data with buffer
        cf = ContentFactory("kr_stock", get_start_date(start, period * 2 + 250), end)
        close = cf.get_df("price_close")

        # Calculate momentum
        momentum = close.pct_change(period)

        # Select positive momentum stocks
        selected = momentum > 0

        # Equal weight, 1e8 == 100% of AUM
        positions = selected.div(selected.sum(axis=1), axis=0) * 1e8

        # CRITICAL: Always shift positions to avoid look-ahead bias
        return positions.shift(1).loc[str(start):str(end)]
```

## Parameter Handling

```python
class Alpha(BaseAlpha):
    """Parameterized strategy."""

    def get(self, start: int, end: int, **kwargs) -> pd.DataFrame:
        # Extract with defaults
        momentum_period = kwargs.get("momentum_period", 20)
        top_percent = kwargs.get("top_percent", 0.9)

        # Implementation...
```

## See Also

- `../templates/` - Ready-to-use strategy templates
- `api_reference.md` - ContentFactory and data access methods
- `research_process.md` - Research methodology
- `troubleshooting.md` - Common mistakes and debugging
