#!/usr/bin/env python3
"""Cost Deduction Effect Analysis.

Compare naive equal weight (mean → cumprod) vs Finter backtest (with costs).
This shows the impact of transaction costs and turnover reduction from
combining multiple alphas.

Usage:
    python cost_analysis.py --portfolio portfolio.py --market vn_stock
    python cost_analysis.py --alpha-list alpha1,alpha2,alpha3 --market us_stock
"""

import argparse
import importlib.util
import sys
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def load_portfolio_class(portfolio_path: str):
    """Dynamically load Portfolio class from file."""
    spec = importlib.util.spec_from_file_location("portfolio_module", portfolio_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Portfolio


def calculate_previous_start_date(start_date: int, lookback_days: int) -> int:
    """Calculate start date for preloading data."""
    start = datetime.strptime(str(start_date), "%Y%m%d")
    previous_start = start - timedelta(days=lookback_days)
    return int(previous_start.strftime("%Y%m%d"))


def get_naive_ew_nav(alpha_pnl_df: pd.DataFrame, start: int, end: int) -> pd.Series:
    """Calculate naive equal weight NAV (mean → cumprod).

    This ignores transaction costs - just average returns and compound.

    Args:
        alpha_pnl_df: DataFrame of alpha daily returns (date x alphas)
        start: Start date (YYYYMMDD)
        end: End date (YYYYMMDD)

    Returns:
        NAV series starting at 1000
    """
    # Slice to date range
    df = alpha_pnl_df.loc[str(start):str(end)].copy()

    # Clean consecutive 1's (data artifacts)
    find_1 = (df == 1) & (df.shift(1) == 1)
    df = df.mask(find_1, np.nan).ffill(limit=5)

    # Equal weight average of daily returns
    daily_returns = df.mean(axis=1)

    # Cumprod for NAV (starting at 1000)
    nav = (1 + daily_returns).cumprod() * 1000

    return nav


def get_finter_backtest_nav(
    portfolio_class,
    market: str,
    start: int,
    end: int,
) -> tuple[pd.Series, dict]:
    """Run Finter backtest and get NAV with costs.

    Args:
        portfolio_class: Portfolio class with alpha_list and weight()
        market: Market type (us_stock, vn_stock, etc.)
        start: Start date
        end: End date

    Returns:
        Tuple of (NAV series, statistics dict)
    """
    from finter.backtest import Simulator

    portfolio = portfolio_class()

    simulator = Simulator(market_type=market)
    result = simulator.run(position=portfolio.get(start, end))

    return result.summary['nav'], result.statistics


def plot_cost_comparison(
    naive_nav: pd.Series,
    finter_nav: pd.Series,
    stats: dict,
    output_path: str = "cost_analysis.png",
) -> None:
    """Plot comparison of naive EW vs Finter backtest.

    Shows:
    - Top: NAV comparison
    - Bottom: Cost drag (cumulative difference)
    """
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))

    # Normalize both to start at 1000
    naive_normalized = naive_nav / naive_nav.iloc[0] * 1000
    finter_normalized = finter_nav / finter_nav.iloc[0] * 1000

    # Align indices
    common_idx = naive_normalized.index.intersection(finter_normalized.index)
    naive_plot = naive_normalized.loc[common_idx]
    finter_plot = finter_normalized.loc[common_idx]

    # Top plot: NAV comparison
    axes[0].plot(naive_plot.index, naive_plot.values, label='Naive EW (no costs)',
                 linewidth=2, color='blue', linestyle='--')
    axes[0].plot(finter_plot.index, finter_plot.values, label='Finter EW (with costs)',
                 linewidth=2, color='green')
    axes[0].set_title('Portfolio NAV: Naive EW vs Finter Backtest', fontsize=14)
    axes[0].set_ylabel('NAV (starts at 1000)')
    axes[0].legend(loc='upper left')
    axes[0].grid(True, alpha=0.3)

    # Add stats annotation
    naive_total_return = (naive_plot.iloc[-1] / naive_plot.iloc[0] - 1) * 100
    finter_total_return = (finter_plot.iloc[-1] / finter_plot.iloc[0] - 1) * 100
    cost_drag = naive_total_return - finter_total_return

    stats_text = (
        f"Naive Return: {naive_total_return:.1f}%\n"
        f"Finter Return: {finter_total_return:.1f}%\n"
        f"Cost Drag: {cost_drag:.1f}%\n"
        f"Finter Sharpe: {stats.get('Sharpe Ratio', 0):.2f}"
    )
    axes[0].text(0.02, 0.98, stats_text, transform=axes[0].transAxes,
                 fontsize=10, verticalalignment='top',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # Bottom plot: Cost drag over time
    cost_drag_series = (naive_plot - finter_plot) / finter_plot * 100
    axes[1].fill_between(cost_drag_series.index, 0, cost_drag_series.values,
                         alpha=0.5, color='red')
    axes[1].plot(cost_drag_series.index, cost_drag_series.values,
                 linewidth=1, color='darkred')
    axes[1].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    axes[1].set_title('Cost Drag: (Naive - Finter) / Finter (%)', fontsize=14)
    axes[1].set_ylabel('Cost Drag (%)')
    axes[1].set_xlabel('Date')
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\nChart saved to: {output_path}")

    # Show in Jupyter if available
    try:
        plt.show()
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="Compare naive EW vs Finter backtest (cost analysis)"
    )
    parser.add_argument("--portfolio", help="Path to portfolio.py file")
    parser.add_argument("--alpha-list", help="Comma-separated alpha list entries")
    parser.add_argument("--market", required=True,
                        choices=["kr_stock", "us_stock", "vn_stock", "id_stock", "us_etf"],
                        help="Market type")
    parser.add_argument("--start", type=int, default=20200101, help="Start date (YYYYMMDD)")
    parser.add_argument("--end", type=int, default=None, help="End date (YYYYMMDD, default: today)")
    parser.add_argument("--output", default="cost_analysis.png", help="Output chart path")
    args = parser.parse_args()

    if args.end is None:
        args.end = int(datetime.now().strftime("%Y%m%d"))

    print("=" * 60)
    print("COST DEDUCTION EFFECT ANALYSIS")
    print("=" * 60)
    print(f"Market: {args.market}")
    print(f"Period: {args.start} - {args.end}")

    # Load portfolio
    if args.portfolio:
        print(f"\nLoading portfolio from: {args.portfolio}")
        Portfolio = load_portfolio_class(args.portfolio)
        alpha_list = Portfolio.alpha_list
    elif args.alpha_list:
        alpha_list = [a.strip() for a in args.alpha_list.split(",")]
        # Create inline Portfolio class
        from finter import BasePortfolio

        class Portfolio(BasePortfolio):
            pass
        Portfolio.alpha_list = alpha_list
    else:
        print("ERROR: Must specify --portfolio or --alpha-list")
        sys.exit(1)

    print(f"Alpha count: {len(alpha_list)}")

    # Get alpha PNL data
    print("\nLoading alpha returns...")
    portfolio = Portfolio()
    preload_start = calculate_previous_start_date(args.start, 365)
    alpha_pnl_df = portfolio.alpha_pnl_df(args.market, preload_start, args.end)
    print(f"Alpha PNL shape: {alpha_pnl_df.shape}")

    # Calculate naive EW NAV
    print("\nCalculating naive EW (mean → cumprod)...")
    naive_nav = get_naive_ew_nav(alpha_pnl_df, args.start, args.end)
    print(f"Naive NAV range: {naive_nav.iloc[0]:.0f} → {naive_nav.iloc[-1]:.0f}")

    # Run Finter backtest
    print("\nRunning Finter backtest (with costs)...")
    finter_nav, stats = get_finter_backtest_nav(Portfolio, args.market, args.start, args.end)
    print(f"Finter NAV range: {finter_nav.iloc[0]:.0f} → {finter_nav.iloc[-1]:.0f}")

    # Print comparison
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    naive_return = (naive_nav.iloc[-1] / naive_nav.iloc[0] - 1) * 100
    finter_return = (finter_nav.iloc[-1] / finter_nav.iloc[0] - 1) * 100
    cost_drag = naive_return - finter_return

    print(f"\nNaive EW Total Return: {naive_return:.2f}%")
    print(f"Finter EW Total Return: {finter_return:.2f}%")
    print(f"Cost Drag: {cost_drag:.2f}%")
    print(f"\nFinter Stats:")
    print(f"  Sharpe Ratio: {stats.get('Sharpe Ratio', 'N/A')}")
    print(f"  Max Drawdown: {stats.get('Max Drawdown (%)', 'N/A')}%")
    print(f"  Turnover: {stats.get('Turnover', 'N/A')}")

    # Plot comparison
    print("\nGenerating comparison chart...")
    plot_cost_comparison(naive_nav, finter_nav, stats, args.output)

    print("\n" + "=" * 60)
    print("INTERPRETATION")
    print("=" * 60)
    print("""
The 'Cost Drag' shows how much return is lost due to transaction costs.

- Positive cost drag = Naive EW overestimates returns
- Lower cost drag = More efficient portfolio (less turnover)

Benefits of combining alphas:
1. Turnover Reduction: Offsetting positions cancel out
2. Diversification: Lower combined volatility
3. Smoother Returns: Less extreme daily movements
""")


if __name__ == "__main__":
    main()
