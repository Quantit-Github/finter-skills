# FinancialCalculator API Reference

API reference for working with quarterly financial statement data using get_fc().

## Overview

FinancialCalculator provides a fluent API for:
1. Loading multiple financial items with aliases
2. Applying rolling operations (TTM, averages)
3. Calculating ratios and expressions
4. Filtering specific companies
5. Converting to wide format (pandas DataFrame)

**When to use:** Quarterly financial statements (income, balance sheet, cash flow)

**When NOT to use:** Market data (price, volume) → use `get_df()` instead

## cf.get_fc()

Load financial items with aliases for calculation.

### Signature

```python
fc = cf.get_fc(item_name: str | dict, **kwargs) -> FinancialCalculator
```

### Parameters

**Single item:**
```python
fc = cf.get_fc('krx-spot-owners_of_parent_net_income')
```

**Multiple items (recommended):**
```python
fc = cf.get_fc({
    'alias1': 'full-item-name-1',
    'alias2': 'full-item-name-2',
})
```

**Why use dict with aliases?**
- Shorter names in expressions: `'income / equity'` vs `'krx-spot-owners_of_parent_net_income / krx-spot-owners_of_parent_equity'`
- Clearer code intent
- Auto-join multiple items on (id, pit, fiscal)

### Returns

FinancialCalculator object with methods:
- `apply_rolling()` - Rolling window operations
- `apply_expression()` - Calculate ratios
- `filter()` - Filter specific companies
- `to_wide()` - Convert to pandas DataFrame
- Direct polars methods: `sort()`, `select()`, etc.

## fc.apply_rolling()

Apply rolling window operations for TTM calculations or averages.

### Signature

```python
fc.apply_rolling(
    quarters: int,
    operation: str,
    variables: list[str] | None = None
) -> FinancialCalculator
```

### Parameters

- `quarters`: Window size (4 = TTM, 0 = latest)
- `operation`: 'sum', 'mean', 'diff', 'last'
- `variables`: **REQUIRED** when multiple columns exist

### Operations

| Operation | Description | Common Use |
|-----------|-------------|------------|
| `'sum'` | Sum over N quarters | TTM revenue, TTM income |
| `'mean'` | Average over N quarters | Average equity, average assets |
| `'diff'` | Current - N quarters ago | YoY change |
| `'last'` | Latest quarter (quarters=0) | Latest balance sheet |

### Examples

**TTM (Trailing Twelve Months):**
```python
fc = cf.get_fc({
    'income': 'krx-spot-owners_of_parent_net_income',
    'sales': 'krx-spot-sales'
})

ttm = fc.apply_rolling(4, 'sum', variables=['income', 'sales'])
```

**Average balance sheet:**
```python
fc = cf.get_fc({
    'equity': 'krx-spot-owners_of_parent_equity',
    'assets': 'krx-spot-total_assets'
})

avg = fc.apply_rolling(4, 'mean', variables=['equity', 'assets'])
```

**Selective rolling (different operations):**
```python
fc = cf.get_fc({
    'income': 'krx-spot-owners_of_parent_net_income',
    'equity': 'krx-spot-owners_of_parent_equity'
})

# TTM income, average equity
result = (fc
    .apply_rolling(4, 'sum', variables=['income'])
    .apply_rolling(4, 'mean', variables=['equity'])
)
```

## fc.apply_expression()

Calculate ratios using column aliases.

### Signature

```python
fc.apply_expression(expression: str) -> FinancialCalculator
```

### Parameters

- `expression`: Python expression using column aliases

### Examples

**Simple ratio:**
```python
fc = cf.get_fc({
    'income': 'krx-spot-owners_of_parent_net_income',
    'equity': 'krx-spot-owners_of_parent_equity'
})

roe = fc.apply_expression('income / equity')
```

**Complex expression:**
```python
fc = cf.get_fc({
    'income': 'krx-spot-owners_of_parent_net_income',
    'sales': 'krx-spot-sales',
    'assets': 'krx-spot-total_assets',
    'equity': 'krx-spot-owners_of_parent_equity'
})

# DuPont: (income/sales) * (sales/assets) * (assets/equity)
dupont = fc.apply_expression('(income / sales) * (sales / assets) * (assets / equity)')
```

## fc.filter()

Filter for specific companies using Polars expressions.

### Signature

```python
fc.filter(condition) -> polars.DataFrame
```

**Note: Returns Polars DataFrame, not FinancialCalculator!**

### Examples

**Single company:**
```python
import polars as pl

samsung = fc.filter(pl.col('id') == 12170)
print(samsung)  # Polars DataFrame (long format)
```

**Multiple companies:**
```python
companies = fc.filter(pl.col('id').is_in([12170, 10642]))
```

## fc.to_wide()

Convert to pandas DataFrame (dates × stocks) for Alpha usage.

### Signature

```python
fc.to_wide() -> pd.DataFrame
```

### Returns

Pandas DataFrame with:
- Index: Trading dates (daily)
- **Columns: Depends on whether expression was applied**
  - **With expression**: Simple Int64Index (Finter IDs)
  - **Without expression**: MultiIndex (variable name, Finter ID)
