# Finter API Reference

Quick reference for Finter data access and backtesting methods.

## ContentFactory

Load market data across FINTER universes.

### Initialization

```python
from finter.data import ContentFactory
from helpers import get_start_date

# Basic usage
cf = ContentFactory(
    universe="kr_stock",  # "kr_stock", "us_stock", "btcusdt_spot_binance"
    start=get_start_date(20240101, buffer=365),
    end=20240201
)
```

### Key Methods

#### get_df(item_name)

Returns DataFrame with dates as index, stocks as columns.

```python
# Price data
close = cf.get_df("price_close")
open_price = cf.get_df("price_open")
high = cf.get_df("price_high")
low = cf.get_df("price_low")

# Volume and market cap
volume = cf.get_df("volume")
market_cap = cf.get_df("market_cap")

# Financial ratios
per = cf.get_df("per")   # Price-to-Earnings Ratio
pbr = cf.get_df("pbr")   # Price-to-Book Ratio
roe = cf.get_df("roe")   # Return on Equity
```

**Returns:** `pd.DataFrame` with shape (dates, stocks)

#### summary()

Prints available data categories. Returns `None`.

```python
cf.summary()
# Output categories:
# - Economic
# - Event
# - Financial
# - Index
# - Market
# - Quantitative
# - Unstructured
```

#### search(term)

Find data items containing search term.

```python
# Find all price-related items
price_items = cf.search("price")
# Returns: ['price_close', 'price_open', 'price_high', 'price_low', ...]

# Find volume items
volume_items = cf.search("volume")

# Find ratio items
ratio_items = cf.search("ratio")
```

**Returns:** List of matching item names

### Common Data Items

#### Price Data
- `price_close` - Daily closing price
- `price_open` - Daily opening price
- `price_high` - Daily high price
- `price_low` - Daily low price
- `price_adj_close` - Adjusted closing price (split/dividend adjusted)

#### Volume and Trading
- `volume` - Daily trading volume
- `trading_value` - Total trading value
- `trading_volume` - Number of shares traded

#### Financial Ratios
- `per` - Price-to-Earnings Ratio
- `pbr` - Price-to-Book Ratio
- `pcr` - Price-to-Cashflow Ratio
- `psr` - Price-to-Sales Ratio
- `roe` - Return on Equity
- `roa` - Return on Assets

#### Market Metrics
- `market_cap` - Market capitalization
- `shares_outstanding` - Number of outstanding shares

### Best Practices

#### Load with Buffer

Always load more historical data than needed:

```python
from helpers import get_start_date

# ✓ Correct - load extra historical data
cf = ContentFactory("kr_stock", get_start_date(start, buffer=365), end)
```

#### Handle Missing Data

```python
# Check for missing values
data = cf.get_df("price_close")
print(f"Missing values: {data.isnull().sum().sum()}")

# Forward fill missing values
data_filled = data.fillna(method='ffill')

# Or drop stocks with too many missing values
threshold = 0.9  # At least 90% data
valid_stocks = data.notna().sum() / len(data) >= threshold
data_clean = data.loc[:, valid_stocks]
```

## Symbol Search

Find FINTER IDs for specific stocks.

### Correct Usage (Must instantiate first!)

```python
from finter.data import Symbol

# ✓ CORRECT - Create instance first, then search
symbol = Symbol("us_stock")  # Create instance with universe
result = symbol.search("palantir")  # Returns DataFrame!

# IMPORTANT: result is a DataFrame with FINTER IDs in the INDEX
finter_id = result.index[0]  # Get FINTER ID from index
print(f"FINTER ID: {finter_id}")

# ❌ WRONG - This will not work!
result = Symbol.search("palantir", universe="us_stock")  # NO!
```

**Result Format:**
- Returns: `pd.DataFrame` with stock information
- FINTER ID location: `result.index` (NOT a column!)
- Get first match: `result.index[0]`

### Find Multiple Stock IDs

```python
from finter.data import Symbol

# Korean stocks
symbol = Symbol("kr_stock")
samsung_id = symbol.search("삼성전자").index[0]
sk_id = symbol.search("SK하이닉스").index[0]
naver_id = symbol.search("NAVER").index[0]

print(f"Samsung: {samsung_id}")
print(f"SK Hynix: {sk_id}")
print(f"NAVER: {naver_id}")

# US stocks
us_symbol = Symbol("us_stock")
pltr_id = us_symbol.search("palantir").index[0]
print(f"Palantir: {pltr_id}")
```

### Use in Alpha Strategy

**IMPORTANT**: Find IDs first, then hardcode them.

```python
# Step 1: Find IDs (run this ONCE, outside Alpha class)
from finter.data import Symbol

symbol = Symbol("us_stock")
pltr_id = symbol.search("palantir").index[0]
nvda_id = symbol.search("nvidia").index[0]
# Output: pltr_id = "12345", nvda_id = "67890"

# Step 2: Hardcode IDs in your Alpha class
class Alpha(BaseAlpha):
    def get(self, start, end):
        target_ids = ["12345", "67890"]  # Hardcoded from above
        close = cf.get_df("price_close")[target_ids]
        # ...
```

