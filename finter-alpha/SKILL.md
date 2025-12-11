---
name: finter-alpha
description: Quantitative trading alpha strategy development using the Finter Python library. Use when user requests to create, modify, or analyze alpha strategies (e.g., "create RSI strategy", "momentum alpha", "create momentum strategy", "combine value and momentum factors"). Supports the BaseAlpha framework with automated backtesting and result analysis.
---

# Finter Alpha Strategy Development

Develop quantitative trading alpha strategies using the Finter framework.

## ⚠️ CRITICAL RULES (MUST FOLLOW)

**Alpha Class Requirements:**
1. **Class name MUST be `Alpha`** (not CustomStrategy, MyAlpha, etc.)
2. **Method name MUST be `get`** (not generate, calculate, etc.)
3. **Method signature**: `def get(self, start: int, end: int, **kwargs) -> pd.DataFrame`
4. **ALWAYS shift positions**: `return positions.shift(1)` to avoid look-ahead bias
5. **Position values = MONEY AMOUNT** (1e8 = 100% AUM), NOT signals (1/-1)!
6. **Date buffer**: Use `get_start_date(start, buffer)`, NEVER `start - 300`!

**Common Mistakes:**

**Mistake 1: Using signals instead of money amounts**
```python
# ❌ WRONG - Using 1/-1 signals
momentum = close.pct_change(20)
positions = (momentum > 0).astype(float)  # Returns 1 or 0
return positions.shift(1)  # WRONG! These are signals, not money!

# ✅ CORRECT - Using money amounts (1e8 = 100% AUM)
momentum = close.pct_change(20)
selected = momentum > 0
positions = selected.div(selected.sum(axis=1), axis=0) * 1e8  # Equal weight
return positions.shift(1)  # Each position is money amount!
```

**Mistake 2: Wrong date buffer calculation**
```python
# ❌ WRONG - Direct subtraction breaks date format
cf = ContentFactory("kr_stock", start - 300, end)  # 20240101 - 300 = 20239801!

# ✅ CORRECT - Use get_start_date helper
from helpers import get_start_date
cf = ContentFactory("kr_stock", get_start_date(start, buffer=300), end)

# get_start_date is included in all templates!
def get_start_date(start: int, buffer: int = 365) -> int:
    """
    Get start date with buffer days for data loading.
    Rule of thumb: buffer = 2x longest lookback + 250 days
    """
    return int(
        (datetime.strptime(str(start), "%Y%m%d") - timedelta(days=buffer)).strftime("%Y%m%d")
    )
```

**Mistake 3: Wrong class/method names**
```python
# ❌ WRONG
class MyAlpha(BaseAlpha):
    def generate(self, start, end):  # Wrong method name!
        return positions  # Missing shift!

# ✅ CORRECT
class Alpha(BaseAlpha):
    def get(self, start: int, end: int, **kwargs) -> pd.DataFrame:
        return positions.shift(1)  # Correct!
```

**Mistake 4: Renaming DataFrame columns**
```python
# ❌ WRONG - Renaming columns breaks Simulator (can't match symbols)
nvda_id = '11776801'
aapl_id = '00169001'
close = cf.get_df("price_close")[[nvda_id, aapl_id]]
close.columns = ['NVDA', 'AAPL']  # NEVER do this!

# ✅ CORRECT - Keep Finter ID columns as-is
close = cf.get_df("price_close")[[nvda_id, aapl_id]]
# columns: ['11776801', '00169001'] - keep original IDs
positions = ...  # Same column structure required for Simulator
```

**Mistake 5: Date slicing without str() conversion**
```python
# ❌ WRONG - Integer dates don't work with DatetimeIndex.loc[]
return positions.shift(1).loc[start:end]  # KeyError or wrong results!

# ✅ CORRECT - Convert to string for DatetimeIndex slicing
return positions.shift(1).loc[str(start):str(end)]  # Works correctly!
```

## 📋 Workflow (DATA FIRST)

1. **Explore Data FIRST**: Load sample data in Jupyter, visualize, test library functions
2. **Analyze Patterns**: Check distributions, correlations, data quality
3. **Reference Examples**: Find closest template from `templates/examples/`
4. **Implement in Jupyter**: Write Alpha class based on data insights
5. **Validate Positions**: Run `validate_positions(positions)` to check format
6. **Backtest in Jupyter**: Run Simulator, record metrics
7. **Save alpha.py**: Save the implementation regardless of backtest results
8. **Run Scripts (MANDATORY)**: Execute backtest_runner, chart_generator, info_generator
9. **Report Results**: Summarize findings and let Fund Manager decide next steps

