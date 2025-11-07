# Research Guidelines for Alpha Development

Systematic approach to developing and validating quantitative trading strategies.

## Research Process Overview

1. **Hypothesis Formation** - Define investment thesis
2. **Data Exploration** - Analyze available data and relationships
3. **Strategy Development** - Implement alpha logic
4. **Backtesting** - Evaluate historical performance
5. **Validation** - Check for robustness and overfitting
6. **Iteration** - Refine based on results

## 1. Hypothesis Formation

### Questions to Answer

- **What market inefficiency are you exploiting?**
  - Momentum persistence?
  - Mean reversion?
  - Valuation anomaly?
  - Behavioral bias?

- **Why should this work?**
  - Economic rationale?
  - Behavioral explanation?
  - Risk premium?

- **What is the expected holding period?**
  - Intraday?
  - Days to weeks?
  - Months?

### Example Hypotheses

**Good:**
- "Stocks with strong recent momentum outperform because investor attention and institutional buying create persistence"
- "Stocks trading below their historical valuation multiples tend to revert as markets correct mispricings"

**Bad:**
- "I'll combine every possible indicator and optimize"
- "This pattern worked well in the backtest"

## 2. Data Exploration

### Initial Analysis Checklist

```python
from finter.data import ContentFactory
import pandas as pd

cf = ContentFactory("kr_stock", 20150101, 20241231)

# 1. Check data availability
cf.summary()
available_items = cf.search("your_term")

# 2. Load key data
price = cf.get_df("price_close")
volume = cf.get_df("volume")

# 3. Check data quality
print(f"Date range: {price.index[0]} to {price.index[-1]}")
print(f"Number of stocks: {price.shape[1]}")
print(f"Missing values: {price.isnull().sum().sum()}")
print(f"Missing ratio: {price.isnull().sum().sum() / price.size:.2%}")

# 4. Visualize distributions
price.pct_change().describe()
volume.describe()
```

### Key Metrics to Check

- **Data coverage**: How many stocks? Date range?
- **Missing data**: What percentage? Randomly distributed?
- **Outliers**: Any extreme values? Data errors?
- **Liquidity**: Sufficient trading volume?

## 3. Strategy Development

### Implementation Checklist

- [ ] **Clear logic**: Can you explain the strategy in 2-3 sentences?
- [ ] **Proper shifting**: Always use `.shift(1)` to avoid look-ahead bias
- [ ] **Position constraints**: Row sums ≤ 1e8
- [ ] **Handle missing data**: NaN values properly managed
- [ ] **Parameter bounds**: Reasonable parameter ranges
- [ ] **Code comments**: Logic is documented

### Anti-Patterns to Avoid

❌ **Over-complication**
```python
# Bad: Too many conditions and special cases
if condition1 and condition2:
    if condition3 or (condition4 and condition5):
        signal = complex_calculation()
```

✓ **Simplicity**
```python
# Good: Clear, understandable logic
momentum = price.pct_change(period)
signal = momentum > threshold
```

❌ **Data snooping**
```python
# Bad: Using parameters tuned on same period
momentum_period = 23  # "This worked best in backtest"
```

✓ **Justifiable parameters**
```python
# Good: Theoretically motivated
momentum_period = 21  # Standard monthly lookback
```

## 4. Backtesting

### Standard Backtest Setup

```python
from finter.backtest import Simulator

# Run with realistic costs
simulator = Simulator(
    market_type="kr_stock",
    commission_rate=0.0025,  # 0.25%
    slippage_rate=0.001,     # 0.1%
    tax_rate=0.0023         # 0.23%
)

result = simulator.run(position=positions)
stats = result.statistics
```

### Metrics to Evaluate

**Primary Metrics:**
- Sharpe Ratio (> 1.0 good, > 2.0 excellent)
- Maximum Drawdown (< 30% acceptable)
- Total Return (compare to benchmark)

**Secondary Metrics:**
- Win Rate (> 50% desirable but not required)
- Profit Factor (> 1.5 good)
- Average Win vs Average Loss ratio

**Warning Signs:**
- Too good to be true (Sharpe > 3.0)
- Very high win rate with low Sharpe (lots of small wins, huge losses)
- Drawdowns lasting > 2 years
- Strategy works only in specific periods

### Time Period Analysis

Test across different market regimes:

```python
# Test in different periods
test_periods = [
    (20150101, 20171231),  # Bull market
    (20180101, 20191231),  # Volatile period
    (20200101, 20211231),  # COVID & recovery
    (20220101, 20241231),  # Recent period
]

results = []
for start, end in test_periods:
    positions = alpha.get(start, end)
    result = simulator.run(position=positions)
    results.append({
        'period': f"{start}-{end}",
        'sharpe': result.statistics['Sharpe Ratio'],
        'return': result.statistics['Total Return (%)']
    })

# Check consistency across periods
print(pd.DataFrame(results))
```

