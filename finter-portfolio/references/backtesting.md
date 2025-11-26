# Portfolio Backtesting and Evaluation

Guide to backtesting portfolio strategies and comparing performance against baselines.

## Overview

Portfolio backtesting validates whether your weight allocation strategy actually improves performance compared to simple baselines like equal weight. **ALWAYS backtest before finalizing your portfolio.**

---

## Portfolio Backtesting Concept

### Portfolio vs Alpha Backtesting

**Alpha Backtesting**:
- Input: Position DataFrame (date x stocks)
- Output: Performance metrics (return, Sharpe, drawdown)

**Portfolio Backtesting**:
- Input: Weight DataFrame (date x alphas) → Convert to Position
- Process: Combine weighted alpha positions
- Output: Performance metrics + comparison with baseline

### Key Difference

Portfolio backtesting requires an additional step: **converting weights to positions**.

```python
# Step 1: Calculate weights
weights = portfolio.weight(start, end)  # date x alpha_names

# Step 2: Convert weights to positions (NEW!)
positions = portfolio.get(start, end)   # date x stocks (combined)

# Step 3: Backtest positions (same as alpha)
from finter.backtest import Simulator
simulator = Simulator(market_type="us_stock")
result = simulator.run(position=positions)
```

---

## Understanding the get() Method

### ⚠️ CRITICAL: DO NOT IMPLEMENT get() METHOD

**BasePortfolio already provides the `get()` method automatically!**

You only need to implement the `weight()` method. BasePortfolio will handle the rest.

### How get() Works (Automatically)

```python
# Conceptually (BasePortfolio does this for you):
# weights:    date x alpha_names (e.g., 3 alphas)
# positions:  date x stocks (e.g., 500 stocks)

# For each date:
#   final_position[stock] = Σ(weight[alpha] × alpha_position[alpha, stock])
```

### Your Portfolio Class (Simple!)

```python
class Portfolio(BasePortfolio):
    alpha_list = [...]

    def weight(self, start: int, end: int) -> pd.DataFrame:
        # Calculate weights
        # ... (your weight calculation logic)
        return weights.shift(1).loc[str(start):str(end)]

    # That's it! NO need to implement get()
```

### Using get() Method

BasePortfolio automatically provides `get()`, so just call it:

```python
portfolio = Portfolio()

# Just call get() - it works automatically!
positions = portfolio.get(20200101, int(datetime.now().strftime("%Y%m%d")))

# positions is now a combined DataFrame (date x stocks)
# Ready for backtesting!
```

### What BasePortfolio.get() Does Automatically

1. **Loads your weights**: Calls your `weight()` method
2. **Loads each alpha's positions**: Gets actual positions from each alpha
3. **Combines positions**: Multiplies each alpha's positions by your weights
4. **Returns combined positions**: Returns final portfolio positions

### Important Notes

1. **Only implement weight()**: BasePortfolio handles position combination
2. **Weight normalization**: Make sure weights sum to ~1.0
3. **Date alignment**: BasePortfolio handles date/stock universe alignment automatically

---

## Running the Backtest

### Basic Backtest

```python
from finter.backtest import Simulator

# Step 1: Create portfolio and generate positions
portfolio = Portfolio()
positions = portfolio.get(20200101, int(datetime.now().strftime("%Y%m%d")))

# Step 2: Run backtest
simulator = Simulator(market_type="us_stock")
result = simulator.run(position=positions)

# Step 3: Check results (use EXACT field names!)
stats = result.statistics
print(f"Total Return: {stats['Total Return (%)']:.2f}%")
print(f"Sharpe Ratio: {stats['Sharpe Ratio']:.2f}")
print(f"Max Drawdown: {stats['Max Drawdown (%)']:.2f}%")
print(f"Hit Ratio: {stats['Hit Ratio (%)']:.2f}%")

# Step 4: Visualize NAV curve
result.summary['nav'].plot(title='Portfolio NAV (starts at 1000)', figsize=(12,6))
```

**IMPORTANT**:
- NAV always starts at 1000 (not 1 or 1e8!)
- DO NOT use 'Annual Return (%)' - it doesn't exist in result.statistics

### Result Structure

```python
result.statistics:  # Dict with performance metrics
    'Total Return (%)'
    'Sharpe Ratio'
    'Max Drawdown (%)'
    ...

result.summary:  # DataFrame with time series
    'nav'           # Net Asset Value (starts at 1000)
    'daily_return'  # Daily returns
    ...
```

---

## Comparing with Equal Weight Baseline

### Why Compare with Equal Weight?

1. **Baseline performance**: Is your optimization worth the complexity?
2. **Risk assessment**: Does optimization reduce or increase risk?
3. **Robustness check**: Simple methods often outperform complex ones
4. **1/N paradox**: Equal weight is notoriously hard to beat

### Implementation

