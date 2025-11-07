# Alpha Development Best Practices

Performance optimization tips, common mistakes, and debugging strategies.

## Common Mistakes and Solutions

### 1. Look-Ahead Bias

**Problem**: Using future information to make past decisions.

```python
# ❌ WRONG - This is the #1 mistake!
def get(self, start, end):
    momentum = close.pct_change(20)
    # Forgot to shift - using today's momentum to trade today!
    return momentum.loc[str(start):str(end)]

# ✓ CORRECT - Always shift positions
def get(self, start, end):
    # Load data with buffer
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

### 2. Position Constraint Violations

**Problem**: Row sums exceed 1e8 (total AUM).

```python
# ❌ WRONG - Positions can exceed total capital
def get(self, start, end):
    signals = momentum > 0
    positions = signals * 1e8  # Each position is 100%!
    return positions.shift(1).loc[str(start):str(end)]

# ✓ CORRECT - Normalize to total capital
def get(self, start, end):
    # Load data with buffer
    cf = ContentFactory("kr_stock", get_start_date(start, 20 * 2 + 250), end)
    close = cf.get_df("price_close")
    momentum = close.pct_change(20)

    signals = momentum > 0
    # Divide by number of positions, 1e8 == 100% of AUM
    positions = signals.div(signals.sum(axis=1), axis=0) * 1e8

    # CRITICAL: Always shift positions to avoid look-ahead bias
    return positions.shift(1).loc[str(start):str(end)]
```

**Validation:**
```python
# Check position constraints
row_sums = positions.sum(axis=1)
assert (row_sums <= 1e8 + 1).all(), f"Max row sum: {row_sums.max()}"
print(f"✓ Position constraints satisfied")
```

### 3. Insufficient Data Buffer

**Problem**: Not loading enough historical data for calculations.

```python
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

    # CRITICAL: Always shift positions to avoid look-ahead bias
    return momentum.shift(1).loc[str(start):str(end)]
```

**Rule of Thumb:** Buffer = 2x longest lookback period + 250 days

Use the helper function:
```python
def get_start_date(start: int, buffer: int = 365) -> int:
    """
    Get start date with buffer days
    Rule of thumb: buffer = 2x longest lookback + 250 days
    """
    from datetime import datetime, timedelta
    return int(
        (datetime.strptime(str(start), "%Y%m%d") - timedelta(days=buffer)).strftime("%Y%m%d")
    )
```

### 4. NaN Handling

**Problem**: NaN values propagate through calculations.

```python
# ❌ WRONG - NaN values create empty positions
def get(self, start, end):
    cf = ContentFactory("kr_stock", get_start_date(start, 20 * 2 + 250), end)
    close = cf.get_df("price_close")
    momentum = close.pct_change(20)
    # If any NaN, entire row becomes NaN after division
    positions = momentum.div(momentum.sum(axis=1), axis=0) * 1e8

# ✓ CORRECT - Handle NaN explicitly
def get(self, start, end):
    # Load data with buffer
    cf = ContentFactory("kr_stock", get_start_date(start, 20 * 2 + 250), end)
    close = cf.get_df("price_close")
    momentum = close.pct_change(20)

    # Fill NaN with 0 or drop
    momentum_clean = momentum.fillna(0)
    # Or: momentum_clean = momentum.dropna(axis=1, how='all')

    # Equal weight selected stocks, 1e8 == 100% of AUM
    positions = momentum_clean.div(momentum_clean.sum(axis=1), axis=0) * 1e8

    # CRITICAL: Always shift positions to avoid look-ahead bias
    return positions.shift(1).loc[str(start):str(end)]
```

### 5. Incorrect Class Name

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

## Performance Optimization

### 1. Vectorization Over Loops

```python
# ❌ SLOW - Row-by-row iteration
def get(self, start, end):
    cf = ContentFactory("kr_stock", get_start_date(start, 20 * 2 + 250), end)
    close = cf.get_df("price_close")

    results = []
    for date in close.index:
        row = close.loc[date]
        momentum = row.pct_change()
        results.append(momentum)
    return pd.DataFrame(results)

# ✓ FAST - Vectorized operations
def get(self, start, end):
    # Load data with buffer
    cf = ContentFactory("kr_stock", get_start_date(start, 20 * 2 + 250), end)
    close = cf.get_df("price_close")

    # Operates on entire DataFrame at once
    momentum = close.pct_change(20)

    # CRITICAL: Always shift positions to avoid look-ahead bias
    return momentum.shift(1).loc[str(start):str(end)]
```

**Speed Improvement:** 10-100x faster

### 2. Avoid Redundant Calculations

```python
# ❌ INEFFICIENT - Calculating same thing multiple times
def get(self, start, end):
    close = cf.get_df("price_close")
    
    momentum = close.pct_change(20)
    momentum_rank = momentum.rank(pct=True, axis=1)
    
    # Recalculating momentum again!
    signals = close.pct_change(20) > 0

# ✓ EFFICIENT - Calculate once, reuse
def get(self, start, end):
    close = cf.get_df("price_close")
    
    momentum = close.pct_change(20)  # Calculate once
    momentum_rank = momentum.rank(pct=True, axis=1)
    signals = momentum > 0  # Reuse calculation
