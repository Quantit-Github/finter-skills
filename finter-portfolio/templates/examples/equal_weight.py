"""
Equal Weight Portfolio - Simplest Baseline

This is the simplest portfolio strategy: allocate equal weight (1/N) to all alphas.

Use Cases:
- Baseline for comparison
- High correlation between alphas (>0.7)
- When uncertain about alpha quality
- Maximum robustness (no estimation error)

Advantages:
- No estimation error
- Most robust
- Often outperforms complex methods (1/N paradox)
- No look-ahead bias

Disadvantages:
- Ignores risk differences
- Ignores performance differences
- May overweight risky alphas
"""

from finter import BasePortfolio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def calculate_previous_start_date(start_date: int, lookback_days: int) -> int:
    """
    Calculate the start date for preloading data based on lookback period

    Args:
        start_date (int): Target start date in YYYYMMDD format
        lookback_days (int): Number of days to look back

    Returns:
        int: Previous start date in YYYYMMDD format
    """
    start = datetime.strptime(str(start_date), "%Y%m%d")
    previous_start = start - timedelta(days=lookback_days)
    return int(previous_start.strftime("%Y%m%d"))


class Portfolio(BasePortfolio):
    """
    Equal Weight Portfolio (1/N)

    Allocates equal weight to all alpha strategies regardless of
    their risk or performance characteristics.
    """

    # List of alpha strategies to be combined
    alpha_list = [
        "us.compustat.stock.ywcho.alphathon2_yw_di",
        "us.compustat.stock.jyjung.insur_spxndx_roe",
        "us.compustat.stock.sypark.US_BDC_v4"
    ]

    def weight(self, start: int, end: int) -> pd.DataFrame:
        """
        Calculate equal weights for all alphas.

        Args:
            start (int): Start date in YYYYMMDD format
            end (int): End date in YYYYMMDD format

        Returns:
            pd.DataFrame: Weight DataFrame (date x alpha_names)
                         Each weight = 1/N where N = number of alphas
        """
        # Load alpha returns (need dates only, not actual returns for equal weight)
        # But we still load to get proper date index
        preload_start = calculate_previous_start_date(start, 365)
        alpha_return_df = self.alpha_pnl_df('us_stock', preload_start, end)

        # Equal weight: 1/N
        n_alphas = len(self.alpha_list)
        weights = pd.DataFrame(
            1.0 / n_alphas,
            index=alpha_return_df.index,
            columns=alpha_return_df.columns
        )

        # Static weights don't need shift(1) - they don't depend on returns
        # Just slice to requested date range
        return weights.loc[str(start):str(end)]

    # NOTE: NO need to implement get() method!
    # BasePortfolio automatically provides get() which combines alpha positions
    # using your weight() method. Just call portfolio.get(start, end) directly.


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    # Create portfolio instance
    portfolio = Portfolio()

    # Generate weights
    weights = portfolio.weight(20240101, 20241231)

    # Validate
    print("=" * 60)
    print("Equal Weight Portfolio Validation")
    print("=" * 60)

    print(f"\nShape: {weights.shape}")
    print(f"Date range: {weights.index[0]} to {weights.index[-1]}")

    print(f"\nWeight statistics:")
    print(weights.describe())

    print(f"\nWeight sum per date (should be ~1.0):")
    weight_sum = weights.sum(axis=1)
    print(weight_sum.describe())

    print(f"\nAny NaN? {weights.isna().any().any()}")

    # Visualize
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 1, figsize=(12, 10))

    # Plot 1: Weight time series
    weights.plot(ax=axes[0], title='Equal Weight Portfolio - Weight Allocation Over Time')
    axes[0].set_ylabel('Weight')
    axes[0].legend(loc='center left', bbox_to_anchor=(1, 0.5))
    axes[0].axhline(y=1.0/len(portfolio.alpha_list), color='gray', linestyle='--', label='Equal Weight')

    # Plot 2: Weight sum check
    weight_sum.plot(ax=axes[1], title='Weight Sum Check (should be 1.0)')
    axes[1].set_ylabel('Weight Sum')
    axes[1].axhline(y=1.0, color='red', linestyle='--', label='Target')
    axes[1].set_ylim([0.99, 1.01])
    axes[1].legend()

    plt.tight_layout()
    plt.show()

    print("\n" + "=" * 60)
    print("✓ Equal weight portfolio validated successfully!")
    print("=" * 60)

    # ========================================================================
    # BACKTESTING
    # ========================================================================
    print("\n" + "=" * 60)
    print("Portfolio Backtesting")
    print("=" * 60)

    from finter.backtest import Simulator

    # Run backtest
    print("\nRunning backtest...")
    simulator = Simulator(market_type="us_stock")
    result = simulator.run(position=portfolio.get(20240101, 20241231))

    # Print performance metrics
    stats = result.statistics
    print("\nPerformance Metrics:")
    print(f"  Total Return: {stats['Total Return (%)']:.2f}%")
    print(f"  Sharpe Ratio: {stats['Sharpe Ratio']:.2f}")
    print(f"  Max Drawdown: {stats['Max Drawdown (%)']:.2f}%")
    print(f"  Win Rate: {stats['Win Rate (%)']:.2f}%")

    # Visualize backtest results
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))

    # Plot 1: NAV curve
    result.summary['nav'].plot(ax=axes[0], title='Portfolio NAV (Equal Weight)', linewidth=2, color='blue')
    axes[0].set_ylabel('NAV (starts at 1000)')
    axes[0].grid(True, alpha=0.3)

    # Plot 2: Drawdown
    nav = result.summary['nav']
    drawdown = (nav / nav.cummax() - 1) * 100
    drawdown.plot(ax=axes[1], title='Portfolio Drawdown (%)', linewidth=2, color='red')
    axes[1].fill_between(drawdown.index, drawdown, 0, alpha=0.3, color='red')
    axes[1].set_ylabel('Drawdown (%)')
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

    print("\n" + "=" * 60)
    print("✓ Equal weight portfolio backtested successfully!")
    print("=" * 60)
    print("\nNOTE: Equal weight serves as a baseline.")
    print("      Compare other strategies (risk parity, MVO) against this benchmark.")
    print("      The 1/N paradox: Simple equal weight often outperforms complex optimization!")
