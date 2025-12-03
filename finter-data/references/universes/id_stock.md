# id_stock

Indonesian stock market data.

## Search Pattern

```python
cf = ContentFactory('id_stock', 20200101, 20241201)

cf.search('price')
cf.search('volume')
cf.search('sector')
```

## Common Items

| Category | Item | Description |
|----------|------|-------------|
| Price | `price_close` | Close price |
| Volume | `volume_sum` | Trading volume (**not** `trading_volume`!) |
| Other | `sharia` | Sharia compliance (binary) |
| Other | `sector_code` | Sector classification |
| Other | `adjust_factor` | Adjustment factor |

## ID System

- Ticker-style IDs (e.g., 'AADI', 'AALI', 'BBCA')
- Consistent across datasets

## Gotchas

**Volume item name:**
```python
# ❌ Wrong
cf.get_df('trading_volume')  # Not found!

# ✅ Correct
cf.get_df('volume_sum')
```

**Financial data errors:**
```python
# ⚠️ Most financial items fail to load
cf.get_df('total_assets')  # Error: '<=' not supported...
```

Use `cf.search()` to check available items before loading.
