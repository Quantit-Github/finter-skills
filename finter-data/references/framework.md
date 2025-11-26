# Framework: Data Loading and Quality

Core concepts for loading and validating data from Finter.

## Overview

Finter provides data through:
1. **ContentFactory**: Main data loader with search and loading capabilities
2. **Symbol**: Company name to ID converter
3. **FinancialCalculator**: Financial statement calculator (for `get_fc()`)

**Key principle: Discover BEFORE load. NEVER guess item names.**

## ContentFactory API

### Initialization

```python
from finter.data import ContentFactory

cf = ContentFactory(universe, start, end)
```

**Parameters:**
- `universe`: 'kr_stock', 'us_stock', 'us_etf', 'id_stock', 'vn_stock', 'raw' (crypto)
- `start`: Start date (YYYYMMDD)
- `end`: End date (YYYYMMDD)

**CRITICAL: All parameters in constructor, NOT in get_df()!**

### Discovery Methods

#### cf.usage()

Shows general usage guide:

```python
cf.usage()
```

Returns:
- Basic usage patterns
- Available methods (get_df, get_fc, search, summary)
- FinancialCalculator examples
- Common parameters

**Use this FIRST** when starting with new universe or data type.

#### cf.usage(item_name)

Shows item-specific usage patterns:

```python
cf.usage('krx-spot-owners_of_parent_net_income')
```

Returns:
- Item-specific patterns
- Recommended operations (for financial items)
- Common use cases
- Example code

**Use this** when you know the item name and want to see best practices.

#### cf.search(query)

Searches for available items:

```python
# Search by keyword
results = cf.search('close')
# Returns: ['price_close', 'adj_close', ...]

results = cf.search('volume')
# Returns: ['trading_volume', ...]

# Search by prefix (for financial items)
results = cf.search('krx-spot')
# Returns all quarterly financial items

results = cf.search('owners_of_parent')
# Returns: ['krx-spot-owners_of_parent_net_income', 'krx-spot-owners_of_parent_equity', ...]
```

**Search strategies:**
- Use concept keywords: 'close', 'volume', 'income', 'equity'
- Use prefixes: 'krx-spot-' (Korean financial), 'price_', 'trading_'
- Use patterns: 'owners_of_parent', 'current_', 'operating_'

**CRITICAL: ALWAYS search() before get_df(). NO guessing!**

#### cf.summary()

Shows category breakdown:

```python
cf.summary()
```

Returns:
```
Content Model Summary:
----------------------------------------
Economic: 1 subcategories, 4 items
Event: 3 subcategories, 16 items
Financial: 2 subcategories, 288 items
Index: 1 subcategories, 68 items
Market: 7 subcategories, 102 items
Quantitative: 3 subcategories, 708 items
Unstructured: 12 subcategories, 162 items
```

**Use this** when search() returns empty or you want to explore categories.

### Data Loading Methods

#### get_df() - For Market Data

Use for price, volume, and most data items:

```python
# Single item
close = cf.get_df('price_close')  # Returns pandas DataFrame

# Multiple items (load separately)
close = cf.get_df('price_close')
volume = cf.get_df('trading_volume')
```

**Returns:** pandas DataFrame
- Index: dates (DatetimeIndex)
- Columns: Finter IDs (stock identifiers)
- Values: data values

**Use for:** Market data, quantitative factors, most items

#### get_fc() - For Financial Data

Use for quarterly financial statements:

```python
# Load with aliases
fc = cf.get_fc({
    'income': 'krx-spot-owners_of_parent_net_income',
    'equity': 'krx-spot-owners_of_parent_equity'
})

# Apply operations and convert to DataFrame
result = (fc
    .apply_rolling(4, 'sum', variables=['income'])
    .apply_expression('income / equity')
    .to_wide())  # Returns pandas DataFrame
```

**Returns:** FinancialCalculator (fluent API)
- Methods: `apply_rolling()`, `apply_expression()`, `filter()`, `to_wide()`
- Final: Convert to pandas DataFrame with `to_wide()`

**Use for:** Financial statements (income, balance sheet, cash flow)

**Why separate from get_df()?**
- Financial data is point-in-time (PIT) - released quarterly
- Needs rolling operations (TTM, averages)
- Requires date reindexing to trading days
- Benefits from fluent calculation API

See `financial_calculator.md` for complete get_fc() documentation.

## Symbol Search

Find company Finter IDs by name or ticker:

```python
from finter.data import Symbol

# Create Symbol instance
symbol = Symbol('kr_stock')

# Search by name
result = symbol.search('삼성전자')
print(result)
#           STK_CD       ISIN_CD STK_NM_KOR   STK_NM_ENG
# ccid
# 12170.0   005930  KR7005930003    삼성전자  SamsungElec
# ...

# Get Finter ID from INDEX (not column!)
finter_id = result.index[0]  # 12170.0
print(f"Samsung ID: {finter_id}")

# Use in data filtering
close = cf.get_df('price_close')
samsung_price = close[finter_id]
```

**Key points:**
- Returns pandas DataFrame
- **Finter ID is in the INDEX**, not a column
- Use `result.index[0]` to get the ID
- Returns multiple matches (sorted by relevance)
- Works with Korean name, English name, or ticker

## Data Quality Principles

