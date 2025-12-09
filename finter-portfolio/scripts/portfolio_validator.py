#!/usr/bin/env python3
"""
Portfolio Strategy Validator for Finter

Validates portfolio strategies for common issues:
1. Path Independence - positions must be identical for overlapping dates
2. Trading Days Index - positions must align with universe trading days
3. Weight Sum - weights must sum to approximately 1.0 per row

Usage:
    python portfolio_validator.py --code portfolio.py --universe kr_stock
    python portfolio_validator.py --code portfolio.py --universe us_stock --verbose
"""

import argparse
import importlib.util
import sys
from pathlib import Path

import pandas as pd
from finter.data import ContentFactory


def load_portfolio_from_file(filepath):
    """Load Portfolio class from Python file."""
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Portfolio file not found: {filepath}")

    spec = importlib.util.spec_from_file_location("portfolio_module", filepath)
    module = importlib.util.module_from_spec(spec)
    sys.modules["portfolio_module"] = module
    spec.loader.exec_module(module)

    if not hasattr(module, "Portfolio"):
        raise ValueError(f"File must contain a class named 'Portfolio': {filepath}")

    return module.Portfolio


def print_header(title):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print("─" * 60)


# ============================================================
# CHECK 1: Path Independence
# ============================================================

def check_path_independence(PortfolioClass, verbose=False):
    """Check if positions are identical for overlapping dates."""
    range1 = (20200101, 20211231)
    range2 = (20210101, 20221231)
    overlap_start, overlap_end = "20210101", "20211231"

    print(f"    Range 1: {range1[0]} - {range1[1]}")
    print(f"    Range 2: {range2[0]} - {range2[1]}")

    portfolio = PortfolioClass()
    pos1 = portfolio.get(*range1)
    pos2 = portfolio.get(*range2)

    # Align to overlap
    pos1_overlap = pos1.loc[overlap_start:overlap_end]
    pos2_overlap = pos2.loc[overlap_start:overlap_end]

    common_cols = pos1_overlap.columns.intersection(pos2_overlap.columns)
    common_idx = pos1_overlap.index.intersection(pos2_overlap.index)

    # Exclude last few rows (boundary effects from shift)
    if len(common_idx) > 5:
        common_idx = common_idx[:-3]

    pos1_aligned = pos1_overlap.loc[common_idx, common_cols]
    pos2_aligned = pos2_overlap.loc[common_idx, common_cols]

    if len(common_idx) == 0:
        return False, "No overlapping dates", {}

    diff = (pos1_aligned - pos2_aligned).abs()
    max_diff = diff.max().max()

    passed = max_diff < 1e-6
    details = {
        "overlap_days": len(common_idx),
        "max_diff": max_diff,
    }

    if not passed and verbose:
        diff_mask = diff > 1e-6
        details["affected_pct"] = diff_mask.sum().sum() / diff.size * 100

    return passed, f"max_diff={max_diff:.2e}", details


# ============================================================
# CHECK 2: Trading Days Index
# ============================================================

def check_trading_days(PortfolioClass, universe, verbose=False):
    """Check if position index matches trading days."""
    # Skip for raw universe (crypto) - 8H candles, no trading_days
    if universe == "raw":
        print("    Skipped for raw universe (crypto uses 8H candles)")
        return True, "skipped (crypto)", {}

    start, end = 20230101, 20231231

    print(f"    Universe: {universe}, Range: {start} - {end}")

    cf = ContentFactory(universe, start, end)
    # Normalize trading_days to YYYYMMDD int
    trading_days = set(int(d.strftime('%Y%m%d')) for d in cf.trading_days)

    portfolio = PortfolioClass()
    positions = portfolio.get(start, end)

    # Normalize position index to YYYYMMDD int
    pos_index = positions.index
    if hasattr(pos_index, 'strftime'):
        pos_dates = set(int(d) for d in pos_index.strftime('%Y%m%d'))
    else:
        pos_dates = set(int(str(d).replace('-', '')[:8]) for d in pos_index)

    extra_days = pos_dates - trading_days

    passed = len(extra_days) == 0
    details = {
        "trading_days": len(trading_days),
        "position_days": len(pos_dates),
        "invalid_days": len(extra_days),
    }

    if not passed and verbose:
        details["invalid_samples"] = sorted(extra_days)[:5]

    return passed, f"invalid={len(extra_days)}", details


# ============================================================
# CHECK 3: Weight Sum (Portfolio-specific)
# ============================================================

