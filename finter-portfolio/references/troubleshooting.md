# Troubleshooting Portfolio Development

Common issues, error messages, and solutions when developing portfolio strategies.

---

## Weight Sum Issues

### Problem: Weights Don't Sum to 1.0

**Symptoms:**
```python
weights.sum(axis=1).describe()
# mean: 0.5  ← Should be ~1.0!
# or
# mean: 3.2  ← Should be ~1.0!
```

**Causes & Solutions:**

#### Cause 1: Forgot to Normalize

```python
# ❌ WRONG
inv_volatility = 1 / volatility_df
return inv_volatility.shift(1).loc[str(start):str(end)]  # Not normalized!

# ✅ CORRECT
inv_volatility = 1 / volatility_df
weights = inv_volatility.div(inv_volatility.sum(axis=1), axis=0)  # Normalize!
return weights.shift(1).loc[str(start):str(end)]
```

#### Cause 2: NaN in Denominator

```python
# ❌ WRONG - If all values are NaN, sum is 0, division fails
weights = inv_volatility.div(inv_volatility.sum(axis=1), axis=0)

# ✅ CORRECT - Handle NaN explicitly
weights = inv_volatility.div(inv_volatility.sum(axis=1), axis=0)
weights = weights.fillna(1.0 / len(self.alpha_list))  # Equal weight as fallback
```

#### Cause 3: After Shift, First Row is NaN

```python
# After shift(1), first row will be NaN
weights = weights.shift(1)
# First row sum will be 0, not 1.0!

# Solution: Check after slicing
weights_sliced = weights.loc[str(start):str(end)]
# If first row is NaN:
weights_sliced = weights_sliced.fillna(method='bfill', limit=1)
```

---

## NaN in Weights

### Problem: Final Weights Contain NaN

**Symptoms:**
```python
weights.isna().any().any()  # True ← Should be False!
```

**Causes & Solutions:**

#### Cause 1: Insufficient Buffer

```python
# ❌ WRONG - Not enough historical data
def weight(self, start, end):
    alpha_return_df = self.alpha_pnl_df('us_stock', start, end)
    volatility = alpha_return_df.rolling(126).std()  # First 126 rows are NaN!

# ✅ CORRECT - Load with buffer
def weight(self, start, end):
    preload_start = calculate_previous_start_date(start, 365)
    alpha_return_df = self.alpha_pnl_df('us_stock', preload_start, end)
    volatility = alpha_return_df.rolling(126).std()  # Sufficient data!
```

#### Cause 2: Division by Zero

```python
# ❌ WRONG - Zero volatility → NaN
inv_volatility = 1 / volatility_df  # If volatility is 0 → inf → NaN

# ✅ CORRECT - Handle zero volatility
adjusted_volatility = volatility_df.replace(0, np.nan)
inv_volatility = 1 / adjusted_volatility
```

#### Cause 3: All Alphas Have NaN on Same Date

```python
# If all alphas are NaN on a date, normalization fails
# ✅ CORRECT - Fill NaN before normalization
weights = inv_volatility.div(inv_volatility.sum(axis=1), axis=0)
weights = weights.fillna(0)  # or fillna(1.0 / len(self.alpha_list))
```

---

## Look-Ahead Bias

### Problem: Using Future Data in Weights

**How to Detect:**
- Weights change on same day as alpha returns
- Backtest performance too good to be true
- Missing shift(1) in code

**Common Mistakes:**

#### Mistake 1: Forgot shift(1)

```python
# ❌ WRONG - Using today's return to calculate today's weight
rolling_return = alpha_return_df.rolling(20).mean()
return rolling_return.loc[str(start):str(end)]  # Look-ahead bias!

# ✅ CORRECT - Use yesterday's return to calculate today's weight
rolling_return = alpha_return_df.rolling(20).mean()
return rolling_return.shift(1).loc[str(start):str(end)]
```

#### Mistake 2: Shift Applied After Slicing

