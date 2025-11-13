"""
Mean-Variance Optimization (MVO) Portfolio - Markowitz Approach

This strategy uses Markowitz portfolio theory to find weights that
maximize the Sharpe ratio (risk-adjusted returns).

Use Cases:
- Alphas have low correlation (<0.3)
- Want theory-backed optimal allocation
- Performance maximization is priority
- Have sufficient historical data (2+ years)

Advantages:
- Theory-backed (Nobel Prize)
- Optimal under assumptions
- Accounts for both risk and return
- Considers correlations

Disadvantages:
- Very unstable (small input changes → large weight changes)
- Sensitive to estimation errors (garbage in, garbage out)
- Computational cost
- Often produces extreme weights (0% or 100%)

Tips to Stabilize:
1. Use longer lookback period (252+ days)
2. Add weight constraints (min/max limits)
3. Add turnover penalty (reduce rebalancing)
4. Use shrinkage on covariance matrix
5. Consider equal weight as baseline first
"""

from finter import BasePortfolio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy.optimize import minimize


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
    Mean-Variance Optimization Portfolio

    Maximizes Sharpe ratio using Markowitz portfolio theory.
    Uses rolling window optimization with constraints to prevent extreme weights.
    """

    # List of alpha strategies to be combined
    alpha_list = [
        "us.compustat.stock.ywcho.alphathon2_yw_di",
        "us.compustat.stock.jyjung.insur_spxndx_roe",
        "us.compustat.stock.sypark.US_BDC_v4"
    ]

    def weight(self, start: int, end: int) -> pd.DataFrame:
        """
        Calculate optimal weights using mean-variance optimization.

        Args:
            start (int): Start date in YYYYMMDD format
            end (int): End date in YYYYMMDD format

        Returns:
            pd.DataFrame: Weight DataFrame (date x alpha_names)
                         Weights sum to 1.0 per date
        """
        # Use 1-year lookback for MVO
        # Longer lookback = more stable estimates
        lookback = 252  # 1 year

        # Load alpha returns with sufficient buffer
        preload_start = calculate_previous_start_date(start, lookback + 250)
        alpha_return_df = self.alpha_pnl_df('us_stock', preload_start, end)

        # Clean consecutive 1's
        find_1 = (alpha_return_df == 1) & (alpha_return_df.shift(1) == 1)
        alpha_return_df = alpha_return_df.mask(find_1, np.nan).ffill(limit=5)

        # Calculate rolling optimization
        weights_list = []
        dates_list = []

        for i in range(lookback, len(alpha_return_df)):
            # Get lookback window
            window = alpha_return_df.iloc[i - lookback:i]

            # Convert to standard returns (0-baseline)
            returns = window - 1.0

            # Calculate mean returns and covariance
            mu = returns.mean().values
            cov = returns.cov().values

            # Optimize weights
            n = len(mu)
            init_weights = np.ones(n) / n

            # Objective: Negative Sharpe ratio (minimize)
            def neg_sharpe(w):
                port_return = np.dot(w, mu)
                port_vol = np.sqrt(np.dot(w, np.dot(cov, w)))
                # Add small epsilon to avoid division by zero
                return -port_return / (port_vol + 1e-6)

            # Constraints: weights sum to 1
            constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}

            # Bounds: long-only, max 60% per alpha (prevent concentration)
            # Adjust these bounds based on your risk tolerance:
            # - (0, 1): No constraint (may result in 100% allocation)
            # - (0, 0.5): Max 50% per alpha (more diversified)
            # - (0.1, 0.6): Min 10%, max 60% (forced diversification)
            bounds = tuple((0, 0.6) for _ in range(n))

            # Optimize
            result = minimize(
                neg_sharpe,
                init_weights,
                method='SLSQP',  # Sequential Least Squares Programming
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 100}
            )

            if result.success:
                weights_list.append(result.x)
            else:
                # Fallback to equal weight on optimization failure
                weights_list.append(np.ones(n) / n)

            dates_list.append(alpha_return_df.index[i])

        # Create weights DataFrame
        weights_df = pd.DataFrame(
            weights_list,
            index=dates_list,
            columns=alpha_return_df.columns
        )

        # Already lagged by construction (using past data only)
        # But shift(1) for extra safety
        return weights_df.shift(1).loc[str(start):str(end)]

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
    print("Generating mean-variance optimal weights...")
    print("(This may take a minute due to optimization...)")
    weights = portfolio.weight(20240101, 20241231)

    # Validate
    print("\n" + "=" * 60)
    print("Mean-Variance Optimization Portfolio Validation")
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

    # Calculate weight turnover (how much weights change)
    weight_change = weights.diff().abs().sum(axis=1)
    print(f"\nWeight Turnover (daily):")
    print(f"  Mean: {weight_change.mean():.4f}")
    print(f"  Median: {weight_change.median():.4f}")
    print(f"  Max: {weight_change.max():.4f}")

    # Analyze alpha characteristics
    print("\n" + "=" * 60)
    print("Alpha Analysis")
    print("=" * 60)

    # Load alpha returns for analysis
    alpha_return_df = portfolio.alpha_pnl_df('us_stock', 20230101, 20241231)
    find_1 = (alpha_return_df == 1) & (alpha_return_df.shift(1) == 1)
    alpha_return_df = alpha_return_df.mask(find_1, np.nan).ffill(limit=5)

    # Calculate metrics
    returns = alpha_return_df - 1.0
    mean_return = returns.mean() * 252  # Annualized
    volatility = returns.std() * np.sqrt(252)  # Annualized
    sharpe = mean_return / volatility

    print("\nAlpha Characteristics (Annualized):")
    metrics_df = pd.DataFrame({
        'Return': mean_return,
        'Volatility': volatility,
        'Sharpe': sharpe
    }).sort_values('Sharpe', ascending=False)
    print(metrics_df)

    print("\nAverage Weight by Alpha:")
    print(weights.mean().sort_values(ascending=False))

    print("\nCorrelation Matrix:")
    print(alpha_return_df.corr().round(3))

    # Visualize
    import matplotlib.pyplot as plt
    import seaborn as sns

    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

    # Plot 1: Weight time series
    ax1 = fig.add_subplot(gs[0, :2])
    weights.plot(ax=ax1, title='Mean-Variance Optimal Weights Over Time')
    ax1.set_ylabel('Weight')
    ax1.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    ax1.axhline(y=1.0/len(portfolio.alpha_list), color='gray', linestyle='--', alpha=0.5)

    # Plot 2: Weight distribution
    ax2 = fig.add_subplot(gs[0, 2])
    weights.boxplot(ax=ax2)
    ax2.set_title('Weight Distribution')
    ax2.set_ylabel('Weight')
    ax2.axhline(y=1.0/len(portfolio.alpha_list), color='red', linestyle='--', label='Equal')

    # Plot 3: Weight sum check
    ax3 = fig.add_subplot(gs[1, 0])
    weight_sum.plot(ax=ax3, title='Weight Sum (should be 1.0)')
    ax3.axhline(y=1.0, color='red', linestyle='--')
    ax3.set_ylim([0.99, 1.01])
    ax3.set_ylabel('Sum')

    # Plot 4: Weight turnover
    ax4 = fig.add_subplot(gs[1, 1])
    weight_change.plot(ax=ax4, title='Weight Turnover (Daily Change)')
    ax4.set_ylabel('Total Change')

    # Plot 5: Correlation heatmap
    ax5 = fig.add_subplot(gs[1, 2])
    sns.heatmap(alpha_return_df.corr(), annot=True, cmap='coolwarm', center=0,
                ax=ax5, fmt='.2f', square=True, cbar_kws={'label': 'Correlation'})
    ax5.set_title('Alpha Correlation')

    # Plot 6: Cumulative returns
    ax6 = fig.add_subplot(gs[2, :2])
    cumulative_returns = (1 + returns).cumprod()
    cumulative_returns.plot(ax=ax6, title='Alpha Cumulative Returns')
    ax6.set_ylabel('Cumulative Return')
    ax6.legend(loc='center left', bbox_to_anchor=(1, 0.5))

    # Plot 7: Risk-return scatter
    ax7 = fig.add_subplot(gs[2, 2])
    ax7.scatter(volatility, mean_return, s=100, alpha=0.6)
    for i, name in enumerate(alpha_return_df.columns):
        ax7.annotate(name.split('.')[-1][:10], (volatility.iloc[i], mean_return.iloc[i]),
                    fontsize=8, ha='right')
    ax7.set_xlabel('Volatility (Annualized)')
    ax7.set_ylabel('Return (Annualized)')
    ax7.set_title('Risk-Return Profile')
    ax7.grid(True, alpha=0.3)

    plt.show()

    print("\n" + "=" * 60)
    print("✓ Mean-variance optimization portfolio validated successfully!")
    print("=" * 60)
    print("\nNOTE: MVO can be unstable. Consider:")
    print("  - Using longer lookback period (504 days)")
    print("  - Adding tighter weight constraints (e.g., 0.2-0.4)")
    print("  - Comparing with equal weight and risk parity")
    print("  - Monitoring turnover (high turnover = high transaction costs)")

    # ========================================================================
    # BACKTESTING & COMPARISON WITH EQUAL WEIGHT
    # ========================================================================
    print("\n" + "=" * 60)
    print("Portfolio Backtesting & Equal Weight Comparison")
    print("=" * 60)

    from finter.backtest import Simulator

    # Backtest mean-variance portfolio
    print("\nBacktesting mean-variance optimal portfolio...")
    simulator = Simulator(market_type="us_stock")
    mv_result = simulator.run(position=portfolio.get(20240101, 20241231))

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
    print(f"{'Metric':<20} {'MVO':>15} {'Equal Weight':>15} {'Difference':>15}")
    print("-" * 60)

    metrics = ['Total Return (%)', 'Sharpe Ratio', 'Max Drawdown (%)', 'Hit Ratio (%)']
    for metric in metrics:
        mv_val = mv_result.statistics[metric]
        eq_val = eq_result.statistics[metric]
        diff = mv_val - eq_val
        print(f"{metric:<20} {mv_val:>15.2f} {eq_val:>15.2f} {diff:>+15.2f}")

    # Calculate turnover for MVO
    weight_change = weights.diff().abs().sum(axis=1)
    print(f"\n{'Turnover (daily avg)':<20} {weight_change.mean():>15.2f} {'N/A':>15} {'-':>15}")

    # Visualize comparison
    fig, axes = plt.subplots(3, 1, figsize=(12, 12))

    # Plot 1: NAV comparison
    mv_result.summary['nav'].plot(ax=axes[0], label='Mean-Variance', linewidth=2)
    eq_result.summary['nav'].plot(ax=axes[0], label='Equal Weight', linewidth=2, linestyle='--')
    axes[0].set_title('Portfolio Performance Comparison')
    axes[0].set_ylabel('NAV (starts at 1000)')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Plot 2: Drawdown comparison
    mv_nav = mv_result.summary['nav']
    eq_nav = eq_result.summary['nav']
    mv_dd = (mv_nav / mv_nav.cummax() - 1) * 100
    eq_dd = (eq_nav / eq_nav.cummax() - 1) * 100
    mv_dd.plot(ax=axes[1], label='Mean-Variance', linewidth=2)
    eq_dd.plot(ax=axes[1], label='Equal Weight', linewidth=2, linestyle='--')
    axes[1].fill_between(mv_dd.index, mv_dd, 0, alpha=0.2)
    axes[1].set_title('Drawdown Comparison (%)')
    axes[1].set_ylabel('Drawdown (%)')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # Plot 3: Metrics bar chart
    comparison_df = pd.DataFrame({
        'Mean-Variance': [mv_result.statistics[m] for m in metrics],
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
    print("✓ Mean-variance portfolio backtested and compared!")
    print("=" * 60)

    # Interpretation
    mv_sharpe = mv_result.statistics['Sharpe Ratio']
    eq_sharpe = eq_result.statistics['Sharpe Ratio']
    sharpe_improvement = ((mv_sharpe / eq_sharpe) - 1) * 100 if eq_sharpe != 0 else 0

    print("\nInterpretation:")
    if mv_sharpe > eq_sharpe * 1.15:  # 15% better (higher bar for complex MVO)
        print(f"  ✓ MVO shows significant improvement ({sharpe_improvement:+.1f}% Sharpe)")
        print("    Worth the added complexity and computational cost!")
    elif mv_sharpe > eq_sharpe:
        print(f"  ⚠️  MVO shows modest improvement ({sharpe_improvement:+.1f}% Sharpe)")
        print(f"    Turnover: {weight_change.mean():.3f} (monitor transaction costs)")
        print("    Consider if improvement justifies complexity.")
    else:
        print(f"  ⚠️  MVO underperforms equal weight ({sharpe_improvement:+.1f}% Sharpe)")
        print("    1/N paradox: Simple equal weight beats optimization!")
        print("    Try:")
        print("      - Longer lookback period (504 days)")
        print("      - Tighter weight constraints")
        print("      - Risk parity instead of MVO")
