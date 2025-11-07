# BaseAlpha Framework Guide

The BaseAlpha framework provides a simple, straightforward approach to alpha strategy development. Use this for quick prototypes and simpler strategies.

## Core Concept

BaseAlpha requires implementing a single method: `get(start, end, **kwargs)` that returns position DataFrame.

## Class Structure

```python
from finter import BaseAlpha
from finter.data import ContentFactory
import pandas as pd

class Alpha(BaseAlpha):
    """Strategy description"""
    
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
            - Values: Position sizes (money allocated)
        """
        # Implementation here
        pass
```

## Method Signature Rules

1. **Must accept** `start` and `end` parameters
2. **Class name must be** `Alpha` (not CustomAlpha, MyStrategy, etc.)
3. **Must return** pandas DataFrame with proper format

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

## Position Value Interpretation

- `1e8` = 100% of AUM in that stock
- `5e7` = 50% of AUM
- `0` = No position
- Negative values = Short positions (if supported by universe)

## Critical Rules

### 1. Always Shift Positions

**CRITICAL**: Always use `.shift(1)` to avoid look-ahead bias:

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
    # CRITICAL: Always shift positions to avoid look-ahead bias
    return positions.shift(1).loc[str(start):str(end)]
```

### 2. Load Data with Buffer

Always load data with buffer period for calculations. Use the `get_start_date()` helper:

```python
def get_start_date(start: int, buffer: int = 365) -> int:
    """
    Get start date with buffer days

    Because we need to load data with buffer for calculations
    Rule of thumb: buffer = 2x longest lookback + 250 days
    """
    from datetime import datetime, timedelta

    return int(
        (datetime.strptime(str(start), "%Y%m%d") - timedelta(days=buffer)).strftime(
            "%Y%m%d"
        )
    )

# ❌ Wrong - insufficient data for calculations
def get(self, start, end):
    cf = ContentFactory("kr_stock", start, end)  # Not enough history!
    momentum = close.pct_change(60)  # Will have NaN at start

# ✓ Correct - load with proper buffer
def get(self, start, end):
    # Rule of thumb: buffer = 2x longest lookback + 250 days
    cf = ContentFactory("kr_stock", get_start_date(start, 60 * 2 + 250), end)
    momentum = close.pct_change(60)  # Has enough history
```

### 3. Respect Position Constraints

```python
# Validate your positions
def validate_positions(positions):
    row_sums = positions.sum(axis=1)
    assert (row_sums <= 1e8).all(), f"Row sums exceed AUM: {row_sums.max()}"
    assert not positions.isnull().any().any(), "Contains NaN values"
    print("✓ Position validation passed")
```

## Complete Implementation Example

```python
from finter import BaseAlpha
from finter.data import ContentFactory
import pandas as pd


def get_start_date(start: int, buffer: int = 365) -> int:
    """
    Get start date with buffer days

    Because we need to load data with buffer for calculations
    Rule of thumb: buffer = 2x longest lookback + 250 days
    """
    from datetime import datetime, timedelta

    return int(
        (datetime.strptime(str(start), "%Y%m%d") - timedelta(days=buffer)).strftime(
            "%Y%m%d"
        )
    )


class Alpha(BaseAlpha):
    """
    Simple momentum strategy with configurable parameters.

    Strategy Logic:
    1. Calculate price momentum over specified period
    2. Rank all stocks by momentum percentile
    3. Select top performers above threshold
    4. Apply rolling average for position stability
    5. Equal weight selected stocks
    """

    def get(self, start: int, end: int,
            momentum_period: int = 21,
            top_percent: float = 0.9,
            rolling_window: int = 5) -> pd.DataFrame:
        """
        Generate alpha positions for date range.

        Parameters
        ----------
        start : int
            Start date in YYYYMMDD format (e.g., 20240101)
        end : int
            End date in YYYYMMDD format (e.g., 20241231)
        momentum_period : int
            Lookback period for momentum calculation (default: 21)
        top_percent : float
            Percentile threshold for stock selection (0.9 = top 10%)
        rolling_window : int
            Smoothing window for position stability (default: 5)

        Returns
        -------
        pd.DataFrame
            Position DataFrame with:
            - Index: Trading dates
            - Columns: Stock tickers (FINTER IDs)
            - Values: Position sizes (money allocated, row sum ≤ 1e8)
        """
        # Load data with buffer for calculations
        # Rule of thumb: buffer = 2x longest lookback + 250 days
        buffer = max(momentum_period, rolling_window) * 2 + 250
        cf = ContentFactory("kr_stock", get_start_date(start, buffer), end)

        # Retrieve daily closing prices
        close_price = cf.get_df("price_close")

        # Calculate momentum
        momentum = close_price.pct_change(momentum_period)

        # Rank stocks by momentum (percentile)
        stock_rank = momentum.rank(pct=True, axis=1)

        # Select top stocks
        stock_top = stock_rank[stock_rank >= top_percent]

        # Apply rolling mean for smoothing
        stock_top_rolling = stock_top.rolling(rolling_window).mean()

        # Normalize to position sizes, 1e8 == 100% of AUM
        stock_ratio = stock_top_rolling.div(
            stock_top_rolling.sum(axis=1), axis=0
        )
        position = stock_ratio * 1e8

        # CRITICAL: Always shift positions to avoid look-ahead bias
        alpha = position.shift(1)

        # Return positions for requested date range
        return alpha.loc[str(start):str(end)]
