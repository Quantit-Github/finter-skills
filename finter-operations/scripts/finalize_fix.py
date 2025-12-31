#!/usr/bin/env python3
"""
Finalize Alpha Fix - Standalone Script for Jupyter Execution

Validates fixed code, runs A/B comparison, and decides on resubmission.

Usage:
    python finalize_fix.py --original ./original/am.py --fixed ./alpha.py --universe id_stock

Output:
    - fix_report.json: Decision (RESUBMIT/REJECT/HUMAN_REVIEW) and metrics comparison
"""

import argparse
import importlib.util
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


class FixDecision(str, Enum):
    """Decision on what to do with the fixed alpha."""

    RESUBMIT = "resubmit"  # Bug fixed, performance same or better
    REJECT = "reject"  # Fix made it worse
    HUMAN_REVIEW = "human_review"  # Can't determine


# ============================================================
# VALIDATION FUNCTIONS (from finter-alpha finalize.py)
# ============================================================


def load_alpha_class(filepath: Path):
    """Load Alpha class from Python file."""
    if not filepath.exists():
        raise FileNotFoundError(f"Alpha file not found: {filepath}")

    spec = importlib.util.spec_from_file_location("alpha_module", filepath)
    module = importlib.util.module_from_spec(spec)
    sys.modules["alpha_module"] = module
    spec.loader.exec_module(module)

    if not hasattr(module, "Alpha"):
        raise ValueError(f"File must contain a class named 'Alpha': {filepath}")

    return module.Alpha


def check_class_name(filepath: Path) -> tuple[bool, str]:
    """Check if Alpha class is named correctly."""
    import ast

    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                base_name = None
                if isinstance(base, ast.Name):
                    base_name = base.id
                elif isinstance(base, ast.Attribute):
                    base_name = base.attr

                if base_name == "BaseAlpha" and node.name != "Alpha":
                    return False, f"Class must be named 'Alpha', not '{node.name}'"

    return True, "OK"


def validate_positions(positions: pd.DataFrame) -> dict:
    """Validate position DataFrame."""
    issues = {"errors": [], "warnings": []}

    if positions.empty:
        issues["errors"].append("Position DataFrame is empty")
        return issues

    # Check row sums
    row_sums = positions.sum(axis=1)
    if row_sums.max() > 1e8 + 1000:
        issues["errors"].append(f"Row sums exceed 1e8. Max: {row_sums.max():.0f}")

    # Check for all-NaN rows
    all_nan_rows = positions.isna().all(axis=1)
    if all_nan_rows.any():
        dates = positions.index[all_nan_rows].tolist()[:3]
        issues["errors"].append(
            f"Found {all_nan_rows.sum()} all-NaN rows. Use fillna(0). First: {dates}"
        )

    # Warnings
    nan_count = positions.isnull().sum().sum()
    if nan_count > 0:
        issues["warnings"].append(
            f"{nan_count} NaN values ({nan_count/positions.size*100:.1f}%)"
        )

    zero_days = (row_sums == 0).sum()
    if zero_days > 0:
        issues["warnings"].append(f"{zero_days} days with zero positions")

    return issues


def check_path_independence(AlphaClass, verbose=False) -> tuple[bool, str]:
    """Check if alpha is path-independent."""
    try:
        alpha = AlphaClass()

        # Two overlapping periods
        pos1 = alpha.get(20200101, 20211231)
        pos2 = alpha.get(20210101, 20221231)

        # Find overlap
        overlap_start = max(pos1.index.min(), pos2.index.min())
        overlap_end = min(pos1.index.max(), pos2.index.max())

        p1 = pos1.loc[overlap_start:overlap_end]
        p2 = pos2.loc[overlap_start:overlap_end]

        # Align
        common_idx = p1.index.intersection(p2.index)
        common_cols = p1.columns.intersection(p2.columns)

        if len(common_idx) == 0:
            return True, "No overlap to check"

        p1 = p1.loc[common_idx, common_cols]
        p2 = p2.loc[common_idx, common_cols]

        # Compare
        diff = (p1.fillna(0) - p2.fillna(0)).abs()
        max_diff = diff.max().max()

        if max_diff > 1e-6:
            return False, f"max_diff={max_diff:.2e}"
        return True, "OK"

    except Exception as e:
        return False, f"Error: {e}"


