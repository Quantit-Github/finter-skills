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

---

## Common API

### cf.get_fc()

Load financial items with aliases for calculation.

```python
fc = cf.get_fc(item_name: str | dict, **kwargs) -> FinancialCalculator
```

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

### fc.apply_rolling()

Apply rolling window operations for TTM calculations or averages.

```python
fc.apply_rolling(
    quarters: int,
    operation: str,
    variables: list[str] | None = None
) -> FinancialCalculator
```

**Parameters:**
- `quarters`: Window size (4 = TTM, 0 = latest)
- `operation`: 'sum', 'mean', 'diff', 'last'
- `variables`: **REQUIRED** when multiple columns exist

| Operation | Description | Common Use |
|-----------|-------------|------------|
| `'sum'` | Sum over N quarters | TTM revenue, TTM income |
| `'mean'` | Average over N quarters | Average equity, average assets |
| `'diff'` | Current - N quarters ago | YoY change |
| `'last'` | Latest quarter (quarters=0) | Latest balance sheet |

### fc.apply_expression()

Calculate ratios using column aliases.

```python
fc.apply_expression(expression: str) -> FinancialCalculator
```

**Example:**
```python
roe = fc.apply_expression('income / equity')
```

### fc.filter()

Filter for specific companies using Polars expressions.

```python
fc.filter(condition) -> polars.DataFrame
```

**Note:** Returns Polars DataFrame, not FinancialCalculator!

```python
import polars as pl
samsung = fc.filter(pl.col('id') == 12170)
```

### fc.to_wide()

Convert to pandas DataFrame (dates × stocks) for Alpha usage.

```python
fc.to_wide() -> pd.DataFrame
```

**Returns:** Pandas DataFrame with:
- Index: Trading dates (daily)
- Columns: Depends on whether expression was applied
  - **With expression**: Simple Int64Index (Finter IDs)
  - **Without expression**: MultiIndex (variable name, Finter ID)
- Values: Calculated values, forward-filled to trading dates

**Column behavior:**

| Scenario | Column Type | Access Pattern |
|----------|-------------|----------------|
| After `apply_expression()` | Simple index | `df[12170]` |
| Multiple variables, no expression | MultiIndex | `df.xs(12170, level=1, axis=1)` |

---

## kr_stock Patterns

### Search Prefix: `krx-spot-`

For kr_stock financial data, search with `krx-spot-` prefix:

```python
cf = ContentFactory('kr_stock', 20200101, 20241201)

# Search financial items
results = cf.search('krx-spot-')
# Returns: ['krx-spot-sales', 'krx-spot-operating_income', ...]

results = cf.search('krx-spot-owners')
# Returns: ['krx-spot-owners_of_parent_net_income', 'krx-spot-owners_of_parent_equity', ...]
```

### Common Items

| Item | Description |
|------|-------------|
| `krx-spot-sales` | Revenue |
| `krx-spot-operating_income` | Operating income |
| `krx-spot-owners_of_parent_net_income` | Net income (parent) |
| `krx-spot-owners_of_parent_equity` | Equity (parent) |
| `krx-spot-total_assets` | Total assets |
| `krx-spot-current_assets` | Current assets |
| `krx-spot-current_liabilities` | Current liabilities |

### Examples

**ROE (Return on Equity):**
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

**Operating Margin:**
```python
margin = (cf.get_fc({
    'oi': 'krx-spot-operating_income',
    'sales': 'krx-spot-sales'
})
    .apply_rolling(4, 'sum', variables=['oi', 'sales'])
    .apply_expression('oi / sales')
    .to_wide())
```

**Current Ratio (no rolling):**
```python
current_ratio = (cf.get_fc({
    'ca': 'krx-spot-current_assets',
    'cl': 'krx-spot-current_liabilities'
})
    .apply_expression('ca / cl')
    .to_wide())
```

---

## us_stock Patterns

### Search Prefix: `pit-`

For us_stock financial data, search with `pit-` prefix:

```python
cf = ContentFactory('us_stock', 20200101, 20241201)

# Search financial items
results = cf.search('pit-')
# Returns: ['pit-saleq', 'pit-niq', 'pit-atq', ...]

results = cf.search('pit-sale')
# Returns: ['pit-saleq', ...]
```

**Note:** `pit-` prefix items automatically use `mode='original'` to preserve fiscal information.

### ID System: gvkey vs gvkeyiid

| Term | Description | Example |
|------|-------------|---------|
| gvkey | Company ID (6-digit) | 001004 |
| gvkeyiid | Security ID (8-digit) | 00100401 |
| iid | Security identifier (2-digit) | 01 |

Relation: `gvkeyiid = gvkey + iid`

**Data by ID type:**

| Data Type | Method | ID Format |
|-----------|--------|-----------|
| Price/Market data | `get_df()` | gvkeyiid (8-digit) |
| Financial data | `get_fc()` | gvkey (6-digit) |

### Automatic ID Conversion

`to_wide()` automatically converts gvkey to gvkeyiid for us_stock:

```python
fc = cf.get_fc('pit-saleq')
df = fc.to_wide()  # Columns are gvkeyiid (8-digit)
print(df.columns[:3])  # ['00130001', '00104501', ...]
```

### Manual ID Conversion: to_security()

For `get_df()` data, use `cf.to_security()`:

```python
# Financial data via get_df (6-digit gvkey)
df = cf.get_df('saleq')
print(df.columns[:3])  # ['001004', '001045', ...]

# Convert to gvkeyiid (1:N broadcast)
df_security = cf.to_security(df)
print(df_security.columns[:3])  # ['00100401', '00104501', ...]
```

**Note:** `to_security()` is us_stock only. Raises ValueError for other universes.

### Common Items

| Item | Description |
|------|-------------|
| `pit-saleq` | Quarterly revenue |
| `pit-niq` | Quarterly net income |
| `pit-atq` | Total assets |
| `pit-seqq` | Stockholders equity |
| `pit-cogsq` | Cost of goods sold |

### Examples

**ROE:**
```python
roe = (cf.get_fc({
    'income': 'pit-niq',
    'equity': 'pit-seqq'
})
    .apply_rolling(4, 'sum', variables=['income'])
    .apply_rolling(4, 'mean', variables=['equity'])
    .apply_expression('income / equity')
    .to_wide())
```

**Gross Margin:**
```python
margin = (cf.get_fc({
    'sales': 'pit-saleq',
    'cogs': 'pit-cogsq'
})
    .apply_rolling(4, 'sum', variables=['sales', 'cogs'])
    .apply_expression('(sales - cogs) / sales')
    .to_wide())
```

---

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

- `framework.md` - ContentFactory basics, get_df() API
- `templates/examples/` - Financial ratio examples