```python
# ❌ WRONG - Shift after slicing doesn't help
weights = calculate_weights(...)
weights_sliced = weights.loc[str(start):str(end)]
return weights_sliced.shift(1)  # Too late! First row is lost!

# ✅ CORRECT - Shift before slicing
weights = calculate_weights(...)
return weights.shift(1).loc[str(start):str(end)]
```

#### Mistake 3: Shift Not Needed for Static Weights

```python
# ✓ CORRECT - Equal weight doesn't use returns, no shift needed
n_alphas = len(self.alpha_list)
weights = pd.DataFrame(1.0 / n_alphas, index=dates, columns=alphas)
return weights.loc[str(start):str(end)]  # No shift needed!
```

**When to shift?**
- ✅ **Return-based weights** → MUST shift(1)
- ⚠️ **Volatility/stats weights** → Recommended shift(1) for safety
- ❌ **Static weights** → No shift needed

---

## Data Issues

### Problem: Consecutive 1's Not Handled

**Symptoms:**
- Volatility too low
- Correlation too high
- Risk parity weights heavily skewed

**Solution:**

```python
# ✅ ALWAYS clean consecutive 1's before calculations
alpha_return_df = self.alpha_pnl_df('us_stock', preload_start, end)

# Clean consecutive 1's
find_1 = (alpha_return_df == 1) & (alpha_return_df.shift(1) == 1)
alpha_return_df = alpha_return_df.mask(find_1, np.nan).ffill(limit=5)

# Now calculate metrics
volatility = alpha_return_df.rolling(126).std()
```

### Problem: Wrong Return Convention

**Symptoms:**
- Returns look wrong (should be near 1.0, but showing near 0.0)
- Calculations give unexpected results

**Cause:**
Alpha returns use 1.0 as baseline, not 0.0

```python
# Alpha return format:
# 1.0 = 0% return (no change)
# 1.01 = +1% return
# 0.99 = -1% return

# If you need 0-baseline returns:
standard_returns = alpha_return_df - 1.0

# Convert back to 1-baseline:
alpha_returns = standard_returns + 1.0
```

---

## Class/Method Name Issues

### Problem: Portfolio Not Recognized

**Symptoms:**
- "Portfolio class not found"
- "weight method not found"

**Causes & Solutions:**

#### Cause 1: Wrong Class Name

```python
# ❌ WRONG
class MyPortfolio(BasePortfolio):
    pass

# ✅ CORRECT
class Portfolio(BasePortfolio):
    pass
```

#### Cause 2: Wrong Method Name

```python
# ❌ WRONG
def get_weights(self, start, end):
    pass

# ❌ WRONG
def calculate(self, start, end):
    pass

# ✅ CORRECT
def weight(self, start, end):
    pass
```

#### Cause 3: Missing alpha_list

```python
# ❌ WRONG - No alpha_list defined
class Portfolio(BasePortfolio):
    def weight(self, start, end):
        pass

# ✅ CORRECT
class Portfolio(BasePortfolio):
    alpha_list = [
        "us.compustat.stock.user.alpha1",
        "us.compustat.stock.user.alpha2"
    ]

    def weight(self, start, end):
        pass
```

---

## Date Range Issues

### Problem: Weights Outside Requested Range

**Symptoms:**
```python
# Requested: 20240101 to 20241231
# Got: 20230101 to 20241231 ← Wrong!
```

**Solution:**

```python
# ❌ WRONG - Returning entire dataset
def weight(self, start, end):
    weights = calculate_weights(...)
    return weights.shift(1)  # Doesn't filter date range!

# ✅ CORRECT - Filter to requested range
def weight(self, start, end):
    weights = calculate_weights(...)
    return weights.shift(1).loc[str(start):str(end)]  # Filter!
```

### Problem: First Date Has NaN After Shift

**Cause:**
shift(1) moves all data down by one row, so first row becomes NaN

**Solution:**

```python
# Option 1: Acceptable if only first row (expected behavior)
# No action needed - this is correct for dynamic weights

# Option 2: Backfill first row only
weights_sliced = weights.shift(1).loc[str(start):str(end)]
weights_sliced.iloc[0] = weights.loc[str(start)].iloc[0]  # Use non-shifted first row
return weights_sliced
```