# ============================================================
# BACKTEST
# ============================================================


def run_backtest(
    alpha_path: Path,
    universe: str,
    start: int = 20200101,
    end: int | None = None,
) -> tuple[float | None, str, Any]:
    """
    Run backtest on alpha code and return Sharpe ratio.

    Returns:
        tuple: (sharpe_ratio or None, message, backtest_result or None)
    """
    if end is None:
        end = int(datetime.now(timezone.utc).strftime("%Y%m%d"))

    try:
        # Load alpha
        AlphaClass = load_alpha_class(alpha_path)
        alpha = AlphaClass()
        positions = alpha.get(start, end)

        # Validate
        validation = validate_positions(positions)
        if validation["errors"]:
            return None, f"Validation error: {validation['errors'][0]}", None

        # Run backtest
        from finter.backtest import Simulator

        sim = Simulator(market_type=universe)
        result = sim.run(position=positions)

        sharpe = result.statistics.get("Sharpe Ratio", 0)
        return sharpe, f"Sharpe={sharpe:.3f}", result

    except Exception as e:
        return None, f"Backtest failed: {e}", None


def create_comparison_chart(
    fixed_result: Any,
    original_result: Any | None,
    output_path: Path,
    fixed_sharpe: float,
    original_sharpe: float | None,
):
    """Create A/B comparison chart."""
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        COLORS = {
            "background": "#1a1a2e",
            "fixed": "#00d26a",  # Green for fixed
            "original": "#ff4757",  # Red for original
            "text": "#eaeaea",
            "text_muted": "#8b8b8b",
            "grid": "#2a2a4a",
        }

        fig, ax = plt.subplots(figsize=(8, 5), facecolor=COLORS["background"])
        ax.set_facecolor(COLORS["background"])

        # Fixed alpha (always present)
        fixed_nav = fixed_result.summary["nav"]
        fixed_returns = (fixed_nav.values / fixed_nav.values[0] - 1) * 100
        ax.plot(
            fixed_nav.index,
            fixed_returns,
            color=COLORS["fixed"],
            linewidth=2,
            label=f"Fixed (Sharpe: {fixed_sharpe:.2f})",
        )

        # Original alpha (if available)
        if original_result is not None and original_sharpe is not None:
            orig_nav = original_result.summary["nav"]
            orig_returns = (orig_nav.values / orig_nav.values[0] - 1) * 100
            ax.plot(
                orig_nav.index,
                orig_returns,
                color=COLORS["original"],
                linewidth=2,
                linestyle="--",
                label=f"Original (Sharpe: {original_sharpe:.2f})",
            )

        # Style
        ax.axhline(y=0, color=COLORS["text_muted"], linewidth=0.5, linestyle="--", alpha=0.5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(COLORS["grid"])
        ax.spines["bottom"].set_color(COLORS["grid"])
        ax.tick_params(colors=COLORS["text_muted"], labelsize=8)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x:+.0f}%"))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.grid(True, alpha=0.2, color=COLORS["grid"])
        ax.set_title("A/B Comparison: Original vs Fixed", color=COLORS["text"], fontsize=11, fontweight="bold")
        ax.legend(loc="upper left", facecolor=COLORS["background"], edgecolor=COLORS["grid"], labelcolor=COLORS["text"])

        plt.tight_layout()
        fig.savefig(output_path, dpi=100, facecolor=COLORS["background"], bbox_inches="tight")
        plt.close(fig)
        return True

    except Exception as e:
        print(f"  ⚠ Chart generation failed: {e}")
        return False


# ============================================================
# DECISION LOGIC
# ============================================================


