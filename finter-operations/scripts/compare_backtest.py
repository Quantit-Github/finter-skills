#!/usr/bin/env python3
"""
Quick before/after backtest comparison.

Usage in Jupyter:
    %run .claude/skills/finter-operations/scripts/compare_backtest.py

Or import:
    from compare_backtest import compare_alphas, plot_comparison
"""

import matplotlib.pyplot as plt
import pandas as pd


def compare_alphas(
    original_class,
    fixed_class,
    universe: str,
    start: int = 20230101,
    end: int = 20241213,
) -> dict:
    """
    Compare original and fixed alpha performance.

    Args:
        original_class: Original Alpha class
        fixed_class: Fixed Alpha class
        universe: Market universe (e.g., "id_stock")
        start: Backtest start date
        end: Backtest end date

    Returns:
        dict with comparison results
    """
    from finter.backtest import Simulator

    results = {}

    # Run original
    print("Running original backtest...")
    try:
        orig_alpha = original_class()
        orig_pos = orig_alpha.get(start, end)
        sim = Simulator(market_type=universe)
        orig_result = sim.run(position=orig_pos)
        results["original"] = {
            "sharpe": orig_result.statistics.get("Sharpe Ratio", 0),
            "return": orig_result.statistics.get("Total Return (%)", 0),
            "max_dd": orig_result.statistics.get("Max Drawdown (%)", 0),
            "nav": orig_result.summary["nav"],
        }
        print(f"  Sharpe: {results['original']['sharpe']:.2f}")
    except Exception as e:
        print(f"  Original failed: {e}")
        results["original"] = {"error": str(e)}

    # Run fixed
    print("Running fixed backtest...")
    try:
        fixed_alpha = fixed_class()
        fixed_pos = fixed_alpha.get(start, end)
        sim = Simulator(market_type=universe)
        fixed_result = sim.run(position=fixed_pos)
        results["fixed"] = {
            "sharpe": fixed_result.statistics.get("Sharpe Ratio", 0),
            "return": fixed_result.statistics.get("Total Return (%)", 0),
            "max_dd": fixed_result.statistics.get("Max Drawdown (%)", 0),
            "nav": fixed_result.summary["nav"],
        }
        print(f"  Sharpe: {results['fixed']['sharpe']:.2f}")
    except Exception as e:
        print(f"  Fixed failed: {e}")
        results["fixed"] = {"error": str(e)}

    # Summary
    if "error" not in results.get("original", {}) and "error" not in results.get("fixed", {}):
        print("\n=== COMPARISON ===")
        print(f"Sharpe: {results['original']['sharpe']:.2f} -> {results['fixed']['sharpe']:.2f}")
        print(f"Return: {results['original']['return']:.1f}% -> {results['fixed']['return']:.1f}%")
        print(f"MaxDD: {results['original']['max_dd']:.1f}% -> {results['fixed']['max_dd']:.1f}%")

    return results


def plot_comparison(results: dict, save_path: str | None = None):
    """
    Plot NAV comparison between original and fixed.

    Args:
        results: Output from compare_alphas()
        save_path: Optional path to save chart
    """
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    orig_nav = results.get("original", {}).get("nav")
    fixed_nav = results.get("fixed", {}).get("nav")

    if orig_nav is None and fixed_nav is None:
        print("No NAV data to plot")
        return

    # NAV comparison
    ax1 = axes[0]
    if orig_nav is not None:
        ax1.plot(orig_nav.index, orig_nav.values, label="Original", alpha=0.7, color="red")
    if fixed_nav is not None:
        ax1.plot(fixed_nav.index, fixed_nav.values, label="Fixed", alpha=0.7, color="green")
    ax1.set_title("NAV Comparison")
    ax1.set_ylabel("NAV")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Difference (if both exist)
    ax2 = axes[1]
    if orig_nav is not None and fixed_nav is not None:
        # Align indices
        common_idx = orig_nav.index.intersection(fixed_nav.index)
        diff = fixed_nav.loc[common_idx] - orig_nav.loc[common_idx]
        ax2.fill_between(common_idx, diff.values, alpha=0.5, color="blue")
        ax2.axhline(y=0, color="black", linestyle="--", alpha=0.5)
        ax2.set_title("NAV Difference (Fixed - Original)")
    ax2.set_ylabel("Difference")
    ax2.set_xlabel("Date")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f"Chart saved to {save_path}")

    plt.show()


def test_path_independence(alpha_class, start1: int = 20240101, start2: int = 20240801, end: int = 20241130) -> bool:
    """
    Quick path independence test.

    Args:
        alpha_class: Alpha class to test
        start1: First start date
        start2: Second start date (must be > start1)
        end: End date

    Returns:
        True if path independent
    """
    alpha = alpha_class()

    print(f"Testing path independence: {start1} vs {start2} -> {end}")

    pos1 = alpha.get(start1, end)
    pos2 = alpha.get(start2, end)

    # Find overlap
    overlap_start = max(pos1.index[0], pos2.index[0])
    overlap_end = min(pos1.index[-1], pos2.index[-1])

    p1 = pos1.loc[overlap_start:overlap_end]
    p2 = pos2.loc[overlap_start:overlap_end]

    diff = (p1 - p2).abs().sum().sum()

    if diff < 1e-6:
        print(f"  PASSED: diff = {diff:.2e}")
        return True
    else:
        diff_by_date = (p1 - p2).abs().sum(axis=1)
        diff_dates = diff_by_date[diff_by_date > 1e-6].head(5)
        print(f"  FAILED: diff = {diff:.2e}")
        print(f"  Differing dates: {list(diff_dates.index)}")
        return False


# Convenience function for Jupyter
def quick_compare(original_path: str, fixed_path: str, universe: str):
    """
    Quick comparison from file paths.

    Usage:
        quick_compare('./original/am.py', './alpha.py', 'id_stock')
    """
    import importlib.util
    from pathlib import Path

    def load_class(path):
        spec = importlib.util.spec_from_file_location("mod", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.Alpha

    orig = load_class(Path(original_path))
    fixed = load_class(Path(fixed_path))

    print("=== Path Independence Test ===")
    test_path_independence(fixed)

    print("\n=== Backtest Comparison ===")
    results = compare_alphas(orig, fixed, universe)

    print("\n=== NAV Chart ===")
    plot_comparison(results)

    return results
