"""
Multi-Factor Strategy

Combine momentum, value, and quality factors with configurable weights.

Strategy Logic:
1. Calculate momentum factor (price change)
2. Calculate value factor (inverse PBR)
3. Calculate quality factor (ROE)
4. Combine factors with weights
5. Select top N stocks by combined score

Typical Parameters:
- momentum_weight: [0.3, 0.4, 0.5]
- value_weight: [0.2, 0.3, 0.4]
- quality_weight: [0.2, 0.3, 0.4]
- momentum_period: [20, 40, 60]
- top_stocks: [20, 30, 50]
"""

from finter import BaseAlpha
from finter.data import ContentFactory
import pandas as pd
from datetime import datetime, timedelta


def get_start_date(start: int, buffer: int = 365) -> int:
    """
    Get start date with buffer days for data loading.
    Rule of thumb: buffer = 2x longest lookback + 250 days
    """
    return int(
        (datetime.strptime(str(start), "%Y%m%d") - timedelta(days=buffer)).strftime("%Y%m%d")
    )


class Alpha(BaseAlpha):
    """Multi-factor: Combine momentum, value, and quality."""

    def get(
        self,
        start: int,
        end: int,
        momentum_weight: float = 0.4,
        value_weight: float = 0.3,
        quality_weight: float = 0.3,
        momentum_period: int = 60,
        top_stocks: int = 30,
    ) -> pd.DataFrame:
        """
        Generate alpha positions for date range.

        Parameters
        ----------
        start : int
            Start date in YYYYMMDD format
        end : int
            End date in YYYYMMDD format
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

        Returns
        -------
        pd.DataFrame
            Position DataFrame
        """
        # Load data with buffer
        cf = ContentFactory(
            "kr_stock", get_start_date(start, momentum_period * 2 + 250), end
        )

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
            momentum_score * momentum_weight
            + value_score * value_weight
            + quality_score * quality_weight
        )

        # Select top N stocks
        rank = combined_score.rank(axis=1, ascending=False)
        selected = rank <= top_stocks

        # Equal weight among selected, 1e8 == 100% of AUM
        weights = selected.div(selected.sum(axis=1), axis=0) * 1e8

        # CRITICAL: Always shift positions to avoid look-ahead bias
        return weights.shift(1).loc[str(start) : str(end)]
