---
name: finter-portfolio
description: Portfolio optimization and alpha combination using the Finter Python library. Use when user requests to combine multiple alphas, optimize portfolio weights, or analyze alpha correlations (e.g., "combine these alphas", "risk parity portfolio", "optimize alpha weights"). Supports the BasePortfolio framework with weight calculation and backtesting.
---

# Finter Portfolio Strategy Development

Develop quantitative portfolio strategies that combine multiple alpha strategies using the Finter framework.

## ⚠️ CRITICAL RULES (MUST FOLLOW)

**Portfolio Class Requirements:**
1. **Class name MUST be `Portfolio`** (not CustomPortfolio, MyPortfolio, etc.)
2. **Method name MUST be `weight`** (not get_weights, calculate, etc.)
3. **Method signature**: `def weight(self, start: int, end: int) -> pd.DataFrame`
4. **ALWAYS shift weights**: `return weights.shift(1)` to avoid look-ahead bias (unless static weights)
5. **Weight normalization**: Weights MUST sum to ~1.0 per row (date)
6. **Alpha list**: Define `alpha_list` as class attribute with strategy names
7. **Use `alpha_pnl_df()`**: Load alpha returns with `self.alpha_pnl_df(market, start, end)`

**Common Mistakes:**

**Mistake 1: Not handling consecutive 1's in alpha returns**
```python
# ❌ WRONG - Ignoring data artifacts
alpha_return_df = self.alpha_pnl_df('us_stock', 19980101, end)
volatility = alpha_return_df.rolling(126).std()  # Wrong volatility!

# ✅ CORRECT - Clean consecutive 1's (no change sequences)
alpha_return_df = self.alpha_pnl_df('us_stock', 19980101, end)
# Find consecutive 1's and keep only first 5 occurrences
find_1 = (alpha_return_df == 1) & (alpha_return_df.shift(1) == 1)
alpha_return_df = alpha_return_df.mask(find_1, np.nan).ffill(limit=5)
volatility = alpha_return_df.rolling(126).std()  # Correct!
```

**Mistake 2: Forgetting weight normalization**
```python
# ❌ WRONG - Weights don't sum to 1
inv_volatility = 1 / volatility_df
return inv_volatility.shift(1)  # Sum != 1.0!

# ✅ CORRECT - Normalize to sum to 1
inv_volatility = 1 / volatility_df
weights = inv_volatility.div(inv_volatility.sum(axis=1), axis=0)
weights = weights.fillna(0)  # Handle NaN
return weights.shift(1)  # Sum = 1.0!
```

**Mistake 3: Not applying shift(1) for dynamic weights**
```python
# ❌ WRONG - Look-ahead bias for return-based weights
weights = alpha_return_df.rolling(20).mean()  # Using today's return
return weights.loc[str(start):str(end)]  # Wrong!

# ✅ CORRECT - Apply shift(1)
weights = alpha_return_df.rolling(20).mean()
return weights.shift(1).loc[str(start):str(end)]  # Correct!

# NOTE: Static weights (equal weight, fixed allocation) don't need shift
```

**Mistake 4: Wrong class/method names**
```python
# ❌ WRONG
class MyPortfolio(BasePortfolio):
    def get_weights(self, start, end):  # Wrong method name!
        return weights  # Missing shift and normalization!

# ✅ CORRECT
class Portfolio(BasePortfolio):
    alpha_list = [...]  # Required!

    def weight(self, start: int, end: int) -> pd.DataFrame:
        # weights calculation...
        return weights.shift(1).loc[str(start):str(end)]  # Correct!
```

## 📋 Workflow (ANALYSIS FIRST)

1. **Load Alpha Returns**: Use `self.alpha_pnl_df()` to get alpha performance data
2. **Analyze Correlations**: Heatmap, rolling correlation, diversification potential
3. **Analyze Performance**: Individual alpha stats (return, sharpe, volatility)
4. **Explore Risk Metrics**: Volatility patterns, drawdowns, regime changes
5. **Choose Algorithm**: Equal weight, risk parity, MVO, etc. (see `references/algorithms.md`)
6. **Implement weight() in Jupyter**: Write Portfolio class based on analysis
7. **Validate Weights**: Check sum=1.0, no NaN, shift applied, sensible ranges
8. **Backtest & Compare**: Use `portfolio.get()` to backtest, ALWAYS compare with equal weight baseline
9. **Save portfolio.py**: Only after successful backtest comparison
10. **Run Scripts (MANDATORY)**: Execute backtest_runner, chart_generator, info_generator

