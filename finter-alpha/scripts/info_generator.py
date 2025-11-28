#!/usr/bin/env python3
"""
Info Generator for Finter Alpha Strategies

Usage:
    python info_generator.py --title "Momentum Top 10" --summary "..." --category momentum \\
        --evaluation "Sharpe 1.5, MDD 15%, Total Return 45%" --lessons "Learned that..."

    python info_generator.py --title "Value Quality" --summary "Low PBR + high ROE" \\
        --category composite --not-investable \\
        --evaluation "Sharpe 0.8, needs improvement" --lessons "Factor combination was weak"

Categories:
    momentum, value, quality, growth, technical, macro, stat_arb, ml, composite

Tags (examples):
    Selection:  top_k, bottom_k, threshold, long_short
    Weighting:  equal_weight, market_cap_weight, score_weight
    Rebalance:  daily, weekly, monthly, quarterly

Required Fields:
    - title: Strategy name (converted to snake_case)
              ⚠️ MUST be in English! Korean/non-ASCII characters will cause errors.
              Example: "Momentum Top 10", "Value Quality", "RSI Mean Reversion"
    - summary: Brief description of the strategy logic
    - category: One of the valid categories above
    - evaluation: Performance evaluation (e.g., "Sharpe 1.5, MDD 15%, Total Return 45%")
    - lessons: Key learnings and insights from development
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

VALID_CATEGORIES = [
    "momentum",
    "value",
    "quality",
    "growth",
    "technical",
    "macro",
    "stat_arb",
    "ml",
    "composite",
]

VALID_UNIVERSES = [
    "kr_stock",
    "us_stock",
    "vn_stock",
    "id_stock",
    "us_etf",
    "btcusdt_spot_binance",
]


def to_snake_case(text: str) -> str:
    """
    Convert text to snake_case.

    Args:
        text: Strategy title (MUST be in English)

    Returns:
        snake_case version of the title

    Raises:
        ValueError: If title contains non-ASCII characters (Korean, etc.)
    """
    # Check for non-ASCII characters (Korean, Chinese, etc.)
    if not text.isascii():
        raise ValueError(
            f"Title must be in English only. Got non-ASCII characters: '{text}'\n"
            "Examples: 'Momentum Top 10', 'Value Quality', 'RSI Mean Reversion'"
        )

    text = re.sub(r"[-\s]+", "_", text)
    text = re.sub(r"[^a-zA-Z0-9_]", "", text)

    # Check if result is empty (all special characters)
    if not text:
        raise ValueError(
            f"Title resulted in empty string after conversion. "
            "Use alphanumeric characters only."
        )

    return text.lower()


def generate_info(
    title: str,
    summary: str,
    category: str,
    evaluation: str,
    lessons: str,
    tags: list[str] | None = None,
    universe: str = "kr_stock",
    investable: bool = True,
) -> dict:
    """
    Generate info dictionary for alpha strategy.

    Required fields:
        title: Strategy name (will be converted to snake_case)
        summary: Brief description of the strategy logic
        category: One of VALID_CATEGORIES
        evaluation: Performance evaluation results (e.g., "Sharpe 1.5, MDD 15%")
        lessons: Key learnings and insights from development

    Optional fields:
        tags: List of descriptive tags
        universe: Market universe (default: kr_stock)
        investable: Whether strategy is ready for investment (default: True)
    """
    if category not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category: {category}")
    if universe not in VALID_UNIVERSES:
        raise ValueError(f"Invalid universe: {universe}")
    if not evaluation or not evaluation.strip():
        raise ValueError("evaluation is required and cannot be empty")
    if not lessons or not lessons.strip():
        raise ValueError("lessons is required and cannot be empty")

    info = {
        "alpha_title": to_snake_case(title),
        "alpha_summary": summary,
        "alpha_category": category,
        "tags": tags or [],
        "universe": universe,
        "investable": investable,
        "evaluation": evaluation,
        "lessons": lessons,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    return info


def main():
    parser = argparse.ArgumentParser(
        description="Generate info.json for alpha strategy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python info_generator.py --title "Momentum Top 10" --summary "Top 10 by 20d momentum" \\
      --category momentum --evaluation "Sharpe 1.5, MDD 15%" --lessons "Momentum works best in trending markets"

  python info_generator.py --title "Value Quality" --summary "Low PBR + high ROE" \\
      --category composite --not-investable \\
      --evaluation "Sharpe 0.8, needs tuning" --lessons "Factor combination needs more research"
        """,
    )

    # Required arguments
    parser.add_argument("--title", required=True, help="Strategy name")
    parser.add_argument("--summary", required=True, help="Brief description of strategy logic")
    parser.add_argument("--category", required=True, choices=VALID_CATEGORIES, help="Strategy category")
    parser.add_argument("--evaluation", required=True, help="Performance evaluation (e.g., 'Sharpe 1.5, MDD 15%')")
    parser.add_argument("--lessons", required=True, help="Key learnings and insights from development")

    # Optional arguments
    parser.add_argument("--tags", default="", help="Comma-separated tags")
    parser.add_argument("--universe", default="kr_stock", choices=VALID_UNIVERSES, help="Market universe")
    parser.add_argument("--not-investable", action="store_true", dest="not_investable", help="Mark as not ready for investment")
    parser.add_argument("--output", default="info.json", help="Output file path")

    args = parser.parse_args()
    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []

    try:
        info = generate_info(
            title=args.title,
            summary=args.summary,
            category=args.category,
            evaluation=args.evaluation,
            lessons=args.lessons,
            tags=tags,
            universe=args.universe,
            investable=not args.not_investable,
        )
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    Path(args.output).write_text(json.dumps(info, ensure_ascii=False, indent=2))
    print(json.dumps(info, ensure_ascii=False, indent=2))
    print(f"\nSaved: {args.output}")


if __name__ == "__main__":
    main()