- Values: Calculated values, forward-filled to trading dates

### Column Structure

**Case 1: Single expression applied**
```python
fc = cf.get_fc({
    'income': 'krx-spot-owners_of_parent_net_income',
    'equity': 'krx-spot-owners_of_parent_equity'
})

roe = (fc
    .apply_rolling(4, 'sum', variables=['income'])
    .apply_rolling(4, 'mean', variables=['equity'])
    .apply_expression('income / equity')  # ← Expression applied!
)

roe_df = roe.to_wide()

print(roe_df.columns)  # Int64Index([12170, 12171, ...])  ← Simple!
samsung_roe = roe_df[12170]  # Direct access ✅
```

**Case 2: No expression (multiple variables)**
```python
fc = cf.get_fc({
    'income': 'krx-spot-owners_of_parent_net_income',
    'equity': 'krx-spot-owners_of_parent_equity'
})

result = (fc
    .apply_rolling(4, 'sum', variables=['income'])
    .apply_rolling(4, 'mean', variables=['equity'])
    # No expression! ← Multiple variables remain
)

result_df = result.to_wide()

print(result_df.columns)  # MultiIndex([('income', 12170), ('equity', 12170), ...])
# Access specific stock - use .xs()!
samsung_data = result_df.xs(12170, level=1, axis=1)  # ✅
print(samsung_data.columns)  # Index(['income', 'equity'])
```

### Examples

**Example 1: With expression (simple columns)**
```python
fc = cf.get_fc({
    'income': 'krx-spot-owners_of_parent_net_income',
    'equity': 'krx-spot-owners_of_parent_equity'
})

roe = (fc
    .apply_rolling(4, 'sum', variables=['income'])
    .apply_rolling(4, 'mean', variables=['equity'])
    .apply_expression('income / equity')
)

roe_df = roe.to_wide()

print(roe_df.shape)  # (dates, stocks)
print(roe_df.index)  # DatetimeIndex (daily)
print(roe_df.columns)  # Int64Index (Finter IDs)  ← Simple!

# Use in Alpha
positions = roe_df.rank(axis=1, pct=True) * 1e8
```

**Example 2: Without expression (MultiIndex columns)**
```python
fc = cf.get_fc({
    'income': 'krx-spot-owners_of_parent_net_income',
    'sales': 'krx-spot-sales'
})

ttm = fc.apply_rolling(4, 'sum', variables=['income', 'sales'])
ttm_df = ttm.to_wide()

print(ttm_df.columns)  # MultiIndex: [(income, 12170), (income, 12171), (sales, 12170), ...]

# Access specific stock across all variables
samsung_id = 12170
samsung_data = ttm_df.xs(samsung_id, level=1, axis=1)
print(samsung_data.columns)  # Index(['income', 'sales'])
print(samsung_data['income'])  # Samsung's TTM income
print(samsung_data['sales'])   # Samsung's TTM sales
```

## Common Financial Patterns

### ROE (Return on Equity)

```python
roe = (cf.get_fc({
    'income': 'krx-spot-owners_of_parent_net_income',
    'equity': 'krx-spot-owners_of_parent_equity'
})
    .apply_rolling(4, 'sum', variables=['income'])
    .apply_rolling(4, 'mean', variables=['equity'])
    .apply_expression('income / equity')
    .to_wide())
```

### Operating Margin

```python
margin = (cf.get_fc({
    'oi': 'krx-spot-operating_income',
    'sales': 'krx-spot-sales'
})
    .apply_rolling(4, 'sum', variables=['oi', 'sales'])
    .apply_expression('oi / sales')
    .to_wide())
```

### Current Ratio (no rolling)

```python
current_ratio = (cf.get_fc({
    'ca': 'krx-spot-current_assets',
    'cl': 'krx-spot-current_liabilities'
})
    .apply_expression('ca / cl')
    .to_wide())
```

### Asset Turnover

```python
turnover = (cf.get_fc({
    'sales': 'krx-spot-sales',
    'assets': 'krx-spot-total_assets'
})
    .apply_rolling(4, 'sum', variables=['sales'])
    .apply_rolling(4, 'mean', variables=['assets'])
    .apply_expression('sales / assets')
    .to_wide())
```

## Workflow Summary

```python
# 1. Load with aliases
fc = cf.get_fc({
    'alias1': 'item-name-1',
    'alias2': 'item-name-2'
})

# 2. Apply rolling (if needed)
fc = fc.apply_rolling(4, 'sum', variables=['alias1'])
fc = fc.apply_rolling(4, 'mean', variables=['alias2'])

# 3. Calculate ratio
fc = fc.apply_expression('alias1 / alias2')

# 4. Filter (optional, for inspection)
import polars as pl
filtered = fc.filter(pl.col('id') == 12170)

# 5. Convert to wide for Alpha
result_df = fc.to_wide()

# 6. Use in Alpha
positions = result_df.rank(axis=1, pct=True) * 1e8
```

## See Also

- `framework.md` - ContentFactory basics
- `templates/examples/` - Financial ratio examples
