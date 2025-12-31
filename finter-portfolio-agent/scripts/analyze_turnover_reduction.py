#!/usr/bin/env python3
"""Turnover Reduction Analysis - Analyze cost deduction effect BEFORE individual evaluation.

This script should be run FIRST in the PM workflow to understand:
1. Individual alpha turnovers (sum)
2. Combined portfolio turnover (with position offsetting)
3. Turnover reduction benefit (cost deduction effect)

WHY THIS MATTERS:
- Individual high-turnover alphas should NOT be automatically excluded
- When combined, offsetting positions reduce net turnover
- A 1000% turnover alpha might add value if it hedges other positions

Usage:
    python analyze_turnover_reduction.py --alpha-list a1,a2,a3 --market vn_stock
    python analyze_turnover_reduction.py --portfolio portfolio.py --market us_stock
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def calculate_previous_start_date(start_date: int, lookback_days: int) -> int:
    """Calculate start date for preloading data."""
    start = datetime.strptime(str(start_date), "%Y%m%d")
    previous_start = start - timedelta(days=lookback_days)
    return int(previous_start.strftime("%Y%m%d"))


def calculate_turnover_from_position(position) -> float:
    """Calculate annual turnover from position DataFrame.

    Turnover = sum of |weight changes| / 2, annualized.
    Position is normalized to weights (each row sums to 1).

    Returns:
        Annual turnover as percentage (e.g., 200 means 200% or 2x)
    """
    import numpy as np

    if position is None or position.empty:
        return 0.0

    # Normalize to weights (each row sums to 1)
    daily_total = position.abs().sum(axis=1)
    daily_total = daily_total.replace(0, np.nan)  # Avoid division by zero
    weights = position.div(daily_total, axis=0).fillna(0)

    # Calculate daily weight changes
    daily_changes = weights.diff().abs().sum(axis=1)

    # Annualize: mean daily turnover * 252 trading days
    # Divide by 2 because buy + sell are counted separately
    annual_turnover = daily_changes.mean() * 252 / 2 * 100

    return annual_turnover if not np.isnan(annual_turnover) else 0.0


def get_individual_turnovers(
    alpha_list: list[str],
    market: str,
    start: int,
    end: int,
) -> dict[str, float]:
    """Calculate turnover for each alpha individually.

    Returns:
        Dict of alpha_name -> annual turnover (%)
    """
    from finter import BasePortfolio

    turnovers = {}

    for alpha_name in alpha_list:
        try:
            # Create single-alpha portfolio using BasePortfolio
            class SingleAlphaPortfolio(BasePortfolio):
                pass

            SingleAlphaPortfolio.alpha_list = [alpha_name]

            portfolio = SingleAlphaPortfolio()
            position = portfolio.get(start, end)

            # Calculate turnover from position changes
            turnover = calculate_turnover_from_position(position)
            turnovers[alpha_name] = turnover

        except Exception as e:
            print(f"  Warning: Could not get turnover for {alpha_name}: {e}")
            turnovers[alpha_name] = 0.0

    return turnovers


def get_combined_turnover(
    alpha_list: list[str],
    market: str,
    start: int,
    end: int,
) -> tuple[float, dict]:
    """Calculate turnover for combined EW portfolio.

    Returns:
        Tuple of (annual_turnover, statistics dict)
    """
    from finter import BasePortfolio
    from finter.backtest import Simulator

    class CombinedPortfolio(BasePortfolio):
        pass

    CombinedPortfolio.alpha_list = alpha_list

    portfolio = CombinedPortfolio()
    position = portfolio.get(start, end)

    # Calculate turnover from position
    turnover = calculate_turnover_from_position(position)

    # Get other stats from Simulator
    simulator = Simulator(market_type=market)
    result = simulator.run(position=position)
    stats = result.statistics

    return turnover, stats


def analyze_position_offsetting(
    alpha_list: list[str],
    market: str,
    start: int,
    end: int,
) -> dict:
    """Analyze how positions offset each other.

    Returns:
        Dict with offsetting analysis:
        - gross_position_sum: Sum of absolute positions across all alphas
        - net_position: Combined portfolio position
        - offset_ratio: How much is offset (1 = no offset, 0 = fully hedged)
    """
    from finter import BasePortfolio

    positions = []

    for alpha_name in alpha_list:
        try:
            class SingleAlphaPortfolio(BasePortfolio):
                pass
            SingleAlphaPortfolio.alpha_list = [alpha_name]

            portfolio = SingleAlphaPortfolio()
            pos = portfolio.get(start, end)
            if pos is not None and not pos.empty:
                positions.append(pos)
        except Exception:
            continue

    if not positions:
        return {"gross_position_sum": 0, "net_position": 0, "offset_ratio": 1.0}

    # Align all positions to common dates
    common_dates = positions[0].index
    for pos in positions[1:]:
        common_dates = common_dates.intersection(pos.index)

    if len(common_dates) == 0:
        return {"gross_position_sum": 0, "net_position": 0, "offset_ratio": 1.0}

    aligned = [pos.loc[common_dates] for pos in positions]

    # Gross position sum (sum of absolute values)
    gross = sum(p.abs().sum(axis=1).mean() for p in aligned)

    # Net position (combined)
    combined = sum(aligned) / len(aligned)  # EW average
    net = combined.abs().sum(axis=1).mean()

    # Offset ratio (1 = no benefit, 0 = fully hedged)
    offset_ratio = net / gross if gross > 0 else 1.0

    return {
        "gross_position_sum": gross,
        "net_position": net,
        "offset_ratio": offset_ratio,
        "offset_benefit_pct": (1 - offset_ratio) * 100,
    }


def plot_turnover_comparison(
    individual_turnovers: dict[str, float],
    combined_turnover: float,
    output_path: str = "turnover_analysis.png",
) -> None:
    """Plot individual vs combined turnover comparison."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Left: Individual turnovers bar chart
    names = [n.split(".")[-1][:15] for n in individual_turnovers.keys()]  # Short names
    values = list(individual_turnovers.values())

    bars = axes[0].bar(range(len(names)), values, color='steelblue', alpha=0.7)
    axes[0].set_xticks(range(len(names)))
    axes[0].set_xticklabels(names, rotation=45, ha='right', fontsize=8)
    axes[0].set_ylabel('Annual Turnover (%)')
    axes[0].set_title('Individual Alpha Turnovers')
    axes[0].axhline(y=np.mean(values), color='red', linestyle='--',
                    label=f'Avg: {np.mean(values):.0f}%')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Right: Sum vs Combined comparison
    sum_individual = sum(values) / len(values)  # Average (EW)
    reduction = sum_individual - combined_turnover
    reduction_pct = (reduction / sum_individual * 100) if sum_individual > 0 else 0

    bars = axes[1].bar(['Avg Individual\n(No Offset)', 'Combined\n(With Offset)'],
                       [sum_individual, combined_turnover],
                       color=['coral', 'seagreen'], alpha=0.7)
    axes[1].set_ylabel('Annual Turnover (%)')
    axes[1].set_title(f'Turnover Reduction: {reduction_pct:.1f}%')

    # Add reduction arrow
    axes[1].annotate('', xy=(1, combined_turnover), xytext=(0, sum_individual),
                     arrowprops=dict(arrowstyle='->', color='green', lw=2))
    axes[1].text(0.5, (sum_individual + combined_turnover) / 2,
                 f'-{reduction_pct:.1f}%', ha='center', fontsize=12, fontweight='bold')

    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\nChart saved to: {output_path}")

    try:
        plt.show()
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="Analyze turnover reduction from combining alphas (cost deduction effect)"
    )
    parser.add_argument("--portfolio", help="Path to portfolio.py file")
    parser.add_argument("--alpha-list", help="Comma-separated alpha list entries (without 'alpha.' prefix)")
    parser.add_argument("--market", required=True,
                        choices=["kr_stock", "us_stock", "vn_stock", "id_stock", "us_etf"],
                        help="Market type")
    parser.add_argument("--start", type=int, default=20200101, help="Start date (YYYYMMDD)")
    parser.add_argument("--end", type=int, default=None, help="End date (YYYYMMDD, default: today)")
    parser.add_argument("--output", default="turnover_analysis.png", help="Output chart path")
    args = parser.parse_args()

    if args.end is None:
        args.end = int(datetime.now().strftime("%Y%m%d"))

    print("=" * 70)
    print("TURNOVER REDUCTION ANALYSIS (Cost Deduction Effect)")
    print("=" * 70)
    print(f"Market: {args.market}")
    print(f"Period: {args.start} - {args.end}")

    # Load alpha list
    if args.portfolio:
        import importlib.util
        spec = importlib.util.spec_from_file_location("portfolio_module", args.portfolio)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        alpha_list = module.Portfolio.alpha_list
    elif args.alpha_list:
        alpha_list = [a.strip() for a in args.alpha_list.split(",")]
    else:
        print("ERROR: Must specify --portfolio or --alpha-list")
        sys.exit(1)

    print(f"Alpha count: {len(alpha_list)}")
    print("\nAlphas:")
    for i, a in enumerate(alpha_list, 1):
        print(f"  {i}. {a}")

    # 1. Get individual turnovers
    print("\n" + "-" * 70)
    print("STEP 1: Individual Alpha Turnovers")
    print("-" * 70)
    individual_turnovers = get_individual_turnovers(alpha_list, args.market, args.start, args.end)

    for alpha, turnover in sorted(individual_turnovers.items(), key=lambda x: -x[1]):
        flag = "⚠️ HIGH" if turnover > 3000 else ""
        print(f"  {alpha.split('.')[-1][:30]}: {turnover:.0f}% {flag}")

    avg_turnover = np.mean(list(individual_turnovers.values()))
    sum_turnover = sum(individual_turnovers.values())
    print(f"\n  Average: {avg_turnover:.0f}%")
    print(f"  Sum (if no offset): {sum_turnover:.0f}%")

    # 2. Get combined turnover
    print("\n" + "-" * 70)
    print("STEP 2: Combined Portfolio Turnover")
    print("-" * 70)
    combined_turnover, stats = get_combined_turnover(alpha_list, args.market, args.start, args.end)
    print(f"  Combined Turnover: {combined_turnover:.0f}%")
    print(f"  Combined Sharpe: {stats.get('Sharpe Ratio', 'N/A')}")
    print(f"  Combined MDD: {stats.get('Max Drawdown (%)', 'N/A')}%")

    # 3. Analyze position offsetting
    print("\n" + "-" * 70)
    print("STEP 3: Position Offsetting Analysis")
    print("-" * 70)
    offset_analysis = analyze_position_offsetting(alpha_list, args.market, args.start, args.end)
    print(f"  Gross Position Sum: {offset_analysis['gross_position_sum']:.4f}")
    print(f"  Net Combined Position: {offset_analysis['net_position']:.4f}")
    print(f"  Offset Ratio: {offset_analysis['offset_ratio']:.2%}")
    print(f"  Offset Benefit: {offset_analysis['offset_benefit_pct']:.1f}%")

    # 4. Calculate reduction benefit
    print("\n" + "=" * 70)
    print("SUMMARY: COST DEDUCTION EFFECT")
    print("=" * 70)

    reduction = avg_turnover - combined_turnover
    reduction_pct = (reduction / avg_turnover * 100) if avg_turnover > 0 else 0

    print(f"""
  ┌─────────────────────────────────────────────────────────┐
  │  Individual Avg Turnover:  {avg_turnover:>6.0f}%                     │
  │  Combined Portfolio:       {combined_turnover:>6.0f}%                     │
  │  ─────────────────────────────────────────────────────  │
  │  TURNOVER REDUCTION:       {reduction:>6.0f}% ({reduction_pct:.1f}% savings)    │
  └─────────────────────────────────────────────────────────┘
""")

    # 5. Interpretation
    print("INTERPRETATION:")
    print("-" * 70)

    if reduction_pct > 30:
        print("""
  ✅ STRONG cost deduction effect!
     Combining these alphas significantly reduces transaction costs.
     High-turnover alphas may still add value due to position offsetting.
""")
    elif reduction_pct > 10:
        print("""
  🟡 MODERATE cost deduction effect.
     Some turnover reduction from position offsetting.
     Consider keeping high-turnover alphas if they add diversification.
""")
    else:
        print("""
  ⚠️ WEAK cost deduction effect.
     Positions are correlated (similar direction).
     High-turnover alphas will directly impact costs.
""")

    # High turnover alphas that might still add value
    high_turnover_alphas = [a for a, t in individual_turnovers.items() if t > 1000]
    if high_turnover_alphas:
        print(f"""
  NOTE: {len(high_turnover_alphas)} alpha(s) have >1000% turnover:
""")
        for a in high_turnover_alphas:
            t = individual_turnovers[a]
            print(f"    - {a.split('.')[-1][:30]}: {t:.0f}%")

        if reduction_pct > 20:
            print("""
  → These high-turnover alphas may STILL ADD VALUE because:
    - Position offsetting reduces their net impact
    - They may provide diversification benefit
    - Don't exclude based on individual turnover alone!
""")
        else:
            print("""
  → With weak offset benefit, these may increase costs significantly.
    Consider excluding or reducing weight.
""")

    # 6. Plot comparison
    print("\nGenerating comparison chart...")
    plot_turnover_comparison(individual_turnovers, combined_turnover, args.output)

    print("\n" + "=" * 70)
    print("NEXT STEPS FOR PM EVALUATION:")
    print("=" * 70)
    print("""
  Use this analysis when evaluating individual alphas:

  1. HIGH OFFSET BENEFIT (>30%):
     - Don't exclude high-turnover alphas prematurely
     - Focus on diversification value and correlation
     - Turnover is NOT a valid red flag for individual exclusion

  2. LOW OFFSET BENEFIT (<10%):
     - Individual turnover matters more
     - High-turnover alphas will directly impact costs
     - Consider excluding if turnover > 30x with no diversification benefit

  3. ALWAYS CONSIDER:
     - Does this alpha offset existing positions?
     - What is the marginal turnover impact of adding/removing it?
     - Economic sense > raw turnover numbers
""")


if __name__ == "__main__":
    main()
