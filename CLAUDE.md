# Finter Framework

## Quick Start

```python
from finter.data import ContentFactory, Symbol

# Data discovery
cf = ContentFactory("kr_stock", 20200101, 20241231)
cf.search("close")  # Find available items
close = cf.get_df("price_close")

# Symbol search
symbol = Symbol("kr_stock")
result = symbol.search("삼성전자")
finter_id = result.index[0]
```

## Available Universes

| Universe | Assets | Notes |
|----------|--------|-------|
| kr_stock | ~2,500 | Richest data, full support |
| us_stock | ~8,000 | Full support |
| us_etf | ~6,700 | Market data only |
| vn_stock | ~1,000 | PascalCase columns |
| id_stock | ~1,000 | Use `volume_sum` |
| crypto_test | ~378 | 10min candles, **2024 ONLY** |

---

## Mental Models

### 1. TIME MACHINE TEST
> "Could I make this decision BEFORE market open?"

You're a trader at 8:30 AM. Market opens at 9:00 AM.
- You KNOW: All prices up to yesterday's close
- You DON'T KNOW: Today's prices (market hasn't opened!)

If your position for day T uses day T's data, you have a **time machine**.
Always end with `.shift(1)`: yesterday's signal -> today's position

### 2. PARALLEL UNIVERSE TEST
> "Would my 2023 trades change if I added 2024 data?"

- Universe A: `get(20200101, 20231231)`
- Universe B: `get(20200101, 20241231)`

2023 trades MUST be identical. If not, you're leaking future data.

**Path Independence = Can you calculate exact preload period?**
| Type | Preload | Examples |
|------|---------|----------|
| Exact | N days | `rolling(N)`, `pct_change(N)`, `diff(N)` |
| End-sensitive | drop last | `resample('ME')` - drop if `end != MonthEnd` |
| No window limit | infinite | `ewm()`, `expanding()`, `.mean()` on full df |

`ewm(span=N)` has NO fixed window. Use `rolling(N)` instead.

### 3. MONEY IS REAL TEST
> "Am I allocating money or just scoring stocks?"

- Position = 1 means "I bet 1 won" (almost nothing)
- Position = 1e8 means "I bet 100 million won (100% AUM)"

Signals (0/1/-1) are NOT Positions. Simulator needs actual money amounts.
`positions = signals.div(signals.sum(axis=1), axis=0) * 1e8`

### 4. SKEPTICAL INVESTOR TEST
> "Is this too good to be true?"

| Metric | Realistic | Suspicious |
|--------|-----------|------------|
| Sharpe | 0.5 ~ 2.0 | > 3.0 |
| Hit Ratio | 48% ~ 58% | > 65% |
| Max Drawdown | 15% ~ 40% | < 5% |

**Suspicious = BUG until proven otherwise.**

---

## Code Checklist

```
[ ] .shift(1) at return? (no time machine)
[ ] No .expanding() or .mean() on full df? (no future leak)
[ ] Position scale ~1e8? (not 0/1 signals)
```

---

## Skill Roles

| Skill | When to Use |
|-------|-------------|
| finter-data | Data loading, Symbol search, preprocessing |
| finter-alpha | BaseAlpha strategy implementation |
| finter-portfolio | BasePortfolio, weight optimization |

## Backtest Stats (Exact Names)

```python
stats = result.statistics
# 'Total Return (%)', 'Sharpe Ratio', 'Max Drawdown (%)',
# 'CAGR (%)', 'Volatility (%)', 'Hit Ratio (%)'
# 'Annual Return (%)' does NOT exist!
```

## crypto_test: MEMORY CRITICAL

**USE ONLY 2024 DATA** for crypto_test:

```python
# CORRECT
cf = ContentFactory('crypto_test', 20240101, 20241231)

# WRONG - will crash
cf = ContentFactory('crypto_test', 20200101, 20241231)
```