**Why FINTER IDs?** FINTER uses unique numeric IDs instead of tickers to prevent symbol conflicts over time.

See `templates/examples/stock_selection.py` for complete example.

## Backtest Simulator

Test alpha strategies with realistic market conditions.

### Basic Usage

```python
from finter.backtest import Simulator

# Initialize simulator
simulator = Simulator(market_type="kr_stock")

# Run backtest
result = simulator.run(position=positions)

# Access results
stats = result.statistics
summary = result.summary
```

### Market Types

```python
# Korean stocks
Simulator(market_type="kr_stock")

# US stocks
Simulator(market_type="us_stock")

# Cryptocurrency
Simulator(market_type="btcusdt_spot_binance")
```

### Transaction Costs

```python
simulator = Simulator(
    market_type="kr_stock",
    commission_rate=0.0025,    # 0.25% commission
    slippage_rate=0.001,       # 0.1% slippage
    tax_rate=0.0023           # 0.23% transaction tax
)
```

### Result Analysis

```python
result = simulator.run(position=positions)

# Performance metrics (pd.Series)
stats = result.statistics

print(f"Total Return: {stats['Total Return (%)']:.2f}%")
print(f"Sharpe Ratio: {stats['Sharpe Ratio']:.2f}")
print(f"Max Drawdown: {stats['Max Drawdown (%)']:.2f}%")
print(f"Win Rate: {stats['Win Rate (%)']:.2f}%")

# Daily data (pd.DataFrame)
summary = result.summary

nav = summary['nav']                # Net asset value
daily_returns = summary['daily_return']  # Daily returns
costs = summary['cost']             # Transaction costs
cumulative_pnl = summary['cumulative_pnl']  # Cumulative P&L
```

### Key Performance Metrics

Available in `result.statistics`:

- `Total Return (%)` - Total portfolio return (for entire backtest period)
- `Sharpe Ratio` - Risk-adjusted return
- `Max Drawdown (%)` - Maximum peak-to-trough decline
- `Win Rate (%)` - Percentage of profitable days
- `Profit Factor` - Gross profit / Gross loss
- `Average Win (%)` - Average winning day return
- `Average Loss (%)` - Average losing day return

**IMPORTANT**: There is NO `Annual Return (%)` field! Use `Total Return (%)` instead.

### Position DataFrame Format

```python
import pandas as pd

# Positions must be DataFrame with:
# - Index: Trading dates
# - Columns: Stock tickers (FINTER IDs)
# - Values: Money allocated (≤ 1e8 total per row)

positions = pd.DataFrame({
    'STOCK_A': [5e7, 4e7, 3e7],
    'STOCK_B': [3e7, 4e7, 5e7],
    'STOCK_C': [2e7, 2e7, 2e7]
}, index=pd.date_range('2024-01-01', periods=3))

# Row sums: 1e8, 1e8, 1e8 ✓
```

## Common DataFrame Operations

### Ranking

```python
# Percentile rank (0-1)
rank_pct = df.rank(pct=True, axis=1)

# Absolute rank
rank_abs = df.rank(axis=1)

# Descending rank
rank_desc = df.rank(ascending=False, axis=1)
```

### Rolling Calculations

```python
# Rolling mean
rolling_mean = df.rolling(window=20).mean()

# Rolling standard deviation
rolling_std = df.rolling(window=20).std()

# Exponential weighted moving average
ewma = df.ewm(span=20).mean()
```

### Cross-Sectional Operations

```python
# Row-wise operations (per date)
row_sum = df.sum(axis=1)
row_mean = df.mean(axis=1)
row_std = df.std(axis=1)

# Normalize each row
normalized = df.div(df.sum(axis=1), axis=0)

# Z-score per row (cross-sectional)
mean = df.mean(axis=1)
std = df.std(axis=1)
z_score = df.sub(mean, axis=0).div(std, axis=0)
```

### Filtering

```python
# Keep only values above threshold
filtered = df[df > threshold]

# Replace values below threshold with 0
filtered = df.where(df > threshold, 0)

# Select top K stocks per day
top_k = df.rank(axis=1, ascending=False) <= k
```

## Date Formatting

Always use YYYYMMDD integer format:

```python
# ✓ Correct formats
start = 20240101
end = 20241231

# Convert datetime to YYYYMMDD
from datetime import datetime
dt = datetime(2024, 1, 1)
date_int = int(dt.strftime("%Y%m%d"))  # 20240101

# Convert YYYYMMDD to string for DataFrame indexing
date_str = str(20240101)  # "20240101"
data.loc[date_str:date_str]
```

## See Also

- `framework.md` - BaseAlpha framework overview
- `../templates/` - Ready-to-use strategy templates
- `troubleshooting.md` - Common mistakes and solutions
