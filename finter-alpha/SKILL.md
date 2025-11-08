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
5. **Position constraints**: Row sums ≤ 1e8 (total AUM)

**Common Mistakes:**
```python
# ❌ WRONG class/method names
class MyAlpha(BaseAlpha):
    def generate(self, start, end):  # Wrong method name!
        return positions  # Missing shift!

# ✅ CORRECT
class Alpha(BaseAlpha):
    def get(self, start: int, end: int, **kwargs) -> pd.DataFrame:
        # ... your logic ...
        return positions.shift(1)  # CRITICAL: Always shift!
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

**IMPORTANT**: Templates show COMPLETE working code. Copy and modify, don't write from scratch!

### Run Backtest in Jupyter
```python
# Step 1: Generate positions
alpha = Alpha()
positions = alpha.get(20240101, 20241231)

# Step 2: Run backtest
from finter.backtest import Simulator
simulator = Simulator(market_type="kr_stock")
result = simulator.run(position=positions)

# Step 3: Check results (use EXACT field names!)
stats = result.statistics
print(f"Total Return: {stats['Total Return (%)']:.2f}%")
print(f"Sharpe Ratio: {stats['Sharpe Ratio']:.2f}")
print(f"Max Drawdown: {stats['Max Drawdown (%)']:.2f}%")
print(f"Win Rate: {stats['Win Rate (%)']:.2f}%")

# IMPORTANT: DO NOT use 'Annual Return (%)' - it doesn't exist!
```

See `references/api_reference.md` for complete Simulator API.

## 📚 Documentation

**Read these BEFORE coding:**
1. **`references/framework.md`** - BaseAlpha requirements (READ THIS FIRST!)
2. **`references/api_reference.md`** - ContentFactory, Simulator, data access
3. **`references/troubleshooting.md`** - Common mistakes and fixes

**Reference during coding:**
- **`templates/examples/`** - 3 complete strategy examples
- **`templates/patterns/`** - Reusable building blocks
- **`references/research_process.md`** - Validation and testing

**Pattern matching guide:**
- Technical/momentum strategy → `examples/technical_analysis.py`
- Combine multiple factors → `examples/multi_factor.py`
- Specific stocks only → `examples/stock_selection.py`
- Equal weighting → `patterns/equal_weight.py`
- Top-K selection → `patterns/top_k_selection.py`

## ⚡ Quick Reference

**Essential imports:**
```python
from finter import BaseAlpha
from finter.data import ContentFactory
from finter.backtest import Simulator
import pandas as pd
```

**ContentFactory usage (CRITICAL):**
```python
# ✅ CORRECT - ALL parameters in constructor
cf = ContentFactory("us_stock", 20230101, 20241231)
open_price = cf.get_df("price_open")  # get_df, not get!
close_price = cf.get_df("price_close")

# ❌ WRONG - Parameters in get_df
cf = ContentFactory("us_stock")
open_price = cf.get_df("price_open", 20230101, 20241231)  # NO!

# ❌ WRONG - Using get instead of get_df
cf = ContentFactory("us_stock", 20230101, 20241231)
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

**DO NOT SKIP** reading `references/framework.md` - it has critical rules!