**⚠️ NEVER write Portfolio class before analyzing alpha returns and correlations!**
**⚠️ NEVER save portfolio.py without backtesting and comparing with equal weight!**
**⚠️ NEVER implement get() method - BasePortfolio provides it automatically!**
**⚠️ NEVER skip running scripts after saving portfolio.py!**

## 🎯 First Steps

### Read the Framework First
**BEFORE coding, read `references/framework.md`** - it explains:
- BasePortfolio class structure and requirements
- Weight DataFrame format and constraints
- Data loading with `alpha_pnl_df()`
- Complete minimal example

### Choose Your Algorithm
**Review `references/algorithms.md` for weight calculation methods:**
- **Equal Weight**: Simple 1/N allocation
- **Risk Parity**: Inverse volatility weighting (balanced risk contribution)
- **Mean-Variance Optimization**: Maximize Sharpe ratio
- **Minimum Correlation**: Diversification-focused
- **Black-Litterman**: Incorporate views into optimization

**IMPORTANT**: Start with simple methods (equal weight, risk parity) before complex optimization!

### Handle Data Preprocessing
**Read `references/preprocessing.md` for:**
- Cleaning consecutive 1's in alpha returns
- Calculating rolling metrics (volatility, correlation)
- Handling NaN and zero values
- Date range calculations with buffer

### Use Templates
**Review `templates/examples/` for working code:**
- **`equal_weight.py`**: Simplest baseline (1/N allocation)
- **`risk_parity.py`**: Volatility-based weighting (RECOMMENDED START)
- **`mean_variance.py`**: Optimization-based approach

**IMPORTANT**: Templates show COMPLETE working code. Copy and modify!

### Validate and Backtest in Jupyter
```python
# Step 1: Generate weights
portfolio = Portfolio()
weights = portfolio.weight(20200101, int(datetime.now().strftime("%Y%m%d")))

# Step 2: Sanity checks (CRITICAL!)
print(f"Weight sum per date:\n{weights.sum(axis=1).describe()}")
print(f"Weight range: [{weights.min().min():.3f}, {weights.max().max():.3f}]")
print(f"Any NaN? {weights.isna().any().any()}")
print(f"Date range: {weights.index[0]} to {weights.index[-1]}")

# Step 3: Visualize weights
weights.plot(figsize=(12,6), title='Portfolio Weights Over Time')
weights.sum(axis=1).plot(title='Weight Sum Check (should be ~1.0)', ylim=[0.95, 1.05])

# Step 4: Check alpha correlations
alpha_return_df = portfolio.alpha_pnl_df('us_stock', 20200101, int(datetime.now().strftime("%Y%m%d")))
import seaborn as sns
sns.heatmap(alpha_return_df.corr(), annot=True, cmap='coolwarm', center=0)

# Step 5: Backtest (CRITICAL - BasePortfolio provides get() automatically!)
from finter.backtest import Simulator
simulator = Simulator(market_type="us_stock")
# NO need to implement get() - just call it!
result = simulator.run(position=portfolio.get(20200101, int(datetime.now().strftime("%Y%m%d"))))

# Print metrics
stats = result.statistics
print(f"Total Return: {stats['Total Return (%)']:.2f}%")
print(f"Sharpe Ratio: {stats['Sharpe Ratio']:.2f}")
print(f"Max Drawdown: {stats['Max Drawdown (%)']:.2f}%")

# Visualize NAV
result.summary['nav'].plot(title='Portfolio NAV', figsize=(12,6))

# Step 6: Compare with equal weight baseline (REQUIRED!)
# Create equal weight portfolio (only implement weight() method)
# See references/backtesting.md for complete comparison code
```

## 📚 Documentation

**Read these BEFORE coding:**
1. **`references/framework.md`** - BasePortfolio requirements (READ THIS FIRST!)
2. **`references/algorithms.md`** - Weight calculation algorithms
3. **`references/preprocessing.md`** - Data cleaning and preparation
4. **`references/backtesting.md`** - Portfolio backtesting and evaluation
5. **`references/troubleshooting.md`** - Common mistakes and fixes

**Reference during coding:**
- **`templates/examples/`** - 3 complete portfolio examples with backtesting
- **`references/algorithms.md`** - Algorithm selection guide
- **`references/backtesting.md`** - How to implement get() and run backtests

**Algorithm selection guide:**
- Start simple → `equal_weight.py`
- Balance risk → `risk_parity.py`
- Maximize returns → `mean_variance.py`
- Custom approach → Combine techniques