```python
# Backtest your optimized portfolio
optimized_result = simulator.run(position=optimized_portfolio.get(start, end))

# Create equal weight baseline
class EqualWeightPortfolio(BasePortfolio):
    alpha_list = [...] # Same as optimized portfolio

    def weight(self, start: int, end: int) -> pd.DataFrame:
        preload_start = calculate_previous_start_date(start, 365)
        alpha_return_df = self.alpha_pnl_df('us_stock', preload_start, end)
        n = len(self.alpha_list)
        weights = pd.DataFrame(1.0/n, index=alpha_return_df.index, columns=alpha_return_df.columns)
        return weights.loc[str(start):str(end)]

    # NO need to implement get() - BasePortfolio provides it!

# Backtest baseline
baseline_portfolio = EqualWeightPortfolio()
baseline_result = simulator.run(position=baseline_portfolio.get(start, end))

# Compare metrics
print("=" * 60)
print("Performance Comparison")
print("=" * 60)
print(f"{'Metric':<20} {'Optimized':>15} {'Equal Weight':>15} {'Difference':>15}")
print("-" * 60)

metrics = ['Total Return (%)', 'Sharpe Ratio', 'Max Drawdown (%)', 'Hit Ratio (%)']
for metric in metrics:
    opt_val = optimized_result.statistics[metric]
    base_val = baseline_result.statistics[metric]
    diff = opt_val - base_val
    print(f"{metric:<20} {opt_val:>15.2f} {base_val:>15.2f} {diff:>+15.2f}")
```

---

## Visualization Best Practices

### 1. NAV Comparison

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(12, 6))

# Plot both NAV curves
optimized_result.summary['nav'].plot(ax=ax, label='Optimized Portfolio', linewidth=2)
baseline_result.summary['nav'].plot(ax=ax, label='Equal Weight Baseline', linewidth=2, linestyle='--')

ax.set_title('Portfolio Performance Comparison', fontsize=14)
ax.set_ylabel('NAV (starts at 1000)')
ax.legend()
ax.grid(True, alpha=0.3)
plt.show()
```

### 2. Drawdown Comparison

```python
# Calculate drawdowns
opt_nav = optimized_result.summary['nav']
base_nav = baseline_result.summary['nav']

opt_dd = (opt_nav / opt_nav.cummax() - 1) * 100
base_dd = (base_nav / base_nav.cummax() - 1) * 100

fig, ax = plt.subplots(figsize=(12, 6))
opt_dd.plot(ax=ax, label='Optimized', linewidth=2)
base_dd.plot(ax=ax, label='Equal Weight', linewidth=2, linestyle='--')
ax.fill_between(opt_dd.index, opt_dd, 0, alpha=0.3)
ax.set_title('Drawdown Comparison (%)', fontsize=14)
ax.set_ylabel('Drawdown (%)')
ax.legend()
ax.grid(True, alpha=0.3)
plt.show()
```

### 3. Rolling Sharpe Comparison

```python
# Calculate rolling 60-day Sharpe
window = 60
opt_returns = optimized_result.summary['daily_return']
base_returns = baseline_result.summary['daily_return']

opt_sharpe = opt_returns.rolling(window).mean() / opt_returns.rolling(window).std() * np.sqrt(252)
base_sharpe = base_returns.rolling(window).mean() / base_returns.rolling(window).std() * np.sqrt(252)

fig, ax = plt.subplots(figsize=(12, 6))
opt_sharpe.plot(ax=ax, label='Optimized', linewidth=2)
base_sharpe.plot(ax=ax, label='Equal Weight', linewidth=2, linestyle='--')
ax.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
ax.set_title('Rolling 60-Day Sharpe Ratio', fontsize=14)
ax.set_ylabel('Sharpe Ratio (Annualized)')
ax.legend()
ax.grid(True, alpha=0.3)
plt.show()
```

### 4. Metrics Bar Chart

```python
import pandas as pd

# Create comparison DataFrame
comparison = pd.DataFrame({
    'Optimized': [
        optimized_result.statistics['Total Return (%)'],
        optimized_result.statistics['Sharpe Ratio'],
        -optimized_result.statistics['Max Drawdown (%)'],  # Negative for visual
        optimized_result.statistics['Hit Ratio (%)']
    ],
    'Equal Weight': [
        baseline_result.statistics['Total Return (%)'],
        baseline_result.statistics['Sharpe Ratio'],
        -baseline_result.statistics['Max Drawdown (%)'],
        baseline_result.statistics['Hit Ratio (%)']
    ]
}, index=['Total Return (%)', 'Sharpe Ratio', 'Max DD (%) [inverted]', 'Hit Ratio (%)'])

