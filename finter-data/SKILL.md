---
name: finter-data
description: Data loading and preparation for Finter platform. Use when you need to load data, handle preprocessing, or work with different universes (e.g., "load kr_stock data", "handle missing values", "use Symbol search", "calculate ROE with financial data").
---

# Finter Data Preparation

Load and preprocess data from Finter platform for quantitative research.

## ⚠️ CRITICAL RULES (MUST FOLLOW)

**Data Discovery:**
1. **ALWAYS use `cf.search()` BEFORE `cf.get_df()`** - NEVER guess item names!
2. **Use `cf.usage()` for guidance** - Check general or item-specific usage
3. **Exception: Crypto (`raw` universe)** - search() doesn't work, use exact names from docs

**ContentFactory Usage:**
```python
# ✅ CORRECT - All parameters in constructor
cf = ContentFactory("kr_stock", 20230101, 20241231)
data = cf.get_df("price_close")

# ❌ WRONG - Parameters in get_df
cf = ContentFactory("kr_stock")
data = cf.get_df("price_close", 20230101, 20241231)  # NO!
```

**Method Selection:**
- **Market data** (price, volume): Use `get_df()` → pandas DataFrame
- **Financial data** (statements): Use `get_fc()` → FinancialCalculator (fluent API)

**Common Mistakes:**

**Mistake 1: Guessing item names**
```python
# ❌ WRONG - Guessing names
close = cf.get_df("closing_price")  # KeyError!

# ✅ CORRECT - Search first
results = cf.search("close")
print(results)  # ['price_close', 'adj_close', ...]
close = cf.get_df("price_close")  # Use exact name!
```

**Mistake 2: Ignoring NaN values**
```python
# ❌ WRONG - Using data without checking
close = cf.get_df("price_close")
returns = close.pct_change()  # May have NaN!

# ✅ CORRECT - Check and handle NaN
close = cf.get_df("price_close")
print(f"NaN ratio: {close.isna().sum().sum() / close.size:.2%}")
close_clean = close.ffill().bfill()  # Handle missing values
returns = close_clean.pct_change()
```

**Mistake 3: Not handling outliers**
```python
# ❌ WRONG - Raw data with extreme values
factor = cf.get_df("some_ratio")
positions = factor * 1e8  # Extreme positions!

# ✅ CORRECT - Handle outliers first
def winsorize(df, lower=0.01, upper=0.99):
    return df.clip(
        lower=df.quantile(lower, axis=1),
        upper=df.quantile(upper, axis=1),
        axis=0
    )

factor = cf.get_df("some_ratio")
factor_clean = winsorize(factor, 0.01, 0.99)
positions = factor_clean * 1e8  # Controlled positions
```

**Mistake 4: Saving figures**
```python
# ❌ WRONG - Causes API errors
import matplotlib.pyplot as plt
close.plot(figsize=(12, 6))
plt.savefig('plot.png')  # ERROR!

# ✅ CORRECT - Let Jupyter display automatically
close.plot(figsize=(12, 6))  # Displays inline, no save needed
```

## 📋 Workflow (DATA FIRST)

1. **Discovery**: Use `cf.search()` to find available data items
2. **Load**: Use ContentFactory with correct parameters
3. **Quality Check**: Inspect NaN, outliers, distributions
4. **Preprocess**: Handle missing values, outliers, normalization
5. **Feature Engineering**: Transform, rank, combine (if needed)
6. **Validate**: Verify data quality before using in alpha

**⚠️ NEVER skip quality checks!**

## 🎯 First Steps

### Read the Framework First
**BEFORE loading data, read `references/framework.md`** - it explains:
- ContentFactory API (search, get_df, get_fc, usage)
- Symbol search for company IDs
- Data quality principles
- Complete discovery workflow

### Know Your Data Type
**Choose the right method:**
- **Market data** (price, volume) → `get_df()` (see framework.md)
- **Financial data** (statements) → `get_fc()` (see financial_calculator.md)

### Review Preprocessing Patterns
**See `references/preprocessing.md` for:**
- Missing value strategies
- Outlier handling methods
- Normalization techniques

## 📚 Documentation

**Read these BEFORE coding:**
1. **`references/framework.md`** - ContentFactory API and data quality (READ THIS FIRST!)
2. **`references/financial_calculator.md`** - get_fc() for financial data (optional)
3. **`references/preprocessing.md`** - Preprocessing methods (SSOT)