**⚠️ NEVER write Alpha class before exploring data!**
**⚠️ NEVER skip running scripts after saving alpha.py!**

**⛔ NO SELF-FEEDBACK RULE:**
- Complete ONE implementation cycle, then STOP
- Do NOT retry based on backtest results
- Do NOT judge if results are "good" or "poor"
- Report what you built and let Fund Manager evaluate

## 🎯 First Steps

### Read the Framework First
**BEFORE coding, read `references/framework.md`** - it explains:
- BaseAlpha class structure and requirements
- Position DataFrame format and constraints
- Data loading with buffer
- Complete minimal example

### Find Your Template
**Review `templates/examples/` for similar patterns:**
- **Momentum/Technical**: `examples/technical_analysis.py`
- **Multi-factor**: `examples/multi_factor.py`
- **Stock Selection**: `examples/stock_selection.py`
- **Bitcoin/Crypto (BETA)**: `examples/crypto_bitcoin.py`

**IMPORTANT**: Templates show COMPLETE working code. Copy and modify, don't write from scratch!

### Run Backtest in Jupyter
```python
# Step 1: Generate positions
alpha = Alpha()
positions = alpha.get(20200101, int(datetime.now().strftime("%Y%m%d")))

# Step 2: Run backtest
from finter.backtest import Simulator
simulator = Simulator(market_type="kr_stock")
result = simulator.run(position=positions)

# Step 3: Check results (use EXACT field names!)
stats = result.statistics
summary = result.summary

print(f"Total Return: {stats['Total Return (%)']:.2f}%")
print(f"Sharpe Ratio: {stats['Sharpe Ratio']:.2f}")
print(f"Max Drawdown: {stats['Max Drawdown (%)']:.2f}%")
print(f"Hit Ratio: {stats['Hit Ratio (%)']:.2f}%")

# Step 4: Turnover & Cost Analysis (MANDATORY)
# target_turnover is already a ratio (1.0 = 100% of AUM)
avg_daily_turnover = summary['target_turnover'].mean()
annual_turnover = avg_daily_turnover * 252  # Annualized turnover ratio
total_cost = summary['cost'].sum() + summary['slippage'].sum()
avg_aum = summary['aum'].mean()
cost_drag = (total_cost / avg_aum) * 100

print(f"Annual Turnover: {annual_turnover:.1%}")
print(f"Total Cost: {total_cost:,.0f}")
print(f"Cost Drag: {cost_drag:.2f}% of AUM")

# Step 5: Visualize NAV curve
summary['nav'].plot(title='NAV (starts at 1000)', figsize=(12,6))

# IMPORTANT:
# - NAV always starts at 1000 (not 1 or 1e8!)
# - DO NOT use 'Annual Return (%)' - it doesn't exist!
# - Turnover & Cost are ALREADY reflected in NAV (net return)
```

**Available `result.statistics` fields (18 total):**
| Field | Description |
|-------|-------------|
| `Total Return (%)` | Total portfolio return |
| `CAGR (%)` | Compound Annual Growth Rate |
| `Volatility (%)` | Annualized standard deviation |
| `Hit Ratio (%)` | % of profitable days |
| `Sharpe Ratio` | Risk-adjusted return |
| `Sortino Ratio` | Downside risk-adjusted return |
| `Max Drawdown (%)` | Largest peak-to-trough loss |
| `Mean Drawdown (%)` | Average drawdown |
| `Calmar Ratio` | Return / Max Drawdown |
| `Avg Tuw` | Average time underwater (days) |
| `Max Tuw` | Maximum time underwater (days) |
| `Skewness` | Return distribution skewness |
| `Kurtosis` | Return distribution kurtosis |
| `VaR 95% (%)` | 95% Value-at-Risk |
| `VaR 99% (%)` | 99% Value-at-Risk |
| `Positive HHI` | HHI for positive returns |
| `Negative HHI` | HHI for negative returns |
| `K Ratio` | Equity curve slope / std error |

See `references/api_reference.md` for complete Simulator API.

## 📚 Documentation

**Read these BEFORE coding:**
1. **`references/framework.md`** - BaseAlpha requirements (READ THIS FIRST!)
2. **`references/universe_reference.md`** - Available universes and data items (includes Crypto BETA)
3. **`references/api_reference.md`** - ContentFactory, Simulator API
4. **`references/troubleshooting.md`** - Common mistakes and fixes

**Reference during coding:**
- **`templates/examples/`** - 4 complete strategy examples (stocks + crypto)
- **`templates/patterns/`** - Reusable building blocks
- **`references/research_process.md`** - Validation and testing