def check_weight_sum(PortfolioClass, verbose=False):
    """
    Check if portfolio weights sum to approximately 1.0 per row.

    This is critical for portfolio strategies where weights should
    represent percentage allocations that sum to 100%.
    """
    start, end = 20230101, 20231231

    print(f"    Range: {start} - {end}")

    portfolio = PortfolioClass()
    positions = portfolio.get(start, end)

    # Convert positions to weights (normalize by row sum)
    row_sums = positions.sum(axis=1)

    # Check if positions are already weights (sum ~1) or positions (sum ~1e8)
    mean_sum = row_sums.mean()

    if mean_sum > 1e6:
        # Positions format (AUM-based), convert to weights
        weights = positions.div(row_sums, axis=0)
        weight_sums = weights.sum(axis=1)
        print(f"    Detected: Position format (AUM ~{mean_sum:.0f})")
    else:
        # Already in weight format
        weight_sums = row_sums
        print(f"    Detected: Weight format (sum ~{mean_sum:.4f})")

    # Check weight sums
    min_sum = weight_sums.min()
    max_sum = weight_sums.max()
    mean_sum = weight_sums.mean()
    std_sum = weight_sums.std()

    # Allow 5% tolerance from 1.0
    tolerance = 0.05
    passed = (abs(mean_sum - 1.0) < tolerance) and (std_sum < tolerance)

    details = {
        "min_weight_sum": min_sum,
        "max_weight_sum": max_sum,
        "mean_weight_sum": mean_sum,
        "std_weight_sum": std_sum,
    }

    if verbose:
        # Find problematic days
        problematic = weight_sums[abs(weight_sums - 1.0) > tolerance]
        if len(problematic) > 0:
            details["problematic_days"] = len(problematic)
            details["problematic_samples"] = problematic.head(5).to_dict()

    msg = f"mean={mean_sum:.4f}, std={std_sum:.4f}"
    return passed, msg, details


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Validate portfolio strategy for common issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Checks performed:
  1. Path Independence - get() with different end dates must return
     identical values for overlapping periods
  2. Trading Days - position index must match universe trading days
  3. Weight Sum - weights must sum to ~1.0 per row

Common fixes:
  - Path Independence: use .expanding() instead of .mean()/.std()
  - Trading Days: use cf.trading_days to align index
  - Weight Sum: normalize with weights.div(weights.sum(axis=1), axis=0)
        """,
    )

    parser.add_argument("--code", required=True, help="Path to portfolio.py")
    parser.add_argument("--universe", required=True, help="Market universe")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show details")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  Portfolio Validator")
    print("=" * 60)
    print(f"  File: {args.code}")
    print(f"  Universe: {args.universe}")

    # Load Portfolio
    try:
        PortfolioClass = load_portfolio_from_file(args.code)
    except Exception as e:
        print(f"\n  ✗ Failed to load Portfolio: {e}")
        sys.exit(1)

    results = []

    # Check 1: Path Independence
    print_header("1. Path Independence")
    try:
        passed, msg, details = check_path_independence(PortfolioClass, args.verbose)
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"\n    {status} - {msg}")
        if args.verbose and not passed and "affected_pct" in details:
            print(f"    Affected: {details['affected_pct']:.1f}% of cells")
        results.append(passed)
    except Exception as e:
        print(f"\n    ✗ ERROR - {e}")
        results.append(False)

    # Check 2: Trading Days
    print_header("2. Trading Days Index")
    try:
        passed, msg, details = check_trading_days(PortfolioClass, args.universe, args.verbose)
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"\n    {status} - {msg}")
        if args.verbose and not passed and "invalid_samples" in details:
            print(f"    Examples: {details['invalid_samples']}")
        results.append(passed)
    except Exception as e:
        print(f"\n    ✗ ERROR - {e}")
        results.append(False)

    # Check 3: Weight Sum
    print_header("3. Weight Sum (~1.0)")
    try:
        passed, msg, details = check_weight_sum(PortfolioClass, args.verbose)
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"\n    {status} - {msg}")
        if args.verbose:
            print(f"    Min: {details['min_weight_sum']:.4f}, Max: {details['max_weight_sum']:.4f}")
        results.append(passed)
    except Exception as e:
        print(f"\n    ✗ ERROR - {e}")
        results.append(False)

    # Summary
    print_header("Summary")
    all_passed = all(results)
    if all_passed:
        print("  ✓ All checks passed!")
    else:
        print(f"  ✗ {results.count(False)}/{len(results)} checks failed")

    print()
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