---

## Performance Issues

### Problem: Optimization Takes Too Long

**Symptoms:**
- Mean-variance optimization runs for minutes
- Timeout errors

**Solutions:**

#### Solution 1: Reduce Lookback Window

```python
# Instead of 252 days (1 year)
lookback = 126  # 6 months (faster)
```

#### Solution 2: Use Simpler Method First

```python
# Instead of complex optimization:
# Try risk parity or equal weight first
```

#### Solution 3: Rebalance Less Frequently

```python
# Instead of daily rebalancing:
# - Weekly: Only calculate weights on Mondays
# - Monthly: Only calculate on first trading day of month
```

---

## Validation Errors

### Problem: Weights Out of Range

**Symptoms:**
```python
weights.min().min()  # -0.5 ← Negative weights!
weights.max().max()  # 2.0  ← Weights > 1!
```

**Causes & Solutions:**

#### Cause 1: No Long-Only Constraint

```python
# In optimization, add bounds:
bounds = tuple((0, 1) for _ in range(n))  # Long-only, max 100%
```

#### Cause 2: Normalization After Clipping

```python
# ❌ WRONG - Clip after normalization
weights = calculate_weights(...).clip(lower=0, upper=1)  # Breaks sum=1!

# ✅ CORRECT - Normalize after clipping
weights_raw = calculate_weights(...)
weights_clipped = weights_raw.clip(lower=0)  # Remove negative
weights = weights_clipped.div(weights_clipped.sum(axis=1), axis=0)  # Re-normalize
```

---

## Debugging Checklist

When weights look wrong, check in order:

1. **Print shape and dates:**
   ```python
   print(f"Shape: {weights.shape}")
   print(f"Date range: {weights.index[0]} to {weights.index[-1]}")
   ```

2. **Check for NaN:**
   ```python
   print(f"Any NaN? {weights.isna().any().any()}")
   print(f"NaN count per column:\n{weights.isna().sum()}")
   ```

3. **Check weight sum:**
   ```python
   weight_sum = weights.sum(axis=1)
   print(f"Weight sum stats:\n{weight_sum.describe()}")
   ```

4. **Check weight range:**
   ```python
   print(f"Min weight: {weights.min().min()}")
   print(f"Max weight: {weights.max().max()}")
   ```

5. **Visualize weights:**
   ```python
   weights.plot(figsize=(12,6), title='Portfolio Weights')
   ```

6. **Check alpha returns:**
   ```python
   print(f"Alpha returns shape: {alpha_return_df.shape}")
   print(f"Alpha returns sample:\n{alpha_return_df.head()}")
   print(f"Any consecutive 1's cleaned? {(alpha_return_df == alpha_return_df.shift(1)).sum().sum()}")
   ```

---

## Getting Help

If you're still stuck after checking this guide:

1. **Check examples**: Review `templates/examples/` for working code
2. **Read framework**: Review `framework.md` for basic requirements
3. **Simplify**: Start with equal_weight.py and build up
4. **Validate step-by-step**: Print intermediate results at each step

**Common pattern for debugging:**
```python
def weight(self, start, end):
    # Load data
    alpha_return_df = ...
    print(f"1. Loaded data: {alpha_return_df.shape}")

    # Clean data
    alpha_return_df = ...
    print(f"2. Cleaned data: {alpha_return_df.shape}, NaN: {alpha_return_df.isna().sum().sum()}")

    # Calculate metrics
    volatility_df = ...
    print(f"3. Volatility: min={volatility_df.min().min()}, max={volatility_df.max().max()}")

    # Calculate weights
    weights = ...
    print(f"4. Raw weights: sum={weights.sum(axis=1).mean()}")

    # Normalize
    weights = weights.div(weights.sum(axis=1), axis=0)
    print(f"5. Normalized: sum={weights.sum(axis=1).mean()}")

    # Final
    result = weights.shift(1).loc[str(start):str(end)]
    print(f"6. Final: {result.shape}, NaN: {result.isna().sum().sum()}")

    return result
```
