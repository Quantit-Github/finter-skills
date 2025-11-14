# Universe Reference

Complete guide to data universes supported by Finter.

## Overview

Finter organizes financial data into **universes** - distinct market domains with different characteristics. Each universe has:

- **Time period**: Historical data availability
- **Resolution**: Data frequency (daily, 8H, etc.)
- **Data items**: Available price, volume, fundamental data
- **Asset coverage**: Number and type of tradable assets

**Supported Markets** (from `finter.backtest.config.config.AVAILABLE_MARKETS`):
- `kr_stock` - Korean stocks
- `us_stock` - US stocks
- `us_etf` - US ETFs
- `us_future` - US futures
- `id_stock` - Indonesian stocks
- `id_bond` - Indonesian bonds
- `id_fund` - Indonesian funds
- `vn_stock` - Vietnamese stocks
- `btcusdt_spot_binance` - Bitcoin (BETA)

**This document focuses on the most commonly used universes: kr_stock, us_stock, and crypto.**

## Korean Stocks (kr_stock)

### Basic Information
- **Universe name**: `"kr_stock"`
- **Market type** (Simulator): `"kr_stock"`
- **Period**: 2000-01-01 ~ present
- **Resolution**: Daily (1D)
- **Asset count**: ~2,500 stocks (KOSPI + KOSDAQ)

### Available Data Categories

Content Model Summary:
- **Economic**: 1 subcategory, 4 items
- **Event**: 3 subcategories, 16 items
- **Financial**: 2 subcategories, 288 items
- **Index**: 1 subcategory, 68 items
- **Market**: 7 subcategories, 102 items
- **Quantitative**: 3 subcategories, 708 items
- **Unstructured**: 12 subcategories, 162 items

**Common starting points:**
- Price: `price_close`, `price_open`, `price_high`, `price_low`
- Valuation: `earnings-to-price`, `book-to-market`, `cashflow-to-price`
- Volume: `volume_sum`, `dollar-trading-volume`

**Discovery is key**: Use `cf.search('keyword')` to find specific data items. There are 1000+ items available.

```python
# Example searches
cf.search('price')      # Find price-related items
cf.search('book')       # Find book value items
cf.search('earnings')   # Find earnings-related items
cf.summary()            # View all categories
```

### Example Usage

```python
from finter.data import ContentFactory
from helpers import get_start_date

# Load Korean stock data
cf = ContentFactory("kr_stock", get_start_date(20240101, buffer=365), 20241231)
close = cf.get_df("price_close")

# Explore available data (search first!)
results = cf.search("earnings")
print(f"Found {len(results)} earnings-related items")

# Explore data
print(f"Stocks: {len(close.columns)}")
print(f"Date range: {close.index[0]} to {close.index[-1]}")
```

**For complete strategy examples with backtesting, see `../templates/examples/`.**

## US Stocks (us_stock)

### Basic Information
- **Universe name**: `"us_stock"`
- **Market type** (Simulator): `"us_stock"`
- **Period**: 1990-01-01 ~ present
- **Resolution**: Daily (1D)
- **Asset count**: ~8,000 stocks (NYSE + NASDAQ + others)

### Available Data Categories

Content Model Summary:
- **Economic**: 1 subcategory, 123 items
- **Financial**: 2 subcategories, 931 items
- **Market**: 3 subcategories, 21 items
- **Quantitative**: 2 subcategories, 262 items
- **Unstructured**: 5 subcategories, 72 items

**Common starting points:**
- Price: `price_close`, `price_open`, `price_high`, `price_low`
- Volume: `trading_volume`

**Discovery is key**: Use `cf.search('keyword')` to find specific data items. There are 1000+ items available.

```python
# Example searches
cf.search('price')      # Find price-related items
cf.search('volume')     # Find volume-related items
cf.summary()            # View all categories
```

### Example Usage

```python
from finter.data import ContentFactory
from helpers import get_start_date

# Load US stock data
cf = ContentFactory("us_stock", get_start_date(20240101, buffer=365), 20241231)
close = cf.get_df("price_close")
trading_volume = cf.get_df("trading_volume")  # Note: different from kr_stock

# Explore data
print(f"Stocks: {len(close.columns)}")
print(f"Date range: {close.index[0]} to {close.index[-1]}")
```

**For complete strategy examples with backtesting, see `../templates/examples/`.**

## Cryptocurrency (BETA)

### ⚠️ Beta Limitations

**Cryptocurrency support is currently in BETA with significant limitations:**

- **Single asset only**: Bitcoin (BTCUSDT) only
- **Single timeframe**: 8-hour (8H) candles only
- **Limited history**: Data from 2018-01-01 onwards
- **No multi-asset portfolios**: Cannot combine multiple cryptocurrencies
- **Raw universe access**: Use `'raw'` universe (not standard universe name)

**More cryptocurrencies, timeframes, and features will be added in future updates.**

