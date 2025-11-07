# Finter API Reference

Quick reference for Finter data access and API methods.

## Symbol Search

Convert stock names/tickers to FINTER IDs for accessing specific stocks.

### Why FINTER IDs?

FINTER uses unique numeric symbol IDs (e.g., `12948`, `56789`) instead of common tickers like "AAPL" or "005930". These IDs are randomly assigned and ensure consistent data access across time, preventing symbol conflicts. **Always use `Symbol.search()` to find the actual FINTER IDs before accessing stock data.**

### Basic Usage

```python
from finter.data import Symbol

# Initialize Symbol search
symbol = Symbol("kr_stock")

# Search by company name or ticker
results = symbol.search("삼성전자")
finter_id = results.index[0]  # Get FINTER ID

# View search results
print(results)  # DataFrame with name, ticker, exchange
```

### Search Patterns

```python
# Korean stocks
symbol = Symbol("kr_stock")
samsung = symbol.search("삼성전자")      # By company name
sk = symbol.search("SK하이닉스")        # By company name
ticker = symbol.search("005930")        # By ticker code

# US stocks
us_symbol = Symbol("us_stock")
apple = us_symbol.search("AAPL")        # By ticker
tech = us_symbol.search("Apple")        # By company name
```

### Using FINTER IDs in Strategies

**IMPORTANT**: Symbol search must be done **outside** the Alpha class. Find IDs first, then hardcode them in your strategy.

```python
# Step 1: Find FINTER IDs (run this BEFORE writing your Alpha class)
from finter.data import Symbol

symbol = Symbol("kr_stock")
samsung_results = symbol.search("삼성전자")
sk_results = symbol.search("SK하이닉스")
naver_results = symbol.search("NAVER")

print(f"Samsung ID: {samsung_results.index[0]}")    # e.g., 12948
print(f"SK Hynix ID: {sk_results.index[0]}")        # e.g., 34521
print(f"NAVER ID: {naver_results.index[0]}")        # e.g., 78932

# Step 2: Copy the actual IDs and hardcode them in your Alpha class
from finter import BaseAlpha
from finter.data import ContentFactory

class Alpha(BaseAlpha):
    """
    Strategy targeting specific stocks (Samsung, SK Hynix, NAVER).
    IDs were found using Symbol.search() and hardcoded here.
    """

    def get(self, start: int, end: int) -> pd.DataFrame:
        # Load data with buffer
        cf = ContentFactory("kr_stock", get_start_date(start, 20 * 2 + 250), end)

        # Hardcoded FINTER IDs (found using Symbol.search() above)
        # NOTE: These are example IDs - use actual IDs from Symbol.search()
        target_ids = [
            "12948",  # Samsung Electronics
            "34521",  # SK Hynix
            "78932"   # NAVER
        ]

        # Load data only for these stocks
        close = cf.get_df("price_close")[target_ids]

        # Apply strategy logic
        momentum = close.pct_change(20)
        rank = momentum.rank(axis=1, pct=True)

        # Equal weight allocation, 1e8 == 100% of AUM
        weights = (rank > 0).astype(float)
        weights = weights.div(weights.sum(axis=1), axis=0) * 1e8

        # CRITICAL: Always shift positions to avoid look-ahead bias
        return weights.shift(1).loc[str(start):str(end)]
```

### Helper Function for Finding Multiple IDs

Use this helper function **before** writing your Alpha class to find multiple IDs at once:

```python
from finter.data import Symbol

def get_finter_ids(stock_names: list, universe: str = "kr_stock") -> list:
    """
    Convert list of stock names to FINTER IDs.
    Run this BEFORE writing your Alpha class, then hardcode the IDs.

    Parameters
    ----------
    stock_names : list
        List of company names or ticker codes
    universe : str
        Market universe ("kr_stock", "us_stock", etc.)

    Returns
    -------
    list
        List of FINTER IDs to hardcode in your strategy
    """
    symbol = Symbol(universe)
    ids = []

    for name in stock_names:
        results = symbol.search(name)
        if not results.empty:
            finter_id = results.index[0]
            ids.append(finter_id)
            print(f"{name}: {finter_id}")
        else:
            print(f"Warning: '{name}' not found")

    return ids

# Example: Find IDs before writing strategy
target_ids = get_finter_ids(["삼성전자", "현대차", "LG에너지솔루션"])
# Output (example - actual IDs will be different numeric values):
# 삼성전자: 12948
# 현대차: 23456
# LG에너지솔루션: 89012

# Now hardcode these actual IDs in your Alpha class
```

## ContentFactory

Load market data across FINTER universes.

### Initialization

```python
from finter.data import ContentFactory

# Basic usage
cf = ContentFactory(
    universe="kr_stock",  # "kr_stock", "us_stock", "btcusdt_spot_binance"
    start=20240101,        # YYYYMMDD format
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

### Data Loading Best Practices

#### 1. Load Extra Historical Data

Always load more data than needed for calculations:

```python
# ❌ Wrong - exactly the date range
cf = ContentFactory("kr_stock", start, end)

# ✓ Correct - load extra historical data
cf = ContentFactory("kr_stock", start - 10000, end)
# This gives buffer for calculations, then filter at the end
```

#### 2. Handle Missing Data

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

#### 3. Date Range Filtering

```python
# Load data
cf = ContentFactory("kr_stock", 20200101 - 10000, 20241231)
data = cf.get_df("price_close")

# Calculate indicators
momentum = data.pct_change(20)

# Filter to exact range at the end
start_date = "20200101"
end_date = "20241231"
result = momentum.loc[start_date:end_date]
```

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

- `Total Return (%)` - Total portfolio return
- `Annual Return (%)` - Annualized return
- `Sharpe Ratio` - Risk-adjusted return
- `Max Drawdown (%)` - Maximum peak-to-trough decline
- `Win Rate (%)` - Percentage of profitable days
- `Profit Factor` - Gross profit / Gross loss
- `Average Win (%)` - Average winning day return
- `Average Loss (%)` - Average losing day return

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

Always use YYYYMMDD integer format for dates:

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

- `base_alpha_guide.md` - BaseAlpha framework
- `alpha_examples.md` - Complete strategy examples
