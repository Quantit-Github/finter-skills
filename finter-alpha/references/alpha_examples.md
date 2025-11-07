# Alpha Strategy Examples

Complete, working implementations of various alpha strategies using the BaseAlpha framework.

## Helper Function

All examples use this helper function for date handling:

```python
def get_start_date(start: int, buffer: int = 365) -> int:
    """
    Get start date with buffer days

    Because we need to load data with buffer for calculations
    Rule of thumb: buffer = 2x longest lookback + 250 days
    """
    from datetime import datetime, timedelta

    return int(
        (datetime.strptime(str(start), "%Y%m%d") - timedelta(days=buffer)).strftime(
            "%Y%m%d"
        )
    )
```

## BaseAlpha Examples

### 1. Simple Momentum Strategy

```python
from finter import BaseAlpha
from finter.data import ContentFactory
import pandas as pd


class Alpha(BaseAlpha):
    """
    Classic momentum strategy: Buy recent winners, sell recent losers.

    Strategy Logic:
    1. Calculate price momentum over specified period
    2. Rank all stocks by momentum
    3. Select top performers above threshold
    4. Equal weight selected stocks
    """

    def get(self, start: int, end: int,
            momentum_period: int = 21,
            top_percent: float = 0.9) -> pd.DataFrame:
        """
        Generate alpha positions for date range.

        Parameters
        ----------
        start : int
            Start date in YYYYMMDD format (e.g., 20240101)
        end : int
            End date in YYYYMMDD format (e.g., 20241231)
        momentum_period : int
            Lookback period for momentum calculation (default: 21 days)
        top_percent : float
            Percentile threshold for selection (0.9 = top 10% stocks)

        Returns
        -------
        pd.DataFrame
            Position DataFrame with:
            - Index: Trading dates
            - Columns: Stock tickers (FINTER IDs)
            - Values: Position sizes (money allocated, row sum ≤ 1e8)
        """
        # Load data with buffer for calculations
        # Rule of thumb: buffer = 2x longest lookback + 250 days
        cf = ContentFactory("kr_stock", get_start_date(start, momentum_period * 2 + 250), end)
        close = cf.get_df("price_close")

        # Calculate momentum
        momentum = close.pct_change(momentum_period)

        # Rank stocks by momentum
        rank = momentum.rank(pct=True, axis=1)

        # Select top stocks
        selected = rank >= top_percent

        # Create positions (equal weight), 1e8 == 100% of AUM
        weights = selected.div(selected.sum(axis=1), axis=0) * 1e8

        # CRITICAL: Always shift positions to avoid look-ahead bias
        return weights.shift(1).loc[str(start):str(end)]
```

**Typical Parameters:**
```python
momentum_period: [10, 21, 42, 63]
top_percent: [0.8, 0.9, 0.95]
```

### 2. Mean Reversion Strategy

```python
class Alpha(BaseAlpha):
    """
    Buy oversold stocks, sell overbought stocks based on z-score.

    Strategy Logic:
    1. Calculate rolling z-score of prices
    2. Identify oversold stocks (z-score below threshold)
    3. Equal weight selected stocks
    4. Smooth positions over holding period
    """

    def get(self, start: int, end: int,
            lookback: int = 60,
            z_threshold: float = 2.0,
            holding_period: int = 5) -> pd.DataFrame:
        """
        Parameters
        ----------
        lookback : int
            Window for calculating mean and std
        z_threshold : float
            Z-score threshold for signals (typically 1.5-2.5)
        holding_period : int
            Days to hold position for smoothing
        """
        # Load data with buffer
        cf = ContentFactory("kr_stock", get_start_date(start, lookback * 2 + 250), end)
        close = cf.get_df("price_close")

        # Calculate z-score
        rolling_mean = close.rolling(lookback).mean()
        rolling_std = close.rolling(lookback).std()
        z_score = (close - rolling_mean) / rolling_std

        # Buy oversold (z-score < -threshold)
        buy_signal = z_score < -z_threshold

        # Equal weight among selected stocks, 1e8 == 100% of AUM
        weights = buy_signal.div(buy_signal.sum(axis=1), axis=0) * 1e8

        # Smooth with rolling average
        weights_smooth = weights.rolling(holding_period).mean()

        # CRITICAL: Always shift positions to avoid look-ahead bias
        return weights_smooth.shift(1).loc[str(start):str(end)]
```

