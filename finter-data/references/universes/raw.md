# raw (Crypto)

Cryptocurrency data from Binance.

## Search Pattern

**`cf.search()` does NOT work!** Use exact paths from documentation.

```python
cf = ContentFactory('raw', 20200101, 20241201)

# ❌ Search doesn't work
cf.search('btc')  # Returns empty!

# ✅ Use exact path
btc = cf.get_df('content.binance.api.price_volume.btcusdt-spot-price_close.8H')
```

## Available Items

| Item | Description |
|------|-------------|
| `content.binance.api.price_volume.btcusdt-spot-price_close.8H` | BTC close price |
| `content.binance.api.price_volume.btcusdt-spot-volume.8H` | BTC volume |

## Gotchas

- **8H candles** (not daily)
- **Full path required** - no shortcuts
- **Limited pairs** - not all crypto pairs available
- **Search doesn't work** - must know exact item paths
