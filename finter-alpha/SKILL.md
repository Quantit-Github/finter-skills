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
7. **Path independence**: Use `.expanding()` not `.mean()`/`.std()` — results must be identical for overlapping dates across different `start`/`end` calls

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
    """Subtract buffer days from start date correctly"""
    # Handles month/year boundaries properly
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

## 📋 Workflow (DATA FIRST)

1. **Explore Data FIRST**: Load sample data in Jupyter, visualize, test library functions
2. **Analyze Patterns**: Check distributions, correlations, data quality
3. **Reference Examples**: Find closest template from `templates/examples/`
4. **Implement in Jupyter**: Write Alpha class based on data insights
5. **Backtest in Jupyter**: Test with Simulator before saving
6. **Save alpha.py**: Only after successful backtest

**⚠️ NEVER write Alpha class before exploring data!**

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

**Data discovery (find item names):**
```python
# ✅ CORRECT - Search BEFORE using
results = cf.search("price")  # Find available items
print(results)  # ['price_close', 'price_open', 'price_high', ...]
close = cf.get_df("price_close")  # Use exact name from search!

# If search returns empty, check categories
cf.summary()  # Shows: Economic, Event, Financial, Market, ...
cf.search("ratio")  # Try related keywords
cf.search("per")    # Try abbreviations

# ❌ WRONG - Guessing item names
close = cf.get_df("closing_price")  # KeyError! Never guess!
per = cf.get_df("price_earnings")   # ALWAYS search() first!
```

**CRITICAL: Always search() BEFORE get_df(). NO guessing item names!**

**⚠️ Crypto exception:**
```python
# cf.search() does NOT work for 'raw' universe
cf = ContentFactory('raw', 20200101, int(datetime.now().strftime("%Y%m%d")))
cf.search("btcusdt")  # Returns empty! Must use exact names from docs
btc_price = cf.get_df('content.binance.api.price_volume.btcusdt-spot-price_close.8H')
```

**ContentFactory usage (CRITICAL):**
```python
# ✅ CORRECT - ALL parameters in constructor
cf = ContentFactory("us_stock", 20200101, int(datetime.now().strftime("%Y%m%d")))
open_price = cf.get_df("price_open")  # get_df, not get!
close_price = cf.get_df("price_close")

# ❌ WRONG - Parameters in get_df
cf = ContentFactory("us_stock")
open_price = cf.get_df("price_open", 20200101, int(datetime.now().strftime("%Y%m%d")))  # NO!

# ❌ WRONG - Using get instead of get_df
cf = ContentFactory("us_stock", 20200101, int(datetime.now().strftime("%Y%m%d")))
open_price = cf.get("price_open")  # NO! Use get_df!
```

**Symbol search (for specific stocks):**
```python
from finter.data import Symbol
symbol = Symbol("us_stock")  # Create instance first
result = symbol.search("palantir")  # Returns DataFrame!

# FINTER ID is in the INDEX (not column!)
finter_id = result.index[0]  # Get FINTER ID from index
print(f"FINTER ID: {finter_id}")
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

**All use same framework** (BaseAlpha, ContentFactory, Simulator, Symbol). **Always use `cf.search()` and `cf.summary()`** to explore data!

**DO NOT SKIP** reading `references/framework.md` - it has critical rules!
