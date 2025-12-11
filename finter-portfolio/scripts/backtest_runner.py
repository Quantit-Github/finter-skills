#!/usr/bin/env python3
"""
Backtest Runner for Finter Portfolio Strategies

Automates backtesting of portfolio strategies with comprehensive result reporting.
Generates CSV results and performance chart PNG.

Usage:
    python backtest_runner.py --code portfolio.py --universe kr_stock
    python backtest_runner.py --code portfolio.py --universe kr_stock --no-validate
    python backtest_runner.py --code portfolio.py --universe us_stock --start 20200101

Output files:
    backtest_summary.csv  - NAV time series
    backtest_stats.csv    - Performance metrics
    chart.png             - Performance chart (unless --no-chart)
"""

import argparse
import importlib.util
import sys
from datetime import datetime
from pathlib import Path

try:
    import numpy as np
    import pandas as pd
    from finter.backtest import Simulator
except ImportError as e:
    print(f"Error: Required package not found - {e}")
    print("Please install: pip install finter pandas numpy")
    sys.exit(1)


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def load_portfolio_from_file(filepath):
    """
    Load Portfolio class from Python file.

    Parameters
    ----------
    filepath : str or Path
        Path to Python file containing Portfolio class

    Returns
    -------
    class
        Portfolio class from the file
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"Portfolio file not found: {filepath}")

    # Load module from file
    spec = importlib.util.spec_from_file_location("portfolio_module", filepath)
    module = importlib.util.module_from_spec(spec)
    sys.modules["portfolio_module"] = module
    spec.loader.exec_module(module)

    # Get Portfolio class
    if not hasattr(module, "Portfolio"):
        raise ValueError(f"File must contain a class named 'Portfolio': {filepath}")

    return module.Portfolio


def print_section(title):
    """Print formatted section header"""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print("=" * 70)


def print_metrics(stats, title="Performance Metrics"):
    """Print formatted performance metrics"""
    print_section(title)

    # Key metrics
    key_metrics = [
        "Total Return (%)",
        "Sharpe Ratio",
        "Max Drawdown (%)",
        "Hit Ratio (%)",
    ]

    for metric in key_metrics:
        if metric in stats:
            value = stats[metric]
            print(f"  {metric:.<50} {value:>12.2f}")

    # Additional metrics
    print("\n  Additional Metrics:")
    other_metrics = [k for k in stats.index if k not in key_metrics]
    for metric in sorted(other_metrics):
        value = stats[metric]
        if isinstance(value, (int, float, np.number)):
            print(f"    {metric:.<48} {value:>12.2f}")


def validate_positions(positions):
    """
    Validate position DataFrame for common issues.

    Parameters
    ----------
    positions : pd.DataFrame
        Position DataFrame to validate

    Returns
    -------
    dict
        Validation results with warnings and errors
    """
    issues = {"errors": [], "warnings": []}

    # Check for empty DataFrame
    if positions.empty:
        issues["errors"].append("Position DataFrame is empty")
        return issues

    # Check row sums
    row_sums = positions.sum(axis=1)
    max_sum = row_sums.max()

    if max_sum > 1e8 + 1000:  # Allow small rounding error
        issues["errors"].append(f"Row sums exceed 1e8 (total AUM). Max: {max_sum:.0f}")

    # Check for NaN values
    nan_count = positions.isnull().sum().sum()
    if nan_count > 0:
        nan_pct = nan_count / positions.size * 100
        issues["warnings"].append(
            f"Contains {nan_count} NaN values ({nan_pct:.2f}% of total)"
        )

    # Check for zero positions
    zero_positions = (row_sums == 0).sum()
    if zero_positions > 0:
        zero_pct = zero_positions / len(positions) * 100
        issues["warnings"].append(
            f"{zero_positions} days with zero positions ({zero_pct:.1f}% of days)"
        )

    # Check for negative values
    if (positions < 0).any().any():
        issues["warnings"].append("Contains negative positions (short positions)")

    return issues


# ============================================================
# MAIN BACKTEST WORKFLOW
# ============================================================


def run_backtest(
    portfolio_file, start_date, end_date, universe, output_dir=None, generate_chart=True
):
    """
    Run complete backtest workflow.

    Validation runs BEFORE backtest - files are only generated if validation passes.

    Parameters
    ----------
    portfolio_file : str
        Path to portfolio strategy file
    start_date : int
        Start date in YYYYMMDD format
    end_date : int
        End date in YYYYMMDD format
    universe : str
        Market universe ("kr_stock", "us_stock", etc.)
    output_dir : str or Path, optional
        Output directory for results (default: current working directory)
    generate_chart : bool
        Whether to generate chart PNG (default: True)

    Returns
    -------
    bool
        True if backtest completed successfully, False otherwise
    """
    print_section("Backtest Configuration")
    print(f"  Portfolio file: {portfolio_file}")
    print(f"  Date range: {start_date} - {end_date}")
    print(f"  Universe: {universe}")

    # Load Portfolio class
    print_section("Loading Portfolio Strategy")
    try:
        PortfolioClass = load_portfolio_from_file(portfolio_file)
        print("  ✓ Successfully loaded Portfolio class")

        if PortfolioClass.__doc__:
            print("\n  Strategy Description:")
            for line in PortfolioClass.__doc__.strip().split("\n"):
                print(f"    {line}")
    except Exception as e:
        print(f"  ✗ Error loading Portfolio class: {e}")
        return False

    # Generate positions
    print_section("Generating Positions")
    try:
        portfolio = PortfolioClass()
        positions = portfolio.get(start_date, end_date)

        print("  ✓ Positions generated successfully")
        print(f"  Shape: {positions.shape}")
        print(f"  Date range: {positions.index[0]} to {positions.index[-1]}")
        print(f"  Trading days: {len(positions)}")
        print(f"  Number of assets: {positions.shape[1]}")
    except Exception as e:
        print(f"  ✗ Error generating positions: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Validate positions
    print_section("Position Validation")
    validation = validate_positions(positions)

    if validation["errors"]:
        print("  ✗ ERRORS FOUND:")
        for error in validation["errors"]:
            print(f"    - {error}")
        return False
    else:
        print("  ✓ No errors found")

    if validation["warnings"]:
        print("\n  ⚠️  WARNINGS:")
        for warning in validation["warnings"]:
            print(f"    - {warning}")

    # Show position statistics
    row_sums = positions.sum(axis=1)
    print("\n  Position Statistics:")
    print(
        f"    Row sum - Min: {row_sums.min():.0f}, "
        f"Max: {row_sums.max():.0f}, "
        f"Mean: {row_sums.mean():.0f}"
    )

    avg_assets_per_day = (positions > 0).sum(axis=1).mean()
    print(f"    Average assets per day: {avg_assets_per_day:.1f}")

    # Run portfolio validation (path independence, trading days, weight sum) BEFORE backtest
    print_section("Portfolio Validation")
    try:
        from portfolio_validator import (
            check_path_independence,
            check_trading_days,
            check_weight_sum,
            load_portfolio_from_file as load_portfolio_validator,
        )

        # Map market_type to universe for validation
        universe_map = {
            "btcusdt_spot_binance": "raw",
        }
        val_universe = universe_map.get(universe, universe)

        PortfolioClassForValidation = load_portfolio_validator(portfolio_file)

        # Check 1: Path Independence
        print("\n  1. Path Independence")
        passed1, msg1, _ = check_path_independence(PortfolioClassForValidation)
        status1 = "✓ PASS" if passed1 else "✗ FAIL"
        print(f"     {status1} - {msg1}")

        # Check 2: Trading Days
        print("\n  2. Trading Days Index")
        passed2, msg2, _ = check_trading_days(PortfolioClassForValidation, val_universe)
        status2 = "✓ PASS" if passed2 else "✗ FAIL"
        print(f"     {status2} - {msg2}")

        # Check 3: Weight Sum (Portfolio-specific)
        print("\n  3. Weight Sum (~1.0)")
        passed3, msg3, _ = check_weight_sum(PortfolioClassForValidation)
        status3 = "✓ PASS" if passed3 else "✗ FAIL"
        print(f"     {status3} - {msg3}")

        if not (passed1 and passed2 and passed3):
            print("\n  ✗ Validation FAILED - fix portfolio.py before backtest!")
            print("    No output files generated.")
            return False
        else:
            print("\n  ✓ All validations passed!")

    except ImportError:
        print("  ⚠️  portfolio_validator.py not found, skipping validation")
    except Exception as e:
        print(f"  ⚠️  Validation error: {e}")
        print("    Continuing with backtest...")

    # Run backtest
    print_section("Running Backtest")
    try:
        simulator = Simulator(
            market_type=universe,
        )

        result = simulator.run(position=positions)
        print("  ✓ Backtest completed successfully")

    except Exception as e:
        print(f"  ✗ Error running backtest: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Print results
    print_metrics(result.statistics)

    # Save results
    print_section("Saving Results")

    # Determine output directory
    out_dir = Path(output_dir) if output_dir else Path.cwd()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Save summary (fixed filename, no timestamp)
    summary_file = out_dir / "backtest_summary.csv"
    result.summary.to_csv(summary_file)
    print(f"  ✓ Summary saved: {summary_file}")
    print("    Note: NAV starts at 1000 (initial portfolio value)")

    # Save statistics
    stats_file = out_dir / "backtest_stats.csv"
    result.statistics.to_csv(stats_file)
    print(f"  ✓ Statistics saved: {stats_file}")

    # Generate chart
    if generate_chart:
        print_section("Generating Chart")
        try:
            from chart_generator import create_performance_chart, load_backtest_data

            nav_series, stats_dict = load_backtest_data(summary_file, stats_file)
            chart_file = out_dir / "chart.png"
            create_performance_chart(
                nav_series=nav_series,
                stats=stats_dict,
                output_path=chart_file,
                size="thumbnail",
                title="Portfolio Performance",
            )
            print(f"  ✓ Chart saved: {chart_file}")
        except ImportError:
            print("  ⚠️  chart_generator not found, skipping chart generation")
        except Exception as e:
            print(f"  ⚠️  Chart generation failed: {e}")

    print_section("Backtest Complete")
    print(f"  All results saved to: {out_dir}")

    return True


# ============================================================
# COMMAND LINE INTERFACE
# ============================================================


def main():
    parser = argparse.ArgumentParser(
        description="Backtest Finter portfolio strategies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python backtest_runner.py --code portfolio.py --universe kr_stock
  python backtest_runner.py --code portfolio.py --universe kr_stock --no-validate
  python backtest_runner.py --code portfolio.py --universe us_stock --start 20200101
  python backtest_runner.py --code portfolio.py --universe kr_stock --no-chart
        """,
    )

    parser.add_argument(
        "--code", required=True, help="Path to Python file containing Portfolio class"
    )

    parser.add_argument(
        "--start",
        type=int,
        default=20200101,
        help="Start date in YYYYMMDD format (default: 20200101)",
    )

    parser.add_argument(
        "--end",
        type=int,
        default=int(datetime.now().strftime("%Y%m%d")),
        help="End date in YYYYMMDD format (default: today)",
    )

    parser.add_argument(
        "--universe",
        required=True,
        choices=[
            "kr_stock",
            "us_stock",
            "vn_stock",
            "id_stock",
            "us_etf",
            "btcusdt_spot_binance",
        ],
        help="Market universe (required)",
    )

    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for results (default: current directory)",
    )

    parser.add_argument(
        "--no-chart",
        action="store_true",
        help="Skip chart PNG generation",
    )

    args = parser.parse_args()

    # Run backtest (validation runs BEFORE backtest, files only generated on success)
    success = run_backtest(
        portfolio_file=args.code,
        start_date=args.start,
        end_date=args.end,
        universe=args.universe,
        output_dir=args.output_dir,
        generate_chart=not args.no_chart,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