**Typical Parameters:**
```python
lookback: [20, 40, 60, 120]
z_threshold: [1.5, 2.0, 2.5, 3.0]
holding_period: [3, 5, 10]
```

### 3. Multi-Factor Strategy

```python
class Alpha(BaseAlpha):
    """
    Combine momentum, value, and quality factors with configurable weights.

    Strategy Logic:
    1. Calculate momentum factor (price change)
    2. Calculate value factor (inverse PBR)
    3. Calculate quality factor (ROE)
    4. Combine factors with weights
    5. Select top N stocks by combined score
    """

    def get(self, start: int, end: int,
            momentum_weight: float = 0.4,
            value_weight: float = 0.3,
            quality_weight: float = 0.3,
            momentum_period: int = 60,
            top_stocks: int = 30) -> pd.DataFrame:
        """
        Parameters
        ----------
        momentum_weight : float
            Weight for momentum factor (0-1)
        value_weight : float
            Weight for value factor (0-1)
        quality_weight : float
            Weight for quality factor (0-1)
        momentum_period : int
            Lookback for momentum calculation
        top_stocks : int
            Number of top stocks to select
        """
        # Load data with buffer
        cf = ContentFactory("kr_stock", get_start_date(start, momentum_period * 2 + 250), end)

        # Load data
        close = cf.get_df("price_close")
        pbr = cf.get_df("pbr")
        roe = cf.get_df("roe")

        # Factor 1: Momentum (price change)
        momentum_score = close.pct_change(momentum_period).rank(axis=1, pct=True)

        # Factor 2: Value (inverse PBR)
        value_score = (1 / pbr).rank(axis=1, pct=True)

        # Factor 3: Quality (ROE)
        quality_score = roe.rank(axis=1, pct=True)

        # Combine factors with weights
        combined_score = (
            momentum_score * momentum_weight +
            value_score * value_weight +
            quality_score * quality_weight
        )

        # Select top N stocks
        rank = combined_score.rank(axis=1, ascending=False)
        selected = rank <= top_stocks

        # Equal weight among selected, 1e8 == 100% of AUM
        weights = selected.div(selected.sum(axis=1), axis=0) * 1e8

        # CRITICAL: Always shift positions to avoid look-ahead bias
        return weights.shift(1).loc[str(start):str(end)]
```

**Typical Parameters:**
```python
momentum_weight: [0.3, 0.4, 0.5]
value_weight: [0.2, 0.3, 0.4]
quality_weight: [0.2, 0.3, 0.4]
momentum_period: [20, 40, 60]
top_stocks: [20, 30, 50]
```

### 4. RSI Strategy

```python
import numpy as np


class Alpha(BaseAlpha):
    """
    RSI-based mean reversion: Buy oversold, sell overbought.

    Strategy Logic:
    1. Calculate RSI (Relative Strength Index)
    2. Identify oversold stocks (RSI below threshold)
    3. Equal weight selected stocks
    """

    def get(self, start: int, end: int,
            rsi_period: int = 14,
            oversold: float = 30,
            overbought: float = 70) -> pd.DataFrame:
        """
        Parameters
        ----------
        rsi_period : int
            RSI calculation period
        oversold : float
            RSI threshold for buy signal (typically 20-30)
        overbought : float
            RSI threshold for sell signal (typically 70-80)
        """
        # Load data with buffer
        cf = ContentFactory("kr_stock", get_start_date(start, rsi_period * 3 + 250), end)
        close = cf.get_df("price_close")

        # Calculate price changes
        delta = close.diff()

        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # Calculate average gain and loss
        avg_gain = gain.rolling(rsi_period).mean()
        avg_loss = loss.rolling(rsi_period).mean()

        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        # Generate signals (buy oversold stocks)
        buy_signal = rsi < oversold

        # Long positions on buy signals, 1e8 == 100% of AUM
        positions = buy_signal.astype(float)
        weights = positions.div(positions.sum(axis=1), axis=0) * 1e8

        # CRITICAL: Always shift positions to avoid look-ahead bias
        return weights.shift(1).loc[str(start):str(end)]
```