```

### 3. Smart Data Loading

```python
# ❌ INEFFICIENT - Loading unnecessary data
def get(self, start, end):
    cf = ContentFactory("kr_stock", start - 10000, end)
    
    # Loading all these but only using close!
    open_price = cf.get_df("price_open")
    high = cf.get_df("price_high")
    low = cf.get_df("price_low")
    close = cf.get_df("price_close")
    volume = cf.get_df("volume")
    
    momentum = close.pct_change(20)

# ✓ EFFICIENT - Load only what you need
def get(self, start, end):
    cf = ContentFactory("kr_stock", start - 10000, end)
    close = cf.get_df("price_close")  # Only necessary data
    momentum = close.pct_change(20)
```

## Debugging Strategies

### 1. Inspect Intermediate Results

```python
def get(self, start, end):
    cf = ContentFactory("kr_stock", start - 10000, end)
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

### 2. Validate Each Step

```python
def validate_dataframe(df, name="DataFrame"):
    """Validation helper function"""
    print(f"\n=== {name} Validation ===")
    print(f"Shape: {df.shape}")
    print(f"NaN count: {df.isnull().sum().sum()} ({df.isnull().sum().sum() / df.size:.1%})")
    print(f"Inf count: {np.isinf(df).sum().sum()}")
    print(f"Value range: [{df.min().min():.4f}, {df.max().max():.4f}]")
    
    if df.sum(axis=1).max() > 1e8 + 1:
        print(f"⚠️ WARNING: Row sums exceed 1e8! Max: {df.sum(axis=1).max():.0f}")
    else:
        print(f"✓ Row sum constraint satisfied")
```

### 3. Backtest Sanity Checks

```python
from finter.backtest import Simulator

# Run backtest
result = simulator.run(position=positions)
stats = result.statistics

# Sanity checks
assert stats['Sharpe Ratio'] < 5, "Sharpe too high - check for look-ahead bias!"
assert stats['Win Rate (%)'] < 90, "Win rate too high - suspicious!"
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
```

### 3. Modular Functions

```python
class Alpha(BaseAlpha):
    def _calculate_momentum(self, close, period):
        """Calculate price momentum"""
        return close.pct_change(period)
    
    def _select_stocks(self, momentum, threshold):
        """Select stocks above threshold"""
        return momentum > threshold
    
    def _create_positions(self, signals):
        """Convert signals to position sizes"""
        return signals.div(signals.sum(axis=1), axis=0) * 1e8
    
    def get(self, start, end):
        cf = ContentFactory("kr_stock", start - 10000, end)
        close = cf.get_df("price_close")
        
        momentum = self._calculate_momentum(close, period=20)
        signals = self._select_stocks(momentum, threshold=0)
        positions = self._create_positions(signals)
        
        return positions.shift(1).loc[str(start):str(end)]
```

## Testing Strategies

### 1. Unit Test Key Components

```python
def test_momentum_calculation():
    """Test momentum calculation is correct"""
    # Create simple test data
    test_data = pd.DataFrame({
        'A': [100, 110, 120],
        'B': [100, 95, 90]
    })
    
    momentum = test_data.pct_change(1)
    
    assert abs(momentum.loc[1, 'A'] - 0.1) < 0.001  # 10% gain
    assert abs(momentum.loc[1, 'B'] - (-0.05)) < 0.001  # 5% loss
    
    print("✓ Momentum calculation test passed")

test_momentum_calculation()
```

### 2. Test Edge Cases

```python
def test_edge_cases():
    """Test strategy handles edge cases"""
    
    # All NaN data
    nan_data = pd.DataFrame(np.nan, index=range(100), columns=range(10))
    positions = alpha.get(20240101, 20240201)
    assert not positions.isnull().all().all(), "Strategy should handle all-NaN input"
    
    # Single stock
    single_stock = close.iloc[:, :1]
    positions = alpha.get(20240101, 20240201)
    assert positions.shape[1] >= 1, "Strategy should work with single stock"
    
    # All negative momentum
    # ... more tests ...
    
    print("✓ Edge case tests passed")
```

## Parameter Selection Guidelines

### 1. Reasonable Defaults

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

# ❌ BAD - Excessive parameter search
param_grid = {
    'momentum_period': range(5, 101, 5),  # 20 values
    'threshold': np.arange(0, 0.5, 0.01), # 50 values
    'smoothing': range(1, 21),            # 20 values
}
# Total: 20,000 combinations - guaranteed overfitting!
```

### 3. Parameter Constraints

```python
def get(self, start, end, momentum_period=20):
    # Validate parameters
    if momentum_period < 1:
        raise ValueError("momentum_period must be positive")
    if momentum_period > 252:
        print("⚠️ Warning: momentum_period > 1 year is unusual")
    
    # Implementation...
```

## See Also

- `research_guidelines.md` - Systematic research process
- `alpha_examples.md` - Working strategy implementations
- `base_alpha_guide.md` - Framework documentation