```

## Common Patterns

### Equal Weight Portfolio

```python
def get(self, start, end):
    # Load data with buffer
    cf = ContentFactory("kr_stock", get_start_date(start), end)
    close = cf.get_df("price_close")

    # All stocks get equal weight, 1e8 == 100% of AUM
    n_stocks = close.shape[1]
    positions = close.notna().astype(float) * (1e8 / n_stocks)

    # CRITICAL: Always shift positions to avoid look-ahead bias
    return positions.shift(1).loc[str(start):str(end)]
```

### Top-K Selection

```python
def get(self, start, end, top_k=10):
    # Load data with buffer
    cf = ContentFactory("kr_stock", get_start_date(start, 20 * 2 + 250), end)
    close = cf.get_df("price_close")

    momentum = close.pct_change(20)

    # Select top K stocks per day
    top_k_mask = momentum.rank(axis=1, ascending=False) <= top_k

    # Equal weight selected stocks, 1e8 == 100% of AUM
    positions = top_k_mask.astype(float) * (1e8 / top_k)

    # CRITICAL: Always shift positions to avoid look-ahead bias
    return positions.shift(1).loc[str(start):str(end)]
```

### Factor Combination

```python
def get(self, start, end, mom_weight=0.5, val_weight=0.5):
    # Load data with buffer
    cf = ContentFactory("kr_stock", get_start_date(start, 20 * 2 + 250), end)

    close = cf.get_df("price_close")
    pbr = cf.get_df("pbr")

    # Rank each factor
    momentum_rank = close.pct_change(20).rank(axis=1, pct=True)
    value_rank = (1 / pbr).rank(axis=1, pct=True)

    # Combine with weights
    combined = momentum_rank * mom_weight + value_rank * val_weight

    # Select top 30% stocks
    selected = combined.rank(axis=1, pct=True) >= 0.7

    # Equal weight selected stocks, 1e8 == 100% of AUM
    positions = selected.div(selected.sum(axis=1), axis=0) * 1e8

    # CRITICAL: Always shift positions to avoid look-ahead bias
    return positions.shift(1).loc[str(start):str(end)]
```

## Parameter Optimization

Test multiple parameter combinations:

```python
import itertools
from finter.backtest import Simulator

# Define parameter grid
param_grid = {
    'momentum_period': [10, 21, 42, 63],
    'top_percent': [0.8, 0.9, 0.95]
}

# Test all combinations
results = []
for params in itertools.product(*param_grid.values()):
    param_dict = dict(zip(param_grid.keys(), params))
    
    # Run strategy
    alpha = Alpha()
    positions = alpha.get(20200101, 20241231, **param_dict)
    
    # Backtest
    simulator = Simulator(market_type="kr_stock")
    result = simulator.run(position=positions)
    
    results.append({
        'params': param_dict,
        'sharpe': result.statistics['Sharpe Ratio'],
        'total_return': result.statistics['Total Return (%)']
    })

# Find best parameters
best = max(results, key=lambda x: x['sharpe'])
print(f"Best params: {best['params']}")
print(f"Sharpe: {best['sharpe']:.2f}")
```

## See Also

- `alpha_examples.md` - More complete strategy examples
- `finter_api_reference.md` - ContentFactory and data access
- `best_practices.md` - Optimization tips and common mistakes