**Typical Parameters:**
```python
rsi_period: [7, 14, 21, 28]
oversold: [20, 25, 30]
overbought: [70, 75, 80]
```

### 5. Volatility-Adjusted Momentum

```python
class Alpha(BaseAlpha):
    """
    Risk-adjusted momentum: Weight by return/volatility ratio (Sharpe-like).

    Strategy Logic:
    1. Calculate price returns over specified period
    2. Calculate rolling volatility
    3. Compute risk-adjusted return (return / volatility)
    4. Select top stocks by risk-adjusted performance
    5. Weight by risk-adjusted return magnitude
    """

    def get(self, start: int, end: int,
            return_period: int = 60,
            vol_period: int = 60,
            top_percent: float = 0.2) -> pd.DataFrame:
        """
        Parameters
        ----------
        return_period : int
            Period for return calculation
        vol_period : int
            Period for volatility calculation
        top_percent : float
            Percentile for stock selection (0.2 = top 20%)
        """
        # Load data with buffer
        buffer = max(return_period, vol_period) * 2 + 250
        cf = ContentFactory("kr_stock", get_start_date(start, buffer), end)
        close = cf.get_df("price_close")

        # Calculate returns
        returns = close.pct_change(return_period)

        # Calculate volatility
        daily_returns = close.pct_change()
        volatility = daily_returns.rolling(vol_period).std()

        # Risk-adjusted return (Sharpe-like ratio)
        risk_adj_return = returns / volatility

        # Select top stocks by risk-adjusted return
        rank = risk_adj_return.rank(pct=True, axis=1)
        selected = rank >= (1 - top_percent)

        # Weight by risk-adjusted return magnitude, 1e8 == 100% of AUM
        weights = (selected * risk_adj_return).clip(lower=0)
        weights = weights.div(weights.sum(axis=1), axis=0) * 1e8

        # CRITICAL: Always shift positions to avoid look-ahead bias
        return weights.shift(1).loc[str(start):str(end)]
```

### 6. Specific Stock Strategy

**IMPORTANT**: Find FINTER IDs first using Symbol.search(), then hardcode them in your Alpha class.

```python
# Step 1: Find FINTER IDs (run this first, outside Alpha class)
# from finter.data import Symbol
# symbol = Symbol("kr_stock")
# print(symbol.search("삼성전자").index[0])    # e.g., 12948
# print(symbol.search("SK하이닉스").index[0])  # e.g., 34521
# print(symbol.search("NAVER").index[0])      # e.g., 78932

# Step 2: Create Alpha class with hardcoded IDs
class Alpha(BaseAlpha):
    """
    Strategy targeting specific stocks only (Samsung, SK Hynix, NAVER).
    Stock IDs were found using Symbol.search() and hardcoded here.

    Strategy Logic:
    1. Load data for specific stocks only
    2. Calculate momentum for each stock
    3. Rank and select stocks with positive momentum
    4. Equal weight selected stocks
    """

    def get(self, start: int, end: int,
            momentum_period: int = 20) -> pd.DataFrame:
        """
        Parameters
        ----------
        momentum_period : int
            Momentum calculation period
        """
        # Load data with buffer
        cf = ContentFactory("kr_stock", get_start_date(start, momentum_period * 2 + 250), end)

        # Hardcoded FINTER IDs (found using Symbol.search())
        # NOTE: These are example IDs - use actual IDs from Symbol.search()
        target_ids = [
            "12948",  # Samsung Electronics
            "34521",  # SK Hynix
            "78932"   # NAVER
        ]

        # Load data only for these stocks
        close = cf.get_df("price_close")[target_ids]

        # Calculate momentum
        momentum = close.pct_change(momentum_period)

        # Rank stocks by momentum
        rank = momentum.rank(axis=1, pct=True)

        # Allocate to stocks with positive momentum, 1e8 == 100% of AUM
        selected = rank > 0.5
        weights = selected.div(selected.sum(axis=1), axis=0) * 1e8

        # CRITICAL: Always shift positions to avoid look-ahead bias
        return weights.shift(1).loc[str(start):str(end)]
```

**Typical Parameters:**
```python
momentum_period: [10, 20, 30, 60]

# Other stock combinations to try (find IDs first):
# Tech stocks: ["삼성전자", "SK하이닉스", "NAVER", "카카오"]
# Auto/Heavy: ["현대차", "POSCO", "LG화학"]
```