**Reference during coding:**
- **`templates/examples/`** - Working examples

## ⚡ Quick Reference

**Essential imports:**
```python
from finter.data import ContentFactory, Symbol
import pandas as pd
```

**Discovery pattern:**
```python
cf = ContentFactory('kr_stock', 20230101, 20241231)

# Check usage first
cf.usage()  # General guide

# Search for items
results = cf.search('close')
print(results)  # ['price_close', 'adj_close', ...]

# For financial data, search with prefix
results = cf.search('krx-spot-sales')  # More specific!
print(results)  # ['krx-spot-sales', 'krx-spot-sales-annual', ...]

# Check categories
cf.summary()  # Shows: Economic, Financial, Market, ...
```

**Symbol search (find company ID):**
```python
symbol = Symbol('kr_stock')
result = symbol.search('삼성전자')
finter_id = result.index[0]  # 12170 (ID is in INDEX, not column!)
```

**Market data loading:**
```python
# Price and volume data
close = cf.get_df('price_close')
volume = cf.get_df('trading_volume')

# Returns pandas DataFrame (dates × stocks)
print(close.shape)  # (dates, stocks)
```

**Financial data loading:**
```python
# For financial statements, use get_fc()
fc = cf.get_fc({
    'income': 'krx-spot-owners_of_parent_net_income',
    'equity': 'krx-spot-owners_of_parent_equity'
})

# Fluent API for calculations
roe = (fc
    .apply_rolling(4, 'sum', variables=['income'])
    .apply_rolling(4, 'mean', variables=['equity'])
    .apply_expression('income / equity')
    .to_wide())  # Convert to pandas DataFrame

# IMPORTANT: Single expression → simple columns
#            No expression → MultiIndex columns (level=0: variable, level=1: stock_id)
#            Use .xs(stock_id, level=1, axis=1) to access specific stock

# See financial_calculator.md for details
```

**Quality checks:**
```python
# Check NaN
print(f"NaN ratio: {close.isna().sum().sum() / close.size:.2%}")

# Check distributions
print(close.describe())

# Check outliers
print(f"Min: {close.min().min()}, Max: {close.max().max()}")
```

**Visualization (IMPORTANT):**
```python
# NEVER set font family - causes errors in Jupyter environment
# ❌ WRONG
plt.rcParams['font.family'] = 'sans-serif'  # Will error!

# ✅ CORRECT - Use default settings
close.plot(figsize=(12, 6), title='Price History')  # Just plot!
close.hist(bins=50, figsize=(10, 6))
```

**Missing value handling:**
```python
# Forward fill + backward fill (most common)
clean = close.ffill().bfill()

# Forward fill only (for time series)
clean = close.ffill()

# Interpolation (for smooth data)
clean = close.interpolate(method='linear')
```

**Outlier handling:**
```python
# Winsorization (recommended)
def winsorize(df, lower=0.01, upper=0.99):
    """Clip to percentiles"""
    return df.clip(
        lower=df.quantile(lower, axis=1),
        upper=df.quantile(upper, axis=1),
        axis=0
    )

factor_clean = winsorize(factor, 0.01, 0.99)
```

**Normalization:**
```python
# Cross-sectional z-score (most common)
def zscore(df):
    """Normalize per timestamp"""
    return df.sub(df.mean(axis=1), axis=0).div(df.std(axis=1), axis=0)

normalized = zscore(factor)

# Cross-sectional rank (robust to outliers)
def rank_normalize(df):
    """Rank 0-1 per timestamp"""
    return df.rank(axis=1, pct=True)

ranked = rank_normalize(factor)
```

## 🔍 When to Use This Skill

**Use finter-data when:**
- ✅ Loading data from Finter (any universe, any data type)
- ✅ Discovering available data items
- ✅ Handling missing values or outliers
- ✅ Normalizing or transforming features
- ✅ Finding company IDs by name (Symbol search)
- ✅ Working with financial statements (get_fc)
- ✅ Checking data quality before analysis

**Don't use for:**
- ❌ Alpha strategy logic (use finter-alpha)
- ❌ Portfolio optimization (use finter-portfolio)
- ❌ Performance evaluation (use finter-evaluation)

**Workflow integration:**
- finter-data → **Load & preprocess data**
- finter-alpha → **Generate alpha signals**
- finter-evaluation → **Evaluate strategy**
- finter-portfolio → **Optimize portfolio**
