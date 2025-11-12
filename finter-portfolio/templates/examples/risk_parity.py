"""
Risk Parity Portfolio - Inverse Volatility Weighting

This strategy allocates weights inversely proportional to volatility,
so each alpha contributes equal risk to the portfolio.

Use Cases:
- Alphas have significantly different volatilities
- Want to balance risk contribution across alphas
- Need more stable weight allocation
- Risk management is priority

Advantages:
- Balances risk contribution
- More stable than return-based methods
- Simple and intuitive
- Well-researched approach

Disadvantages:
- Ignores expected returns
- May underweight high-return alphas
- Requires sufficient history
- Volatility estimates can be noisy
"""

from finter import BasePortfolio
from finter.data import ContentFactory
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
    Risk Parity Portfolio using Inverse Volatility Weighting

    Weights are proportional to 1/volatility, ensuring each alpha
    contributes approximately equal risk to the portfolio.
    """

    # List of alpha strategies to be combined
    alpha_list = [
        "us.compustat.stock.ywcho.alphathon2_yw_di",
        "us.compustat.stock.jyjung.insur_spxndx_roe",
        "us.compustat.stock.sypark.US_BDC_v4"
    ]

    def weight(self, start: int, end: int) -> pd.DataFrame:
        """
        Calculate risk parity weights using inverse volatility.

        Args:
            start (int): Start date in YYYYMMDD format
            end (int): End date in YYYYMMDD format

        Returns:
            pd.DataFrame: Weight DataFrame (date x alpha_names)
                         Weights sum to 1.0 per date
        """
        # Initialize data with 1-year lookback period
        # Need extra buffer for 126-day rolling volatility
        preload_start = calculate_previous_start_date(start, 365)

        # Get alpha returns (alpha_pnl_df returns dict with name as column, date as index)
        alpha_return_df = self.alpha_pnl_df('us_stock', preload_start, end)

        # ===== CRITICAL: Handle consecutive returns of 1 (no change) =====
        # Identify sequences of 1's and keep only first 5 occurrences using mask and ffill
        # This prevents volatility underestimation from long holding periods
        find_1 = (alpha_return_df == 1) & (alpha_return_df.shift(1) == 1)
        alpha_return_df = alpha_return_df.mask(find_1, np.nan).ffill(limit=5)

        # Calculate rolling volatility (6-month = 126 trading days)
        # Using 6 months as it balances responsiveness and stability
        lookback_days = 126
        volatility_df = alpha_return_df.rolling(
            window=lookback_days,
            min_periods=lookback_days  # Require full window for valid calculation
        ).std()

        # Calculate risk parity weights using inverse volatility
        # Replace zero volatility with NaN to avoid division by zero
        adjusted_volatility = volatility_df.replace(0, np.nan)

        # Calculate inverse volatility for risk parity weighting
        inv_volatility = 1 / adjusted_volatility

        # Normalize weights to sum to 1 across each row (date)
        weights = inv_volatility.div(inv_volatility.sum(axis=1), axis=0)

        # Fill NaN weights with 0 (or could use equal weight as fallback)
        weights = weights.fillna(0)

        # ===== IMPORTANT: Shift Logic =====
        # 1. 알파 리턴을 포트폴리오 비중으로 사용하는 경우: shift(1) 필요
        #    - 이유: 오늘의 리턴을 보고 내일 포지션을 잡아야 함 (look-ahead bias 방지)
        # 2. 정적 비중(volatility 기반 등)을 만드는 경우: shift 불필요 또는 선택적
        #    - 이유: volatility는 과거 데이터만 사용하므로 이미 lag가 내재됨
        #    - 하지만 안전하게 하려면 shift(1) 적용 권장
        #
        # 현재 케이스: volatility 기반 risk parity이므로 shift(1) 적용
        return weights.shift(1).loc[str(start):str(end)]

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
    print("Generating risk parity weights...")
    weights = portfolio.weight(20240101, 20241231)

    # Validate
    print("=" * 60)
    print("Risk Parity Portfolio Validation")
    print("=" * 60)

    print(f"\nShape: {weights.shape}")
    print(f"Date range: {weights.index[0]} to {weights.index[-1]}")

    print(f"\nWeight statistics:")
    print(weights.describe())

    print(f"\nWeight sum per date (should be ~1.0):")
    weight_sum = weights.sum(axis=1)
    print(weight_sum.describe())

    print(f"\nAny NaN? {weights.isna().any().any()}")

    print(f"\nWeight range:")
    print(f"  Min: {weights.min().min():.4f}")
    print(f"  Max: {weights.max().max():.4f}")

    # Analyze alpha returns and volatility
    print("\n" + "=" * 60)
    print("Alpha Analysis")
    print("=" * 60)

    # Load alpha returns for analysis
    alpha_return_df = portfolio.alpha_pnl_df('us_stock', 20230101, 20241231)
    find_1 = (alpha_return_df == 1) & (alpha_return_df.shift(1) == 1)
    alpha_return_df = alpha_return_df.mask(find_1, np.nan).ffill(limit=5)

    # Calculate volatility
    volatility = alpha_return_df.rolling(126).std()

    print("\nAverage Volatility by Alpha:")
    print(volatility.mean().sort_values(ascending=False))

    print("\nAverage Weight by Alpha:")
    print(weights.mean().sort_values(ascending=False))

    # Visualize
    import matplotlib.pyplot as plt
    import seaborn as sns

    fig, axes = plt.subplots(3, 2, figsize=(15, 12))

    # Plot 1: Weight time series
    weights.plot(ax=axes[0, 0], title='Risk Parity - Weight Allocation Over Time')
    axes[0, 0].set_ylabel('Weight')
    axes[0, 0].legend(loc='center left', bbox_to_anchor=(1, 0.5))

    # Plot 2: Weight distribution
    weights.boxplot(ax=axes[0, 1])
    axes[0, 1].set_title('Weight Distribution by Alpha')
    axes[0, 1].set_ylabel('Weight')
    axes[0, 1].axhline(y=1.0/len(portfolio.alpha_list), color='red', linestyle='--', label='Equal Weight')

    # Plot 3: Weight sum check
    weight_sum.plot(ax=axes[1, 0], title='Weight Sum Check (should be 1.0)')
    axes[1, 0].set_ylabel('Weight Sum')
    axes[1, 0].axhline(y=1.0, color='red', linestyle='--', label='Target')
    axes[1, 0].set_ylim([0.99, 1.01])
    axes[1, 0].legend()

    # Plot 4: Volatility time series
    volatility.plot(ax=axes[1, 1], title='Rolling 6M Volatility by Alpha')
    axes[1, 1].set_ylabel('Volatility')
    axes[1, 1].legend(loc='center left', bbox_to_anchor=(1, 0.5))

    # Plot 5: Correlation heatmap
    sns.heatmap(alpha_return_df.corr(), annot=True, cmap='coolwarm', center=0,
                ax=axes[2, 0], fmt='.2f', square=True)
    axes[2, 0].set_title('Alpha Return Correlation')

    # Plot 6: Cumulative returns
    cumulative_returns = (1 + (alpha_return_df - 1)).cumprod()
    cumulative_returns.plot(ax=axes[2, 1], title='Alpha Cumulative Returns')
    axes[2, 1].set_ylabel('Cumulative Return')
    axes[2, 1].legend(loc='center left', bbox_to_anchor=(1, 0.5))

    plt.tight_layout()
    plt.show()

    print("\n" + "=" * 60)
    print("✓ Risk parity portfolio validated successfully!")
    print("=" * 60)

    # ========================================================================
    # BACKTESTING & COMPARISON WITH EQUAL WEIGHT
    # ========================================================================
    print("\n" + "=" * 60)
    print("Portfolio Backtesting & Equal Weight Comparison")
    print("=" * 60)

    from finter.backtest import Simulator

    # Backtest risk parity portfolio
    print("\nBacktesting risk parity portfolio...")
    simulator = Simulator(market_type="us_stock")
    rp_result = simulator.run(position=portfolio.get(20240101, 20241231))

    # Create equal weight baseline
    class EqualWeightBaseline(BasePortfolio):
        alpha_list = Portfolio.alpha_list  # Same alphas!

        def weight(self, start, end):
            preload_start = calculate_previous_start_date(start, 365)
            alpha_return_df = self.alpha_pnl_df('us_stock', preload_start, end)
            n = len(self.alpha_list)
            weights = pd.DataFrame(1.0/n, index=alpha_return_df.index, columns=alpha_return_df.columns)
            return weights.loc[str(start):str(end)]

        # NO need to implement get() - BasePortfolio provides it!

    print("Backtesting equal weight baseline...")
    eq_portfolio = EqualWeightBaseline()
    eq_result = simulator.run(position=eq_portfolio.get(20240101, 20241231))

    # Compare metrics
    print("\n" + "=" * 60)
    print("Performance Comparison")
    print("=" * 60)
    print(f"{'Metric':<20} {'Risk Parity':>15} {'Equal Weight':>15} {'Difference':>15}")
    print("-" * 60)

    metrics = ['Total Return (%)', 'Sharpe Ratio', 'Max Drawdown (%)', 'Win Rate (%)']
    for metric in metrics:
        rp_val = rp_result.statistics[metric]
        eq_val = eq_result.statistics[metric]
        diff = rp_val - eq_val
        print(f"{metric:<20} {rp_val:>15.2f} {eq_val:>15.2f} {diff:>+15.2f}")

    # Visualize comparison
    fig, axes = plt.subplots(3, 1, figsize=(12, 12))

    # Plot 1: NAV comparison
    rp_result.summary['nav'].plot(ax=axes[0], label='Risk Parity', linewidth=2)
    eq_result.summary['nav'].plot(ax=axes[0], label='Equal Weight', linewidth=2, linestyle='--')
    axes[0].set_title('Portfolio Performance Comparison')
    axes[0].set_ylabel('NAV (starts at 1000)')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Plot 2: Drawdown comparison
    rp_nav = rp_result.summary['nav']
    eq_nav = eq_result.summary['nav']
    rp_dd = (rp_nav / rp_nav.cummax() - 1) * 100
    eq_dd = (eq_nav / eq_nav.cummax() - 1) * 100
    rp_dd.plot(ax=axes[1], label='Risk Parity', linewidth=2)
    eq_dd.plot(ax=axes[1], label='Equal Weight', linewidth=2, linestyle='--')
    axes[1].fill_between(rp_dd.index, rp_dd, 0, alpha=0.2)
    axes[1].set_title('Drawdown Comparison (%)')
    axes[1].set_ylabel('Drawdown (%)')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # Plot 3: Metrics bar chart
    comparison_df = pd.DataFrame({
        'Risk Parity': [rp_result.statistics[m] for m in metrics],
        'Equal Weight': [eq_result.statistics[m] for m in metrics]
    }, index=metrics)
    comparison_df.plot(kind='bar', ax=axes[2], rot=0)
    axes[2].set_title('Performance Metrics Comparison')
    axes[2].set_ylabel('Value')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.show()

    print("\n" + "=" * 60)
    print("✓ Risk parity portfolio backtested and compared!")
    print("=" * 60)

    # Interpretation
    rp_sharpe = rp_result.statistics['Sharpe Ratio']
    eq_sharpe = eq_result.statistics['Sharpe Ratio']
    sharpe_improvement = ((rp_sharpe / eq_sharpe) - 1) * 100 if eq_sharpe != 0 else 0

    print("\nInterpretation:")
    if rp_sharpe > eq_sharpe * 1.1:  # 10% better
        print(f"  ✓ Risk parity shows significant improvement ({sharpe_improvement:+.1f}% Sharpe)")
        print("    Worth the added complexity!")
    elif rp_sharpe > eq_sharpe:
        print(f"  ✓ Risk parity shows modest improvement ({sharpe_improvement:+.1f}% Sharpe)")
        print("    Consider if improvement justifies complexity.")
    else:
        print(f"  ⚠️  Risk parity underperforms equal weight ({sharpe_improvement:+.1f}% Sharpe)")
        print("    Consider using equal weight (1/N paradox).")
