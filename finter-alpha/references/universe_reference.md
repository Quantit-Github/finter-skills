# Universe Reference

Special cases and exceptions for Finter data universes.

## Overview

All universes use the **same framework** (BaseAlpha, ContentFactory, Simulator). For quick comparison, see SKILL.md.

**This document covers ONLY special cases and exceptions.**

**General rule**: Use `cf.search()` and `cf.summary()` to explore data - don't memorize item names!

## Standard Usage (Most Universes)

Works for: `kr_stock`, `us_stock`, `us_etf`, `id_stock`

```python
from finter.data import ContentFactory

# 1. Initialize
cf = ContentFactory("kr_stock", 20230101, 20241231)

# 2. Explore (DON'T SKIP THIS!)
cf.summary()  # View categories
results = cf.search("price")  # Find items

# 3. Load data
close = cf.get_df("price_close")
```

**Minor differences:**
- `id_stock`: Use `volume_sum` instead of `trading_volume`
- `us_etf`: Market data only (no fundamentals)

**Symbol search** works for all universes - use `Symbol(universe).search(ticker)` to find FINTER IDs.

## Special Case 1: Vietnamese Stocks (vn_stock)

### PascalCase Naming Convention

⚠️ **vn_stock uses PascalCase**, unlike all other universes:

```python
from finter.data import ContentFactory

cf = ContentFactory("vn_stock", 20230101, 20241231)

# ⚠️ Use PascalCase names
close = cf.get_df("ClosePrice")      # NOT price_close
open_price = cf.get_df("OpenPrice")  # NOT price_open
high = cf.get_df("HighestPrice")     # NOT price_high
low = cf.get_df("LowestPrice")       # NOT price_low

# cf.search() still works!
price_items = cf.search("price")
print(price_items)  # ['AveragePrice', 'ClosePrice', 'HighestPrice', ...]
```

**Why PascalCase?** Different data provider convention. Always `cf.search()` first!

## Special Case 2: Cryptocurrency (BETA)

### ⚠️ Beta Limitations

Crypto support has **major limitations**:
- **Single asset only**: Bitcoin (BTCUSDT)
- **Single timeframe**: 8-hour candles only
- **No cf.search()**: Must use exact item names from documentation
- **Different universe names**: `'raw'` for ContentFactory, `'btcusdt_spot_binance'` for Simulator

### Critical Difference: No cf.search()

Unlike all other universes, **cf.search() does NOT work** for crypto:

```python
from finter.data import ContentFactory

cf = ContentFactory('raw', 20180101, 20241231)

# ❌ Does NOT work!
cf.search("btcusdt")  # Returns empty list!
cf.search("price")    # Returns empty list!

# ✅ Must use exact item names
btc_close = cf.get_df('content.binance.api.price_volume.btcusdt-spot-price_close.8H')
btc_volume = cf.get_df('content.binance.api.price_volume.btcusdt-spot-volume.8H')
```

**Available items** (hardcoded):
- `content.binance.api.price_volume.btcusdt-spot-price_close.8H` - BTC closing price
- `content.binance.api.price_volume.btcusdt-spot-volume.8H` - BTC trading volume

### Universe Name Confusion

⚠️ **Different names for different contexts:**

```python
from finter.data import ContentFactory
from finter.backtest import Simulator

# ContentFactory: Use 'raw'
cf = ContentFactory('raw', 20180101, 20241231)
btc_close = cf.get_df('content.binance.api.price_volume.btcusdt-spot-price_close.8H')

# Simulator: Use 'btcusdt_spot_binance'
simulator = Simulator(market_type="btcusdt_spot_binance")
result = simulator.run(position=positions)
```

**Why different?**
- `'raw'` = generic universe for non-standard data
- `'btcusdt_spot_binance'` = specific market type for simulation

### Time Resolution: 8H Candles

Unlike daily resolution for stocks, crypto uses **8-hour candles**:

```python
# Time conversions
# 1 period = 8 hours
# 3 periods = 24 hours (1 day)
# 21 periods = 7 days (1 week)
# 126 periods = 42 days (~6 weeks)

# Example: 1-week momentum
momentum = btc_close.pct_change(21)  # 21 periods = 7 days
```

### Single Asset Positions

No cross-sectional operations - just binary in/out:

```python
# Simple signal: buy if positive momentum
signal = btc_close.pct_change(21) > 0

# Positions: 1e8 (all in) or 0 (out)
positions = signal.astype(float) * 1e8  # Single column DataFrame
```

### Complete Crypto Example

```python
from finter import BaseAlpha
from finter.data import ContentFactory
from finter.backtest import Simulator

class Alpha(BaseAlpha):
    def get(self, start: int, end: int, **kwargs):
        # ⚠️ Use 'raw' universe
        cf = ContentFactory('raw', start - 10000, end)

        # ⚠️ Use exact item name (cf.search() doesn't work!)
        btc_close = cf.get_df('content.binance.api.price_volume.btcusdt-spot-price_close.8H')

        # 21 periods = 7 days (8H candles)
        momentum = btc_close.pct_change(21)
        signal = momentum > 0

        # Single asset: 1e8 or 0
        positions = signal.astype(float) * 1e8

        return positions.shift(1).loc[str(start):str(end)]

# Backtest
alpha = Alpha()
positions = alpha.get(20240101, 20241231)

# ⚠️ Use 'btcusdt_spot_binance' for Simulator
simulator = Simulator(market_type="btcusdt_spot_binance")
result = simulator.run(position=positions)
```

**See `../templates/examples/crypto_bitcoin.py` for full working example.**

### When to Use Crypto

✅ **Suitable for:**
- Bitcoin-specific technical strategies
- Higher frequency signals (8H vs daily stocks)
- Single-asset momentum/trend strategies

❌ **NOT suitable for:**
- Multi-crypto portfolios (only BTC available)
- Daily resolution strategies (only 8H available)
- Altcoin strategies (only BTC available)
- Fundamental analysis (no fundamental data)

## Data Discovery Best Practices

**Rule: ALWAYS search before loading data**

```python
# ✅ CORRECT workflow
cf = ContentFactory("kr_stock", 20230101, 20241231)
cf.summary()  # View categories
items = cf.search("earnings")  # Find items
print(items)  # ['earnings-to-price', 'eps_basic', ...]
data = cf.get_df("earnings-to-price")  # Use exact name

# ❌ WRONG - guessing names
data = cf.get_df("eps")  # KeyError!
data = cf.get_df("price_earnings_ratio")  # KeyError!
```

**Exception**: Crypto (`raw` universe) - `cf.search()` doesn't work, use exact names from this document.

## See Also

- `../SKILL.md` - Universe comparison table (quick reference)
- `framework.md` - BaseAlpha framework rules
- `api_reference.md` - ContentFactory and Simulator API
- `../templates/examples/` - Working examples for each universe
