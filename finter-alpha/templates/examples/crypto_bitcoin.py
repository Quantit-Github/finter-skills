"""
Bitcoin Momentum Strategy (BETA)

Simple momentum strategy for Bitcoin using 8H candles.

Strategy Logic:
1. Calculate price momentum over specified period (in 8H candles)
2. Go long when momentum is positive, flat otherwise
3. Single asset (Bitcoin only)

Important Notes:
- Crypto support is BETA: Bitcoin only, 8H candles only
- Data available from 2018-01-01
- Only closing price available currently
- Use 'raw' universe and 'btcusdt_spot_binance' market type
- cf.search() does NOT work for raw universe
- No cross-sectional operations (single asset)
- Time resolution: 1 period = 8 hours

Typical Parameters:
- momentum_period: [3, 6, 9, 21] (3 = 24 hours, 21 = 7 days)
"""

from finter import BaseAlpha
from finter.data import ContentFactory
import pandas as pd


class Alpha(BaseAlpha):
    """Bitcoin momentum strategy using 8H candles."""

    def get(
        self,
        start: int,
        end: int,
        momentum_period: int = 6,
    ) -> pd.DataFrame:
        """
        Generate alpha positions for Bitcoin.

        Parameters
        ----------
        start : int
            Start date in YYYYMMDD format (e.g., 20230101)
            Must be >= 20180101 (Bitcoin data availability)
        end : int
            End date in YYYYMMDD format (e.g., 20241231)
        momentum_period : int
            Lookback period in 8H candles (default: 6 = 48 hours)
            Common values: 3 (24h), 6 (48h), 9 (72h), 21 (1 week)

        Returns
        -------
        pd.DataFrame
            Position DataFrame with:
            - Index: Trading dates (8H resolution)
            - Columns: Single column (Bitcoin)
            - Values: Position size (1e8 = 100% long, 0 = flat)
        """
        # Load Bitcoin data (use 'raw' universe for crypto)
        # Note: No need for get_start_date() helper, just add buffer manually
        # For crypto, we can't use get_start_date from datetime
        # So we hardcode start to have enough buffer
        cf = ContentFactory('raw', 20180101, end)

        # Load Bitcoin closing price (8H candles)
        btc_close = cf.get_df('content.binance.api.price_volume.btcusdt-spot-price_close.8H')

        # Calculate momentum (percent change over period)
        momentum = btc_close.pct_change(periods=momentum_period)

        # Generate signal: 1 (long) when momentum > 0, 0 (flat) otherwise
        signal = (momentum > 0).astype(float)

        # Convert to positions (1e8 = 100% of AUM)
        positions = signal * 1e8

        # CRITICAL: Always shift positions to avoid look-ahead bias
        return positions.shift(1).loc[str(start): str(end)]


# Example usage in Jupyter:
"""
from finter.backtest import Simulator

# Generate positions
alpha = Alpha()
positions = alpha.get(20230101, 20240101, momentum_period=6)

# Run backtest (use btcusdt_spot_binance market type)
sim = Simulator("btcusdt_spot_binance", 20230101, 20240101)
result = sim.run(position=positions)

# Check results
stats = result.statistics
print(f"Total Return: {stats['Total Return (%)']:.2f}%")
print(f"Sharpe Ratio: {stats['Sharpe Ratio']:.2f}")
print(f"Max Drawdown: {stats['Max Drawdown (%)']:.2f}%")
print(f"Hit Ratio: {stats['Hit Ratio (%)']:.2f}%")

# Plot NAV curve
result.summary['nav'].plot(title='Bitcoin Momentum Strategy NAV', figsize=(12,6))
"""