**Pattern matching guide:**
- Technical/momentum strategy → `examples/technical_analysis.py`
- Combine multiple factors → `examples/multi_factor.py`
- Specific stocks only → `examples/stock_selection.py`
- Bitcoin/crypto strategy (BETA) → `examples/crypto_bitcoin.py`
- Equal weighting → `patterns/equal_weight.py`
- Top-K selection → `patterns/top_k_selection.py`
- Rolling rebalance → `patterns/rolling_rebalance.py`

## ⚡ Quick Reference

**Essential imports:**
```python
from finter import BaseAlpha
from finter.data import ContentFactory
from finter.backtest import Simulator
import pandas as pd
```

**Data Loading:**

> **SSOT:** For ContentFactory usage, data discovery, and Symbol search,
> see `finter-data` skill. Key points:
> - Use `cf.search()` to find data items - **ENGLISH ONLY** (Korean doesn't work)
> - Use `print(cf.search('keyword').to_string())` to see full results (default output truncates)
> - ALL parameters in ContentFactory constructor (NOT in get_df)
> - Use `get_df()` for market data, `get_fc()` for financial data

```python
# Quick example (see finter-data for full details)
cf = ContentFactory("us_stock", 20200101, int(datetime.now().strftime("%Y%m%d")))
print(cf.search('close').to_string())  # See all results without truncation
close = cf.get_df("price_close")  # Use get_df, not get!
```

**Supported Universes:**

| Universe | Assets | Key Differences |
|----------|--------|-----------------|
| kr_stock | ~2,500 | Full support, 1000+ data items |
| us_stock | ~8,000 | Full support, 1000+ data items |
| us_etf   | ~6,700 | Market data only |
| id_stock | ~1,000 | Use `volume_sum` not `trading_volume` |
| vn_stock | ~1,000 | **PascalCase**: `ClosePrice` not `price_close` |
| raw (crypto) | 1 (BTC only) | **No cf.search()**, 8H candles, see `universe_reference.md` |

**DO NOT SKIP** reading `references/framework.md` - it has critical rules!

## 🚀 FINAL STEPS (MANDATORY - After Backtest)

**⚠️ You MUST complete ALL these steps after saving alpha.py!**

### Step 1: Save alpha.py
Save final Alpha class to workspace using Write tool (NOT Jupyter).

### Step 2: Run Backtest Script
```bash
python .claude/skills/finter-alpha/scripts/backtest_runner.py --code alpha.py --universe kr_stock
```
- Includes validation (path independence, trading days index)
- If validation fails → fix alpha.py and re-run
- Generates: `backtest_summary.csv`, `backtest_stats.csv`

### Step 3: Generate Chart
```bash
python .claude/skills/finter-alpha/scripts/chart_generator.py --summary backtest_summary.csv --stats backtest_stats.csv
```
- Generates: `chart.png`

### Step 4: Generate Info
```bash
python .claude/skills/finter-alpha/scripts/info_generator.py \
    --title "Strategy Name" \
    --summary "One-line description of signal logic" \
    --category momentum \
    --universe kr_stock \
    --not-investable \
    --evaluation "Backtest completed" \
    --lessons "Implementation completed"
```
- **--title**: English only, max 34 chars
- **--summary**: OBJECTIVE description of signal (e.g., "20-day momentum, top 10% equal weight")
- **--category**: momentum|value|quality|growth|size|low_vol|technical|macro|stat_arb|event|ml|composite
- **--universe**: kr_stock|us_stock|vn_stock|id_stock|us_etf|btcusdt_spot_binance
- **--not-investable**: ALWAYS use this (Fund Manager decides investability)
- **--evaluation**: Just say "Backtest completed" (Fund Manager evaluates)
- **--lessons**: Just say "Implementation completed" (Fund Manager extracts lessons)
- Generates: `info.json`

### Step 5: Final Summary (FACTS ONLY)
Add ONE markdown cell with **OBJECTIVE FACTS ONLY**:

```markdown
## Results

| Metric | Value |
|--------|-------|
| Total Return | X% |
| Sharpe Ratio | X.XX |
| Max Drawdown | X% |
| Annual Turnover | X.Xx |
| Cost Drag | X.XX% |

## Implementation
- Universe: kr_stock
- Period: 20200101 - 20241210
- Signal: [brief description]
- Rebalancing: daily

## Files
- alpha.py
- backtest_stats.csv
- chart.png
- info.json
```

**⛔ DO NOT INCLUDE:**
- "Strategy failed/succeeded"
- "This works because..."
- "Suggested improvements..."
- "The reason for poor results..."
- Any subjective analysis or recommendations

**Fund Manager will evaluate results and provide feedback.**

**⚠️ Task is NOT complete until all 5 steps are done!**