comparison.plot(kind='bar', figsize=(10, 6), rot=0)
plt.title('Performance Metrics Comparison')
plt.ylabel('Value')
plt.legend()
plt.grid(True, alpha=0.3, axis='y')
plt.tight_layout()
plt.show()
```

---

## Metrics Interpretation

### When Optimization Works

Your optimized portfolio is successful if:
- **Higher Sharpe**: Risk-adjusted returns improved
- **Lower Drawdown**: Risk management is better
- **Comparable or Higher Return**: Not sacrificing returns

### When to Stick with Equal Weight

Consider equal weight if:
- **Lower Sharpe**: Optimization hurt risk-adjusted returns
- **Higher Drawdown**: Increased risk
- **Unstable weights**: High turnover (transaction costs)
- **Marginal improvement**: Complexity not worth <10% Sharpe improvement

### Red Flags

⚠️ **Warning signs**:
- Sharpe much higher but drawdown also much higher → Over-leveraged
- Return higher but very high turnover → Transaction costs will kill gains
- Performance only good in certain periods → Overfitting
- Large gap between in-sample and out-of-sample → Not robust

---

## Complete Backtesting Template

```python
from finter import BasePortfolio
from finter.backtest import Simulator
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Your optimized portfolio
class OptimizedPortfolio(BasePortfolio):
    alpha_list = [...]

    def weight(self, start, end):
        # Your weight calculation
        return weights

    # NO need to implement get() - BasePortfolio provides it!

# Equal weight baseline
class EqualWeightBaseline(BasePortfolio):
    alpha_list = OptimizedPortfolio.alpha_list  # Same alphas!

    def weight(self, start, end):
        preload_start = calculate_previous_start_date(start, 365)
        alpha_return_df = self.alpha_pnl_df('us_stock', preload_start, end)
        n = len(self.alpha_list)
        weights = pd.DataFrame(1.0/n, index=alpha_return_df.index, columns=alpha_return_df.columns)
        return weights.loc[str(start):str(end)]

    # NO need to implement get() - BasePortfolio provides it!

# Backtest both
simulator = Simulator(market_type="us_stock")
opt_result = simulator.run(position=OptimizedPortfolio().get(20200101, int(datetime.now().strftime("%Y%m%d"))))
base_result = simulator.run(position=EqualWeightBaseline().get(20200101, int(datetime.now().strftime("%Y%m%d"))))

# Compare
print("Performance Comparison:")
for metric in ['Total Return (%)', 'Sharpe Ratio', 'Max Drawdown (%)', 'Hit Ratio (%)']:
    print(f"{metric}: {opt_result.statistics[metric]:.2f} vs {base_result.statistics[metric]:.2f}")

# Visualize
fig, axes = plt.subplots(2, 1, figsize=(12, 10))
opt_result.summary['nav'].plot(ax=axes[0], label='Optimized')
base_result.summary['nav'].plot(ax=axes[0], label='Equal Weight')
axes[0].legend()
axes[0].set_title('NAV Comparison')

# Drawdown
opt_dd = (opt_result.summary['nav'] / opt_result.summary['nav'].cummax() - 1) * 100
base_dd = (base_result.summary['nav'] / base_result.summary['nav'].cummax() - 1) * 100
opt_dd.plot(ax=axes[1], label='Optimized')
base_dd.plot(ax=axes[1], label='Equal Weight')
axes[1].legend()
axes[1].set_title('Drawdown (%)')
plt.tight_layout()
plt.show()
```

---

## Validation Checklist

Before finalizing your portfolio, verify:

1. **Backtest completed**: ✓ Ran backtest successfully
2. **Baseline comparison**: ✓ Compared with equal weight
3. **Metrics reviewed**: ✓ Sharpe, drawdown, return analyzed
4. **Visual inspection**: ✓ NAV and drawdown charts reviewed
5. **No overfitting**: ✓ Results reasonable and stable
6. **Transaction costs considered**: ✓ Turnover is acceptable

---

## Common Issues

### Issue 1: NAV is Flat (No Change)

**Cause**: Combined positions sum to zero or very small

**Solution**:
```python
# Debug: Check combined position magnitude
combined_position = portfolio.get(start, end)
print(f"Position sum per date:\n{combined_position.sum(axis=1).describe()}")
```

### Issue 2: Backtest Fails with Error

**Cause**: Position format incorrect (NaN, wrong dtype, etc.)

**Solution**:
```python
# Validate position DataFrame
print(f"Position shape: {combined_position.shape}")
print(f"Any NaN? {combined_position.isna().any().any()}")
print(f"Date range: {combined_position.index[0]} to {combined_position.index[-1]}")
```

---

## Next Steps

- **Run backtest**: Use `portfolio.get()` to validate performance
- **Compare baseline**: Check vs equal weight
- **Iterate**: Adjust weights if needed
- **Save portfolio.py**: Only after successful backtest

**Remember**: BasePortfolio provides `get()` automatically - just implement `weight()`!
