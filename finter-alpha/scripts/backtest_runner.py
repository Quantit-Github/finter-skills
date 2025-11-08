#!/usr/bin/env python3
"""
Backtest Runner for Finter Alpha Strategies

Automates backtesting of alpha strategies with comprehensive result reporting.

Usage:
    python backtest_runner.py --code alpha.py
    python backtest_runner.py --code alpha.py --start 20200101 --end 20241231
    python backtest_runner.py --code alpha.py --universe us_stock
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


def load_alpha_from_file(filepath):
    """
    Load Alpha class from Python file.

    Parameters
    ----------
    filepath : str or Path
        Path to Python file containing Alpha class

    Returns
    -------
    class
        Alpha class from the file
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"Alpha file not found: {filepath}")

    # Load module from file
    spec = importlib.util.spec_from_file_location("alpha_module", filepath)
    module = importlib.util.module_from_spec(spec)
    sys.modules["alpha_module"] = module
    spec.loader.exec_module(module)

    # Get Alpha class
    if not hasattr(module, "Alpha"):
        raise ValueError(f"File must contain a class named 'Alpha': {filepath}")

    return module.Alpha


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
        "Win Rate (%)",
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


def run_backtest(alpha_file, start_date, end_date, universe):
    """
    Run complete backtest workflow.

    Parameters
    ----------
    alpha_file : str
        Path to alpha strategy file
    start_date : int
        Start date in YYYYMMDD format
    end_date : int
        End date in YYYYMMDD format
    universe : str
        Market universe ("kr_stock", "us_stock", etc.)

    Returns
    -------
    bool
        True if backtest completed successfully, False otherwise
    """
    print_section("Backtest Configuration")
    print(f"  Alpha file: {alpha_file}")
    print(f"  Date range: {start_date} - {end_date}")
    print(f"  Universe: {universe}")

    # Load Alpha class
    print_section("Loading Alpha Strategy")
    try:
        AlphaClass = load_alpha_from_file(alpha_file)
        print("  ✓ Successfully loaded Alpha class")

        if AlphaClass.__doc__:
            print("\n  Strategy Description:")
            for line in AlphaClass.__doc__.strip().split("\n"):
                print(f"    {line}")
    except Exception as e:
        print(f"  ✗ Error loading Alpha class: {e}")
        return False

    # Generate positions
    print_section("Generating Positions")
    try:
        alpha = AlphaClass()
        positions = alpha.get(start_date, end_date)

        print("  ✓ Positions generated successfully")
        print(f"  Shape: {positions.shape}")
        print(f"  Date range: {positions.index[0]} to {positions.index[-1]}")
        print(f"  Trading days: {len(positions)}")
        print(f"  Number of stocks: {positions.shape[1]}")
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

    avg_stocks_per_day = (positions > 0).sum(axis=1).mean()
    print(f"    Average stocks per day: {avg_stocks_per_day:.1f}")

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
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save to current working directory
    output_dir = Path.cwd()

    # Save summary
    summary_file = output_dir / f"backtest_summary_{timestamp}.csv"
    result.summary.to_csv(summary_file)
    print(f"  ✓ Summary saved: {summary_file}")
    print(f"    Note: NAV starts at 1000 (initial portfolio value)")

    # Save statistics
    stats_file = output_dir / f"backtest_stats_{timestamp}.csv"
    result.statistics.to_csv(stats_file)
    print(f"  ✓ Statistics saved: {stats_file}")

    # Save positions
    positions_file = output_dir / f"positions_{timestamp}.csv"
    positions.to_csv(positions_file)
    print(f"  ✓ Positions saved: {positions_file}")

    print_section("Backtest Complete")
    print(f"  All results saved with timestamp: {timestamp}")

    return True


# ============================================================
# COMMAND LINE INTERFACE
# ============================================================


def main():
    parser = argparse.ArgumentParser(
        description="Backtest Finter alpha strategies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python backtest_runner.py --code alpha.py
  python backtest_runner.py --code alpha.py --start 20200101 --end 20241231
  python backtest_runner.py --code alpha.py --universe us_stock
        """,
    )

    parser.add_argument(
        "--code", required=True, help="Path to Python file containing Alpha class"
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
        default=20241231,
        help="End date in YYYYMMDD format (default: 20241231)",
    )

    parser.add_argument(
        "--universe",
        default="kr_stock",
        choices=["kr_stock", "us_stock"],
        help="Market universe (default: kr_stock)",
    )

    args = parser.parse_args()

    # Run backtest
    success = run_backtest(
        alpha_file=args.code,
        start_date=args.start,
        end_date=args.end,
        universe=args.universe,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
