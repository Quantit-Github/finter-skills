# Troubleshooting and Best Practices

Common mistakes, debugging strategies, and performance optimization tips.

## Common Mistakes

### 1. Look-Ahead Bias (Most Critical!)

**Problem**: Using future information to make past decisions.

```python
# ❌ WRONG - This is the #1 mistake!
def get(self, start, end):
    from helpers import get_start_date
    cf = ContentFactory("kr_stock", get_start_date(start, 20 * 2 + 250), end)
    close = cf.get_df("price_close")
    momentum = close.pct_change(20)
    # Forgot to shift - using today's momentum to trade today!
    return momentum.loc[str(start):str(end)]

# ✓ CORRECT - Always shift positions
def get(self, start, end):
    from helpers import get_start_date
    cf = ContentFactory("kr_stock", get_start_date(start, 20 * 2 + 250), end)
    close = cf.get_df("price_close")
    momentum = close.pct_change(20)
    # CRITICAL: Always shift positions to avoid look-ahead bias
    return momentum.shift(1).loc[str(start):str(end)]
```

**How to Detect:**
- Unrealistically high Sharpe ratios (> 5)
- Perfect timing of market moves
- Strategy performance drops dramatically in live trading

### 2. Path Independence Violation (Start-End Dependency)

**Problem**: Position values change depending on `start`/`end` parameters.

```python
# ❌ WRONG - Using full-period statistics
def get(self, start, end):
    close = cf.get_df("price_close")
    normalized = (close - close.mean()) / close.std()  # Uses ALL data including future!
    return (normalized > 0).shift(1) * 1e8

# ✓ CORRECT - Using expanding (only past data)
def get(self, start, end):
    close = cf.get_df("price_close")
    normalized = (close - close.expanding().mean()) / close.expanding().std()
    return (normalized > 0).shift(1) * 1e8
```

**Why it matters**: `get(20200101, 20201231)` and `get(20200101, 20210630)` must return **identical values for overlapping dates**. If not, `end` parameter is leaking into past calculations.

**Common violations**: `.mean()`, `.std()`, `.rank()` on full DataFrame → use `.expanding()` versions instead.

**Verify with script**:
```bash
python scripts/alpha_validator.py --code alpha.py --universe kr_stock
```


### 3. Position Constraint Violations

**Problem**: Row sums exceed 1e8 (total AUM).

```python
# ❌ WRONG - Positions can exceed total capital
def get(self, start, end):
    signals = momentum > 0
    positions = signals * 1e8  # Each position is 100%!
    return positions.shift(1).loc[str(start):str(end)]

# ✓ CORRECT - Normalize to total capital
def get(self, start, end):
    from helpers import get_start_date
    cf = ContentFactory("kr_stock", get_start_date(start, 20 * 2 + 250), end)
    close = cf.get_df("price_close")
    momentum = close.pct_change(20)

    signals = momentum > 0
    # Divide by number of positions, 1e8 == 100% of AUM
    positions = signals.div(signals.sum(axis=1), axis=0) * 1e8
    return positions.shift(1).loc[str(start):str(end)]
```

**Validation:**
```python
from helpers import validate_positions

# Check position constraints
validate_positions(positions)
```

### 4. Insufficient Data Buffer

**Problem**: Not loading enough historical data for calculations.

```python
from helpers import get_start_date

# ❌ WRONG - Not enough data for 100-day calculation
def get(self, start, end):
    cf = ContentFactory("kr_stock", start, end)
    close = cf.get_df("price_close")
    momentum = close.pct_change(100)  # First 100 days will be NaN!

# ✓ CORRECT - Load with proper buffer using get_start_date()
def get(self, start, end):
    # Rule of thumb: buffer = 2x longest lookback + 250 days
    cf = ContentFactory("kr_stock", get_start_date(start, 100 * 2 + 250), end)
    close = cf.get_df("price_close")
    momentum = close.pct_change(100)
    return momentum.shift(1).loc[str(start):str(end)]
```

### 5. NaN Handling

**Problem**: NaN values propagate through calculations.

```python
# ❌ WRONG - NaN values create empty positions
def get(self, start, end):
    from helpers import get_start_date
    cf = ContentFactory("kr_stock", get_start_date(start, 20 * 2 + 250), end)
    close = cf.get_df("price_close")
    momentum = close.pct_change(20)
    # If any NaN, entire row becomes NaN after division
    positions = momentum.div(momentum.sum(axis=1), axis=0) * 1e8

# ✓ CORRECT - Handle NaN explicitly
def get(self, start, end):
    from helpers import get_start_date
    cf = ContentFactory("kr_stock", get_start_date(start, 20 * 2 + 250), end)
    close = cf.get_df("price_close")
    momentum = close.pct_change(20)

    # Fill NaN with 0 or drop
    momentum_clean = momentum.fillna(0)

    # Equal weight selected stocks, 1e8 == 100% of AUM
    positions = momentum_clean.div(momentum_clean.sum(axis=1), axis=0) * 1e8
    return positions.shift(1).loc[str(start):str(end)]
```