def determine_fix_decision(
    original_sharpe: float | None,
    fixed_sharpe: float | None,
    validation_passed: bool,
) -> tuple[FixDecision, str]:
    """
    Determine what to do with the fix based on A/B test.

    Logic:
    - If validation failed → HUMAN_REVIEW
    - If performance same or better (within -10%) → RESUBMIT
    - If performance worse (>10% drop) → REJECT
    """
    if not validation_passed:
        return FixDecision.HUMAN_REVIEW, "Validation failed"

    if fixed_sharpe is None:
        return FixDecision.HUMAN_REVIEW, "Fixed Sharpe unavailable"

    # Original was broken, fixed works
    if original_sharpe is None:
        if fixed_sharpe > 0.3:
            return (
                FixDecision.RESUBMIT,
                "Original broken, fixed works with reasonable Sharpe",
            )
        return FixDecision.HUMAN_REVIEW, "Cannot compare - original backtest failed"

    # Avoid division by near-zero
    if abs(original_sharpe) < 0.01:
        if fixed_sharpe >= 0:
            return FixDecision.RESUBMIT, "Original near-zero, fixed is non-negative"
        return FixDecision.HUMAN_REVIEW, "Original near-zero, fixed is negative"

    # Calculate relative change
    relative_change = (fixed_sharpe - original_sharpe) / abs(original_sharpe)

    if relative_change >= -0.10:
        if relative_change > 0.10:
            return (
                FixDecision.RESUBMIT,
                f"Performance improved ({relative_change:+.1%}), bug was hurting performance",
            )
        return (
            FixDecision.RESUBMIT,
            f"Performance similar ({relative_change:+.1%}), bug fixed",
        )
    else:
        return (
            FixDecision.REJECT,
            f"Performance degraded ({relative_change:+.1%}), fix may have broken strategy",
        )


# ============================================================
# REPORT
# ============================================================


@dataclass
class FixReport:
    """Report documenting the fix."""

    # Validation
    validation_passed: bool
    validation_message: str

    # Metrics comparison
    original_sharpe: float | None
    fixed_sharpe: float | None

    # Decision
    decision: str
    decision_reason: str

    # Metadata
    fixed_at: str


# ============================================================
# MAIN
# ============================================================


def print_header(title: str):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print("─" * 60)