## 5. Validation

### Overfitting Detection

**Warning Signs:**
- Large parameter grid tested (> 100 combinations)
- Performance degrades significantly out-of-sample
- Strategy very sensitive to parameter changes
- Complex conditional logic added to "fix" backtest issues

### Robustness Tests

#### 1. Parameter Sensitivity

```python
import numpy as np
import matplotlib.pyplot as plt

# Test parameter sensitivity
base_param = 20
param_range = range(10, 51, 5)
results = []

for param in param_range:
    positions = alpha.get(20200101, 20241231, momentum_period=param)
    result = simulator.run(position=positions)
    results.append(result.statistics['Sharpe Ratio'])

# Plot sensitivity
plt.plot(param_range, results)
plt.xlabel('Momentum Period')
plt.ylabel('Sharpe Ratio')
plt.title('Parameter Sensitivity')
```

**Good**: Gradual change, stable performance across range
**Bad**: Sharp peaks, only works at specific values

#### 2. Rolling Window Validation

```python
# Walk-forward analysis
window_size = 365 * 2  # 2 years
step_size = 365 // 4   # Quarter

start_date = 20150101
end_date = 20241231

results = []
current = start_date
while current + window_size <= end_date:
    window_end = current + window_size
    
    positions = alpha.get(current, window_end)
    result = simulator.run(position=positions)
    
    results.append({
        'window_start': current,
        'sharpe': result.statistics['Sharpe Ratio']
    })
    
    current += step_size

# Check stability
sharpes = [r['sharpe'] for r in results]
print(f"Mean Sharpe: {np.mean(sharpes):.2f}")
print(f"Std Sharpe: {np.std(sharpes):.2f}")
print(f"Min Sharpe: {np.min(sharpes):.2f}")
```

#### 3. Transaction Cost Sensitivity

```python
# Test with varying costs
cost_scenarios = [
    {'commission': 0.001, 'slippage': 0.0005},  # Low cost
    {'commission': 0.0025, 'slippage': 0.001},  # Base case
    {'commission': 0.005, 'slippage': 0.002},   # High cost
]

for costs in cost_scenarios:
    simulator = Simulator(
        market_type="kr_stock",
        commission_rate=costs['commission'],
        slippage_rate=costs['slippage']
    )
    result = simulator.run(position=positions)
    print(f"Costs: {costs}")
    print(f"Sharpe: {result.statistics['Sharpe Ratio']:.2f}")
```

**Good**: Strategy profitable even with higher costs
**Bad**: Performance disappears with realistic costs

### Hold-Out Testing

Always keep a final test set untouched:

```python
# Development: Use this for all strategy development
dev_start, dev_end = 20150101, 20221231

# Hold-out: Test ONLY ONCE at the very end
holdout_start, holdout_end = 20230101, 20241231

# Never optimize using hold-out period!
```

## 6. Iteration

### When to Iterate

**Good Reasons:**
- Strategy has clear economic rationale but poor execution
- Discovered data quality issues
- Found better proxy for original hypothesis
- Simplified overly complex strategy

**Bad Reasons:**
- "Let me try one more parameter combination"
- "I'll add this indicator to boost Sharpe"
- "This works in 2020, let me add conditions for other years"

### Documentation

Keep a research log:

```markdown
## Momentum Strategy v1.0
**Date**: 2024-01-15
**Hypothesis**: 20-day momentum predicts next-day returns
**Results**: Sharpe 0.8, but high turnover
**Issues**: Transaction costs too high
**Next steps**: Add position smoothing

## Momentum Strategy v1.1  
**Date**: 2024-01-20
**Changes**: Added 5-day rolling average to reduce turnover
**Results**: Sharpe 1.2, turnover reduced 40%
**Status**: Ready for production testing
```

## Final Checklist Before Production

- [ ] Economic rationale is clear and documented
- [ ] No look-ahead bias (all `.shift(1)` in place)
- [ ] Tested across multiple time periods
- [ ] Robust to parameter changes
- [ ] Profitable with realistic transaction costs
- [ ] Hold-out test shows consistent performance
- [ ] Code is clean and documented
- [ ] Risk metrics are acceptable (max drawdown < 30%)
- [ ] Turnover and capacity are reasonable
- [ ] Research log is complete

## Common Pitfalls

### 1. Look-Ahead Bias
Most common error! Always shift signals.

### 2. Survivorship Bias
Ensure historical data includes delisted stocks.

### 3. Data Snooping
Testing many strategies on same data leads to false discoveries.

### 4. Curve Fitting
Too many parameters = overfitting to noise.

### 5. Ignoring Costs
Strategy may be unprofitable after costs.

### 6. Regime Dependence
Working only in bull markets isn't robust.

## See Also

- `best_practices.md` - Performance optimization tips
- `alpha_examples.md` - Working strategy implementations
- `base_alpha_guide.md` - Implementation framework
