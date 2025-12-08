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
# ❌ WRONG - Column 이름을 바꾸면 Simulator가 종목을 인식 못함
nvda_id = '11776801'
aapl_id = '00169001'
close = cf.get_df("price_close")[[nvda_id, aapl_id]]
close.columns = ['NVDA', 'AAPL']  # 절대 금지!

# ✅ CORRECT - Finter ID(column)를 그대로 유지
close = cf.get_df("price_close")[[nvda_id, aapl_id]]
# columns: ['11776801', '00169001'] 그대로 사용
positions = ...  # 동일한 column 구조 유지해야 Simulator 작동
```

## 📋 Workflow (DATA FIRST)

1. **Explore Data FIRST**: Load sample data in Jupyter, visualize, test library functions
2. **Analyze Patterns**: Check distributions, correlations, data quality
3. **Reference Examples**: Find closest template from `templates/examples/`
4. **Implement in Jupyter**: Write Alpha class based on data insights
5. **Validate Positions**: Run `validate_positions(positions)` — **⛔ 실패 시 4번으로 돌아가서 수정**
6. **Backtest in Jupyter**: Run Simulator, check metrics — **⛔ 결과 불량 시 4번으로 돌아가서 수정**
7. **Save alpha.py**: Only after validation & backtest 모두 성공

**⚠️ NEVER write Alpha class before exploring data!**
**⚠️ NEVER save alpha.py if validation fails or backtest results are poor!**

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
print(f"Total Return: {stats['Total Return (%)']:.2f}%")
print(f"Sharpe Ratio: {stats['Sharpe Ratio']:.2f}")
print(f"Max Drawdown: {stats['Max Drawdown (%)']:.2f}%")
print(f"Hit Ratio: {stats['Hit Ratio (%)']:.2f}%")

# Step 4: Visualize NAV curve
result.summary['nav'].plot(title='NAV (starts at 1000)', figsize=(12,6))

# IMPORTANT:
# - NAV always starts at 1000 (not 1 or 1e8!)
# - DO NOT use 'Annual Return (%)' - it doesn't exist!
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
> - Use `search_cm` MCP tool FIRST to find data items
> - ALL parameters in ContentFactory constructor (NOT in get_df)
> - Use `get_df()` for market data, `get_fc()` for financial data

```python
# Quick example (see finter-data for full details)
cf = ContentFactory("us_stock", 20200101, int(datetime.now().strftime("%Y%m%d")))
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
