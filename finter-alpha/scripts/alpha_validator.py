#!/usr/bin/env python3
"""
Alpha Strategy Validator for Finter

Validates alpha strategies for common issues:
1. Path Independence - positions must be identical for overlapping dates
2. Trading Days Index - positions must align with universe trading days

Usage:
    python alpha_validator.py --code alpha.py --universe kr_stock
    python alpha_validator.py --code alpha.py --universe us_stock --verbose
"""

import argparse
import importlib.util
import sys
from pathlib import Path

import pandas as pd
from finter.data import ContentFactory


def load_alpha_from_file(filepath):
    """Load Alpha class from Python file."""
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Alpha file not found: {filepath}")

    spec = importlib.util.spec_from_file_location("alpha_module", filepath)
    module = importlib.util.module_from_spec(spec)
    sys.modules["alpha_module"] = module
    spec.loader.exec_module(module)

    if not hasattr(module, "Alpha"):
        raise ValueError(f"File must contain a class named 'Alpha': {filepath}")

    return module.Alpha


def print_header(title):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print("─" * 60)


# ============================================================
# CHECK 1: Path Independence
# ============================================================

def check_path_independence(AlphaClass, verbose=False):
    """Check if positions are identical for overlapping dates."""
    range1 = (20200101, 20211231)
    range2 = (20210101, 20221231)
    overlap_start, overlap_end = "20210101", "20211231"

    print(f"    Range 1: {range1[0]} - {range1[1]}")
    print(f"    Range 2: {range2[0]} - {range2[1]}")

    alpha = AlphaClass()
    pos1 = alpha.get(*range1)
    pos2 = alpha.get(*range2)

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

def check_trading_days(AlphaClass, universe, verbose=False):
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

    alpha = AlphaClass()
    positions = alpha.get(start, end)

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
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Validate alpha strategy for common issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Checks performed:
  1. Path Independence - get() with different end dates must return
     identical values for overlapping periods
  2. Trading Days - position index must match universe trading days

Common fixes:
  - Path Independence: use .expanding() instead of .mean()/.std()
  - Trading Days: use cf.trading_days to align index
        """,
    )

    parser.add_argument("--code", required=True, help="Path to alpha.py")
    parser.add_argument("--universe", required=True, help="Market universe")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show details")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  Alpha Validator")
    print("=" * 60)
    print(f"  File: {args.code}")
    print(f"  Universe: {args.universe}")

    # Load Alpha
    try:
        AlphaClass = load_alpha_from_file(args.code)
    except Exception as e:
        print(f"\n  ✗ Failed to load Alpha: {e}")
        sys.exit(1)

    results = []

    # Check 1: Path Independence
    print_header("1. Path Independence")
    try:
        passed, msg, details = check_path_independence(AlphaClass, args.verbose)
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
        passed, msg, details = check_trading_days(AlphaClass, args.universe, args.verbose)
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"\n    {status} - {msg}")
        if args.verbose and not passed and "invalid_samples" in details:
            print(f"    Examples: {details['invalid_samples']}")
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