## ⚡ Quick Reference

**Essential imports:**
```python
from finter import BasePortfolio
from finter.data import ContentFactory
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
```

**BasePortfolio structure:**
```python
class Portfolio(BasePortfolio):
    alpha_list = [
        "us.compustat.stock.user.alpha1",
        "us.compustat.stock.user.alpha2",
    ]

    def weight(self, start: int, end: int) -> pd.DataFrame:
        # Load alpha returns
        alpha_return_df = self.alpha_pnl_df('us_stock', 19980101, end)

        # Clean data
        find_1 = (alpha_return_df == 1) & (alpha_return_df.shift(1) == 1)
        alpha_return_df = alpha_return_df.mask(find_1, np.nan).ffill(limit=5)

        # Calculate weights (example: equal weight)
        n_alphas = len(self.alpha_list)
        weights = pd.DataFrame(
            1.0 / n_alphas,
            index=alpha_return_df.index,
            columns=alpha_return_df.columns
        )

        # CRITICAL: Apply shift(1) and slice date range
        return weights.shift(1).loc[str(start):str(end)]
```

**Date buffer helper:**
```python
def calculate_previous_start_date(start_date: int, lookback_days: int) -> int:
    """Calculate start date for preloading data based on lookback period"""
    start = datetime.strptime(str(start_date), "%Y%m%d")
    previous_start = start - timedelta(days=lookback_days)
    return int(previous_start.strftime("%Y%m%d"))

# Usage
preload_start = calculate_previous_start_date(start, 365)
alpha_return_df = self.alpha_pnl_df('us_stock', preload_start, end)
```

**Understanding shift(1) logic:**
```python
# When to shift:
# 1. ✅ Alpha return based weights → MUST shift(1)
# 2. ⚠️ Volatility/stats based → Recommended shift(1)
# 3. ❌ Static weights → No shift needed

# Example: Risk parity (volatility-based)
volatility_df = alpha_return_df.rolling(126).std()
inv_volatility = 1 / volatility_df.replace(0, np.nan)
weights = inv_volatility.div(inv_volatility.sum(axis=1), axis=0).fillna(0)
return weights.shift(1).loc[str(start):str(end)]  # ← Shift for safety!
```

**DO NOT SKIP** reading `references/framework.md` - it has critical rules!

## 🚀 FINAL STEPS (MANDATORY - After Successful Backtest)

**⚠️ You MUST complete ALL these steps after saving portfolio.py!**

### ⚠️ Improvement Limit
When backtest fails or results are poor:
- You may attempt to improve the portfolio code **UP TO 3 TIMES maximum**
- After 3 attempts, STOP and report the current status
- Do NOT keep trying indefinitely - some strategies simply don't work
- Track: Attempt 1 (fix obvious) → Attempt 2 (try alternative) → Attempt 3 (final, then report)

### Step 1: Save portfolio.py
Save final Portfolio class to workspace using Write tool (NOT Jupyter).

### Step 2: Run Backtest Script
```bash
python .claude/skills/finter-portfolio/scripts/backtest_runner.py --code portfolio.py --universe us_stock
```
- Validates portfolio weights and runs backtest
- If validation fails → fix portfolio.py and re-run
- Generates: `backtest_summary.csv`, `backtest_stats.csv`

### Step 3: Generate Chart
```bash
python .claude/skills/finter-portfolio/scripts/chart_generator.py --summary backtest_summary.csv --stats backtest_stats.csv
```
- Generates: `chart.png`

### Step 4: Generate Info
```bash
python .claude/skills/finter-portfolio/scripts/info_generator.py \
    --title "Portfolio Name" \
    --summary "One-line description" \
    --category composite \
    --universe us_stock \
    --investable \
    --evaluation "Performance vs equal weight baseline" \
    --lessons "Key learnings from optimization"
```
- **--title**: English only, max 34 chars
- **--category**: momentum|value|quality|growth|size|low_vol|technical|macro|stat_arb|event|ml|composite
- **--universe**: kr_stock|us_stock|vn_stock|id_stock|us_etf
- **--investable** or **--not-investable**: Production ready vs experimental
- Generates: `info.json`

### Step 5: Final Summary
Add ONE markdown cell summarizing:
- Portfolio performance vs equal weight baseline
- Risk-adjusted metrics comparison
- Suggested improvements

**⚠️ Task is NOT complete until all 5 steps are done!**