### Basic Information
- **Universe name**: `"raw"` (special universe for crypto beta)
- **Market type** (Simulator): `"btcusdt_spot_binance"`
- **Period**: 2018-01-01 ~ present
- **Resolution**: 8-hour (8H) candles
- **Asset count**: 1 (Bitcoin only)

### Available Data Items

**Currently available:**
- `content.binance.api.price_volume.btcusdt-spot-price_close.8H` - Bitcoin closing price (8H candles)

**Note**:
- Item names use full content paths (longer than stock universes)
- `cf.search()` is not supported for raw universe
- Additional data items may require specific permissions

### Example Usage

```python
from finter.data import ContentFactory

# Load Bitcoin data (use 'raw' universe)
cf = ContentFactory('raw', 20180101, 20251114)
btc_close = cf.get_df('content.binance.api.price_volume.btcusdt-spot-price_close.8H')

# Explore data
print(btc_close.head())
print(f"Data shape: {btc_close.shape}")
print(f"Date range: {btc_close.index[0]} to {btc_close.index[-1]}")
```

**For complete strategy example with backtesting, see `../templates/examples/crypto_bitcoin.py`.**

### Important Differences from Stock Universes

**1. Universe name**: Use `'raw'` instead of asset-specific name

**2. Data item names**: Full content paths (longer names)
```python
# Stock universes (short names)
close = cf.get_df("price_close")

# Crypto (full content paths)
btc = cf.get_df("content.binance.api.price_volume.btcusdt-spot-price_close.8H")
```

**3. No search support**: `cf.search()` does not work for raw universe
```python
# Stock universes
cf.search('price')  # Works - returns list of items

# Crypto
cf.search('btcusdt')  # Does not work - returns empty list
```

**4. Single asset**: Positions are just `1e8` (all in) or `0` (out)
```python
# No cross-sectional operations like stocks
positions = signal * 1e8  # Single column DataFrame
```

**5. Time resolution**: 8H candles, not daily
- 1 period = 8 hours
- 3 periods = 24 hours (1 day)
- 21 periods = 7 days (1 week)

**6. No fundamental data**: Only price data available

### When to Use Crypto

**Suitable for:**
- Bitcoin-specific technical strategies
- Testing crypto market hypotheses
- Single-asset momentum/trend strategies
- Higher frequency signals (8H vs daily)

**Not suitable for:**
- Multi-crypto portfolios (not yet supported)
- Daily resolution strategies (only 8H available)
- Altcoin strategies (only BTC available)
- Fundamental analysis (no fundamental data)

## Other Markets

Additional markets are available but documentation is limited. Use `cf.search()` to explore:

- `us_etf` - US Exchange-Traded Funds
- `us_future` - US Futures contracts
- `id_stock` - Indonesian stocks
- `id_bond` - Indonesian bonds
- `id_fund` - Indonesian funds
- `vn_stock` - Vietnamese stocks

Contact support or explore with `ContentFactory.search()` for details on these markets.

## Choosing the Right Universe

### Quick Decision Guide

```
Need Korean stocks? → kr_stock
Need US stocks? → us_stock
Need Bitcoin only? → raw (crypto BETA)
Need US ETFs/Futures? → us_etf / us_future
Need emerging markets? → id_stock, vn_stock (explore first)
Need multiple cryptos? → Not yet supported
Need intraday data? → Only crypto (8H) available
Need fundamental ratios? → kr_stock or us_stock
```

### Common Use Cases

**Value Investing**: Use `kr_stock` or `us_stock` for fundamental ratios (PER, PBR, ROE, etc.)

**Momentum Trading**: Any universe works; crypto has higher frequency (8H vs 1D)

**Multi-factor Models**: Use `kr_stock` or `us_stock` for rich factor data

**Crypto Technical Trading**: Use `raw` universe with Bitcoin (BETA)

## Data Discovery

### Stock Universes (kr_stock, us_stock)

**Never guess item names!** Always use `cf.search()` first.

```python
# Search with keywords
cf = ContentFactory("kr_stock", 20200101, 20241231)
results = cf.search("price")
print(results)  # ['price_close', 'price_open', 'price_high', 'price_low', ...]

# Check available categories
cf.summary()  # Economic, Event, Financial, Index, Market, etc.

# Search for specific metrics
ratio_items = cf.search("ratio")
volume_items = cf.search("volume")
```

### Crypto Universe (raw)

**No search support** - you must know the exact item name.

```python
# Known item (from documentation)
cf = ContentFactory('raw', 20180101, 20251114)
btc_price = cf.get_df('content.binance.api.price_volume.btcusdt-spot-price_close.8H')
btc_volume = cf.get_df('content.binance.api.price_volume.btcusdt-spot-volume.8H')

# cf.search() does NOT work for raw universe
```

## See Also

- `framework.md` - BaseAlpha framework requirements
- `api_reference.md` - ContentFactory and Simulator API methods
- `../templates/examples/` - Strategy examples for each universe