def main():
    parser = argparse.ArgumentParser(description="Finalize alpha fix with A/B test")
    parser.add_argument("--original", required=True, help="Path to original alpha code")
    parser.add_argument("--fixed", required=True, help="Path to fixed alpha code")
    parser.add_argument("--universe", required=True, help="Universe (e.g., id_stock)")
    parser.add_argument("--start", type=int, default=20200101, help="Backtest start")
    parser.add_argument("--end", type=int, default=None, help="Backtest end")

    args = parser.parse_args()

    original_path = Path(args.original)
    fixed_path = Path(args.fixed)
    output_dir = fixed_path.parent

    print("=" * 60)
    print("  FINALIZE FIX - A/B COMPARISON")
    print("=" * 60)
    print(f"  Original: {original_path}")
    print(f"  Fixed: {fixed_path}")
    print(f"  Universe: {args.universe}")

    # ─────────────────────────────────────────────────────────
    # STEP 1: Validate Fixed Code
    # ─────────────────────────────────────────────────────────
    print_header("1. Validate Fixed Code")

    validation_passed = True
    validation_messages = []

    # Class name check
    passed, msg = check_class_name(fixed_path)
    print(f"  Class name: {'✓' if passed else '✗'} {msg}")
    if not passed:
        validation_passed = False
        validation_messages.append(msg)

    # Load and check positions
    if validation_passed:
        try:
            AlphaClass = load_alpha_class(fixed_path)
            alpha = AlphaClass()
            end_date = args.end or int(datetime.now(timezone.utc).strftime("%Y%m%d"))
            positions = alpha.get(args.start, end_date)
            print(f"  Positions: ✓ {positions.shape[0]} days, {positions.shape[1]} stocks")

            # Validate positions
            validation = validate_positions(positions)
            if validation["errors"]:
                for err in validation["errors"]:
                    print(f"  ✗ {err}")
                    validation_messages.append(err)
                validation_passed = False

            # Path independence
            if validation_passed:
                passed, msg = check_path_independence(AlphaClass)
                print(f"  Path independence: {'✓' if passed else '✗'} {msg}")
                if not passed:
                    validation_passed = False
                    validation_messages.append(f"Path independence: {msg}")

        except Exception as e:
            print(f"  ✗ Load failed: {e}")
            validation_passed = False
            validation_messages.append(str(e))

    validation_msg = "; ".join(validation_messages) if validation_messages else "OK"

    # ─────────────────────────────────────────────────────────
    # STEP 2: Run Backtests (A/B)
    # ─────────────────────────────────────────────────────────
    print_header("2. A/B Backtest Comparison")

    # Fixed backtest
    print("  Running fixed backtest...")
    fixed_sharpe, fixed_msg, fixed_result = run_backtest(
        fixed_path, args.universe, args.start, args.end
    )
    print(f"  Fixed: {fixed_msg}")

    # Original backtest (may fail if code is buggy)
    print("  Running original backtest...")
    original_sharpe, original_msg, original_result = run_backtest(
        original_path, args.universe, args.start, args.end
    )
    print(f"  Original: {original_msg}")

    # ─────────────────────────────────────────────────────────
    # STEP 3: Decision
    # ─────────────────────────────────────────────────────────
    print_header("3. Decision")

    decision, reason = determine_fix_decision(
        original_sharpe=original_sharpe,
        fixed_sharpe=fixed_sharpe,
        validation_passed=validation_passed,
    )

    decision_emoji = {
        FixDecision.RESUBMIT: "✅",
        FixDecision.REJECT: "❌",
        FixDecision.HUMAN_REVIEW: "🔍",
    }

    print(f"  {decision_emoji[decision]} {decision.value.upper()}")
    print(f"  Reason: {reason}")

    # ─────────────────────────────────────────────────────────
    # Save Report
    # ─────────────────────────────────────────────────────────
    report = FixReport(
        validation_passed=validation_passed,
        validation_message=validation_msg[:500],
        original_sharpe=original_sharpe,
        fixed_sharpe=fixed_sharpe,
        decision=decision.value,
        decision_reason=reason,
        fixed_at=datetime.now(timezone.utc).isoformat() + "Z",
    )

    report_path = output_dir / "fix_report.json"
    with open(report_path, "w") as f:
        json.dump(asdict(report), f, indent=2)

    print(f"\n  Report saved: {report_path}")

    # ─────────────────────────────────────────────────────────
    # Generate Chart
    # ─────────────────────────────────────────────────────────
    if fixed_result is not None and fixed_sharpe is not None:
        chart_path = output_dir / "fix_comparison.png"
        if create_comparison_chart(
            fixed_result=fixed_result,
            original_result=original_result,
            output_path=chart_path,
            fixed_sharpe=fixed_sharpe,
            original_sharpe=original_sharpe,
        ):
            print(f"  Chart saved: {chart_path}")

    # ─────────────────────────────────────────────────────────
    # Summary
    # ─────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)

    if original_sharpe is not None and fixed_sharpe is not None:
        diff = fixed_sharpe - original_sharpe
        print(f"  Sharpe: {original_sharpe:.3f} → {fixed_sharpe:.3f} ({diff:+.3f})")
    elif fixed_sharpe is not None:
        print(f"  Fixed Sharpe: {fixed_sharpe:.3f}")
        print(f"  Original: Failed to run")

    print(f"\n  {decision_emoji[decision]} DECISION: {decision.value.upper()}")
    print(f"  {reason}")
    print()

    # Exit code based on decision
    if decision == FixDecision.RESUBMIT:
        return 0
    elif decision == FixDecision.REJECT:
        return 1
    else:
        return 2


if __name__ == "__main__":
    sys.exit(main())