**US Stocks Example:**
```python
# Step 1: Find IDs first
# from finter.data import Symbol
# us_symbol = Symbol("us_stock")
# for ticker in ["META", "AAPL", "AMZN", "NFLX", "GOOGL"]:
#     print(f"{ticker}: {us_symbol.search(ticker).index[0]}")
# Output (example - actual IDs will be numeric):
# META: 45123
# AAPL: 67890
# AMZN: 23456
# NFLX: 78901
# GOOGL: 34567

# Step 2: Create Alpha with hardcoded IDs
class Alpha(BaseAlpha):
    """
    FAANG momentum strategy.
    Stock IDs were found using Symbol.search() and hardcoded.

    Strategy Logic:
    1. Load data for FAANG stocks only
    2. Calculate 20-day returns
    3. Select top 3 performers
    4. Equal weight selected stocks
    """

    def get(self, start: int, end: int) -> pd.DataFrame:
        # Load data with buffer
        cf = ContentFactory("us_stock", get_start_date(start, 20 * 2 + 250), end)

        # Hardcoded FINTER IDs for FAANG stocks
        # NOTE: These are example IDs - use actual IDs from Symbol.search()
        faang_ids = [
            "45123",  # Meta (Facebook)
            "67890",  # Apple
            "23456",  # Amazon
            "78901",  # Netflix
            "34567"   # Google
        ]

        # Load and analyze
        close = cf.get_df("price_close")[faang_ids]
        returns_20d = close.pct_change(20)

        # Equal weight the top 3 performers
        rank = returns_20d.rank(axis=1, ascending=False)
        selected = rank <= 3

        # 1e8 == 100% of AUM
        weights = selected.div(selected.sum(axis=1), axis=0) * 1e8

        # CRITICAL: Always shift positions to avoid look-ahead bias
        return weights.shift(1).loc[str(start):str(end)]
```

## Common Patterns

### Equal Weight Portfolio

```python
# Simple equal weight across all available stocks
def get(self, start, end):
    # Load data with buffer
    cf = ContentFactory("kr_stock", get_start_date(start), end)
    close = cf.get_df("price_close")

    # Equal weight all stocks, 1e8 == 100% of AUM
    n_stocks = close.shape[1]
    positions = close.notna().astype(float) * (1e8 / n_stocks)

    # CRITICAL: Always shift positions to avoid look-ahead bias
    return positions.shift(1).loc[str(start):str(end)]
```

### Top-K Selection

```python
# Select top 20 stocks by momentum
def get(self, start, end, top_k=20):
    # Load data with buffer
    cf = ContentFactory("kr_stock", get_start_date(start, 20 * 2 + 250), end)
    close = cf.get_df("price_close")
    momentum = close.pct_change(20)

    # Select top K stocks
    top_k_mask = momentum.rank(axis=1, ascending=False) <= top_k

    # Equal weight selected stocks, 1e8 == 100% of AUM
    positions = top_k_mask.astype(float) * (1e8 / top_k)

    # CRITICAL: Always shift positions to avoid look-ahead bias
    return positions.shift(1).loc[str(start):str(end)]
```

### Rolling Rebalance

```python
# Rebalance only every N days to reduce transaction costs
def get(self, start, end, rebalance_freq=5):
    # Load data with buffer
    cf = ContentFactory("kr_stock", get_start_date(start, 20 * 2 + 250), end)
    close = cf.get_df("price_close")

    # Calculate momentum and select stocks
    momentum = close.pct_change(20)
    rank = momentum.rank(pct=True, axis=1)
    selected = rank >= 0.9

    # Equal weight selected stocks, 1e8 == 100% of AUM
    weights = selected.div(selected.sum(axis=1), axis=0) * 1e8

    # Rebalance only every N days (forward fill positions)
    rebalanced = weights.iloc[::rebalance_freq].reindex(
        weights.index, method='ffill'
    )

    # CRITICAL: Always shift positions to avoid look-ahead bias
    return rebalanced.shift(1).loc[str(start):str(end)]
```

## See Also

- `base_alpha_guide.md` - BaseAlpha framework details
- `finter_api_reference.md` - Data access methods
- `best_practices.md` - Optimization and debugging tips