### 6. Incorrect Class Name

**Problem**: Class must be named exactly `Alpha`.

```python
# ❌ WRONG - Will not be recognized
class MomentumStrategy(BaseAlpha):
    pass

class MyAlpha(BaseAlpha):
    pass

# ✓ CORRECT - Must be exactly "Alpha"
class Alpha(BaseAlpha):
    pass
```

### 7. Incorrect Symbol Usage

**Problem**: `Symbol` requires instantiation before use.

```python
# ❌ WRONG - Symbol is not a class method
from finter.data import Symbol

result = Symbol.search("palantir", universe="us_stock")  # Will fail!

# ✓ CORRECT - Must create instance first
from finter.data import Symbol

symbol = Symbol("us_stock")  # Create instance
result = symbol.search("palantir")  # Then search
finter_id = result.index[0]
```

**Why this happens**: `Symbol` is a class that needs to be initialized with a universe before searching.

### 8. Trading Days Index Mismatch

**Problem**: Position index contains non-trading days (weekends, holidays).

```python
# ❌ WRONG - Using calendar dates
def get(self, start, end):
    dates = pd.date_range(str(start), str(end), freq='D')  # Includes weekends!
    positions = pd.DataFrame(index=dates, ...)
    return positions

# ❌ WRONG - Resample without filtering
def get(self, start, end):
    monthly = close.resample('M').last()
    positions = monthly.reindex(close.index, method='ffill')  # May have gaps

# ✓ CORRECT - Use ContentFactory.trading_days
def get(self, start, end):
    cf = ContentFactory(universe, start, end)
    positions = positions.reindex(cf.trading_days)  # Align to trading days
    return positions.shift(1).loc[str(start):str(end)]
```

**Verify with script**:
```bash
python scripts/alpha_validator.py --code alpha.py --universe kr_stock --verbose
```

## Performance Optimization

### 1. Vectorization Over Loops

```python
# ❌ SLOW - Row-by-row iteration
def get(self, start, end):
    from helpers import get_start_date
    cf = ContentFactory("kr_stock", get_start_date(start, 20 * 2 + 250), end)
    close = cf.get_df("price_close")

    results = []
    for date in close.index:
        row = close.loc[date]
        momentum = row.pct_change()
        results.append(momentum)
    return pd.DataFrame(results)

# ✓ FAST - Vectorized operations (10-100x faster)
def get(self, start, end):
    from helpers import get_start_date
    cf = ContentFactory("kr_stock", get_start_date(start, 20 * 2 + 250), end)
    close = cf.get_df("price_close")

    # Operates on entire DataFrame at once
    momentum = close.pct_change(20)
    return momentum.shift(1).loc[str(start):str(end)]
```

### 2. Avoid Redundant Calculations

```python
# ❌ INEFFICIENT - Calculating same thing multiple times
def get(self, start, end):
    from helpers import get_start_date
    cf = ContentFactory("kr_stock", get_start_date(start), end)
    close = cf.get_df("price_close")

    momentum = close.pct_change(20)
    momentum_rank = momentum.rank(pct=True, axis=1)

    # Recalculating momentum again!
    signals = close.pct_change(20) > 0

# ✓ EFFICIENT - Calculate once, reuse
def get(self, start, end):
    from helpers import get_start_date
    cf = ContentFactory("kr_stock", get_start_date(start), end)
    close = cf.get_df("price_close")

    momentum = close.pct_change(20)  # Calculate once
    momentum_rank = momentum.rank(pct=True, axis=1)
    signals = momentum > 0  # Reuse calculation
```

### 3. Smart Data Loading

```python
# ❌ INEFFICIENT - Loading unnecessary data
def get(self, start, end):
    from helpers import get_start_date
    cf = ContentFactory("kr_stock", get_start_date(start), end)

    # Loading all these but only using close!
    open_price = cf.get_df("price_open")
    high = cf.get_df("price_high")
    low = cf.get_df("price_low")
    close = cf.get_df("price_close")
    # (Loading unnecessary data slows down strategy)

    momentum = close.pct_change(20)

# ✓ EFFICIENT - Load only what you need
def get(self, start, end):
    from helpers import get_start_date
    cf = ContentFactory("kr_stock", get_start_date(start), end)
    close = cf.get_df("price_close")  # Only necessary data
    momentum = close.pct_change(20)
```

## Debugging Strategies

### 1. Inspect Intermediate Results