### 1. Always Check NaN

```python
# Check NaN ratio
close = cf.get_df('price_close')
print(f"NaN ratio: {close.isna().sum().sum() / close.size:.2%}")
print(f"Stocks with NaN: {close.isna().any().sum()}")

# Visualize NaN pattern
import matplotlib.pyplot as plt
plt.figure(figsize=(12, 6))
plt.imshow(close.isna(), aspect='auto', cmap='gray')
plt.title('Missing Data Pattern')
plt.xlabel('Stocks')
plt.ylabel('Dates')
```

**Never use data without checking NaN first!**

### 2. Always Check Distributions

```python
# Summary statistics
print(close.describe())

# Histogram
close.iloc[-1].hist(bins=50, figsize=(10, 6))
plt.title('Latest Close Price Distribution')

# Check for extreme values
print(f"Min: {close.min().min()}, Max: {close.max().max()}")
```

### 3. Always Handle Outliers

Extreme values can distort signals:

```python
# Check for outliers
factor = cf.get_df('some_ratio')
print(f"99th percentile: {factor.quantile(0.99, axis=1).mean()}")
print(f"Max: {factor.max().max()}")

# If max >> 99th percentile, outliers present!
```

**See `preprocessing.md` for outlier handling methods.**

### 4. Avoid Look-ahead Bias

Don't use future data for current decisions:

```python
# ❌ WRONG - Using future data
close = cf.get_df('price_close')
future_return = close.shift(-1).pct_change()  # Looks ahead!
signal = (future_return > 0).astype(float)

# ✅ CORRECT - Using past data only
close = cf.get_df('price_close')
past_return = close.pct_change(20)  # 20-day historical return
signal = (past_return > 0).astype(float)
positions = signal.shift(1)  # Execute next day
```

## Complete Discovery Workflow

```python
from finter.data import ContentFactory, Symbol

# Step 1: Create ContentFactory
cf = ContentFactory('kr_stock', 20200101, int(datetime.now().strftime("%Y%m%d")))

# Step 2: Check usage guide
cf.usage()

# Step 3: Explore categories
cf.summary()

# Step 4: Search for data items
results = cf.search('close')
print(f"Found {len(results)} items")
print(results[:5])

# Step 5: Check item-specific usage
cf.usage('price_close')

# Step 6: Load data
close = cf.get_df('price_close')

# Step 7: Quality check
print(f"Shape: {close.shape}")
print(f"NaN ratio: {close.isna().sum().sum() / close.size:.2%}")
print(close.describe())

# Step 8: Visualize
close.plot(alpha=0.1, legend=False, figsize=(12, 6))

# Step 9: Find specific company (if needed)
symbol = Symbol('kr_stock')
samsung = symbol.search('삼성전자')
samsung_id = samsung.index[0]
samsung_price = close[samsung_id]
print(f"Samsung price: {samsung_price.tail()}")
```

## Universe-Specific Notes

### kr_stock / us_stock
- Standard naming: `price_close`, `trading_volume`
- Full financial data available
- cf.search() works well

### us_etf
- Market data only (price, volume)
- Limited fundamental data
- cf.search() works

### id_stock
- Different naming: `volume_sum` instead of `trading_volume`
- Use cf.search() to find correct names

### vn_stock
- PascalCase naming: `ClosePrice` instead of `price_close`
- Use cf.search() to find exact names

### raw (crypto)
- **cf.search() does NOT work!**
- Must use exact names from documentation
- 8H candles (not daily)
- Limited to specific pairs (e.g., btcusdt)

```python
# Crypto exception
cf = ContentFactory('raw', 20200101, int(datetime.now().strftime("%Y%m%d")))
# cf.search("btcusdt")  # Returns empty!

# Use exact name from docs
btc_price = cf.get_df('content.binance.api.price_volume.btcusdt-spot-price_close.8H')
```

## Visualization Best Practices

### CRITICAL: Font Settings

**NEVER set font family** - it causes errors in Jupyter environment:

```python
# ❌ WRONG - Will cause errors
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'sans-serif'  # ERROR!
plt.rcParams['font.sans-serif'] = ['Arial']  # ERROR!

# ✅ CORRECT - Use default settings
close.plot(figsize=(12, 6), title='Price History')  # Just plot!
```

**Reason:** Jupyter environment has pre-configured fonts. Changing them breaks rendering.

### Common Visualization Patterns

**Time series:**
```python
# Single series
close.plot(figsize=(12, 6), title='Price History')

# Multiple series (use alpha for transparency)
close.plot(alpha=0.3, figsize=(12, 6), legend=False)
```

**Distributions:**
```python
# Histogram
close.hist(bins=50, figsize=(10, 6))

# Latest cross-section
close.iloc[-1].hist(bins=50, figsize=(10, 6))
```

**Missing data pattern:**
```python
import matplotlib.pyplot as plt
plt.figure(figsize=(12, 6))
plt.imshow(close.isna(), aspect='auto', cmap='gray')
plt.title('Missing Data Pattern')
plt.xlabel('Stocks')
plt.ylabel('Dates')
```

## See Also

- `financial_calculator.md` - get_fc() API for financial data
- `preprocessing.md` - Data preprocessing methods
- `templates/examples/` - Working code examples