```python
def get(self, start, end):
    from helpers import get_start_date
    cf = ContentFactory("kr_stock", get_start_date(start), end)
    close = cf.get_df("price_close")

    # Debug: Check data loaded correctly
    print(f"Close shape: {close.shape}")
    print(f"Date range: {close.index[0]} to {close.index[-1]}")
    print(f"NaN count: {close.isnull().sum().sum()}")

    momentum = close.pct_change(20)

    # Debug: Check momentum calculation
    print(f"Momentum range: [{momentum.min().min():.4f}, {momentum.max().max():.4f}]")
    print(f"Momentum NaN count: {momentum.isnull().sum().sum()}")

    rank = momentum.rank(pct=True, axis=1)
    selected = rank >= 0.9

    # Debug: Check selection
    print(f"Average stocks selected per day: {selected.sum(axis=1).mean():.1f}")

    positions = selected.div(selected.sum(axis=1), axis=0) * 1e8

    # Debug: Check final positions
    print(f"Position row sums: min={positions.sum(axis=1).min():.0f}, "
          f"max={positions.sum(axis=1).max():.0f}")

    return positions.shift(1).loc[str(start):str(end)]
```

### 2. Use Validation Helper

```python
from helpers import validate_positions

def get(self, start, end):
    # ... strategy logic ...

    # Validate before returning
    validate_positions(positions)

    return positions.shift(1).loc[str(start):str(end)]
```

### 3. Backtest Sanity Checks

```python
from finter.backtest import Simulator

# Run backtest
simulator = Simulator(market_type="kr_stock")
result = simulator.run(position=positions)
stats = result.statistics

# Sanity checks
assert stats['Sharpe Ratio'] < 5, "Sharpe too high - check for look-ahead bias!"
assert stats['Hit Ratio (%)'] < 90, "Hit ratio too high - suspicious!"
assert stats['Max Drawdown (%)'] > 5, "No drawdown - likely data issue!"

print("✓ Sanity checks passed")
```

## Code Quality

### 1. Clear Variable Names

```python
# ❌ UNCLEAR
def get(self, start, end):
    d = cf.get_df("price_close")
    r = d.pct_change(20)
    s = r > 0
    p = s * 1e8 / s.sum(axis=1)
    return p.shift(1)

# ✓ CLEAR
def get(self, start, end):
    from helpers import get_start_date
    cf = ContentFactory("kr_stock", get_start_date(start), end)
    close = cf.get_df("price_close")
    momentum = close.pct_change(20)
    buy_signal = momentum > 0
    positions = buy_signal.div(buy_signal.sum(axis=1), axis=0) * 1e8
    return positions.shift(1).loc[str(start):str(end)]
```

### 2. Document Strategy Logic

```python
class Alpha(BaseAlpha):
    """
    Simple momentum strategy.

    Strategy Logic:
    1. Calculate 20-day price momentum
    2. Select stocks with positive momentum
    3. Equal weight among selected stocks
    4. Rebalance daily

    Parameters:
    - momentum_period: Lookback period for momentum (default: 20)
    - smoothing: Rolling window for position smoothing (default: 5)
    """

    def get(self, start: int, end: int,
            momentum_period: int = 20,
            smoothing: int = 5) -> pd.DataFrame:
        # Implementation...
        pass
```

## Parameter Selection

### 1. Use Reasonable Defaults

```python
# ✓ GOOD - Standard timeframes
momentum_period = 20  # ~1 month
rebalance_freq = 5    # Weekly
lookback = 252        # 1 year

# ❌ BAD - Arbitrary tuned values
momentum_period = 23  # Why 23?
rebalance_freq = 7    # Why 7?
lookback = 187        # Why 187?
```

### 2. Limited Parameter Space

```python
# ✓ GOOD - Focused parameter search
param_grid = {
    'momentum_period': [10, 20, 60],  # Short, medium, long
    'threshold': [0, 0.05]             # With/without threshold
}
# Total: 6 combinations

# ❌ BAD - Excessive parameter search (guaranteed overfitting!)
param_grid = {
    'momentum_period': range(5, 101, 5),  # 20 values
    'threshold': np.arange(0, 0.5, 0.01), # 50 values
    'smoothing': range(1, 21),            # 20 values
}
# Total: 20,000 combinations
```

### 3. Parameter Validation

```python
def get(self, start, end, momentum_period=20):
    # Validate parameters
    if momentum_period < 1:
        raise ValueError("momentum_period must be positive")
    if momentum_period > 252:
        print("⚠️ Warning: momentum_period > 1 year is unusual")

    # Implementation...
```

## Testing Quick Reference

### Quick Position Check

```python
# After generating positions
print(f"Shape: {positions.shape}")
print(f"Row sum range: [{positions.sum(axis=1).min():.0f}, {positions.sum(axis=1).max():.0f}]")
print(f"NaN count: {positions.isnull().sum().sum()}")
```

### Run Quick Backtest

```bash
# Test on 1-month period first
python scripts/backtest_runner.py --code my_alpha.py --start 20240101 --end 20240131
```

## See Also

- `framework.md` - BaseAlpha framework rules
- `research_process.md` - Systematic research methodology
- `../templates/` - Working code examples
