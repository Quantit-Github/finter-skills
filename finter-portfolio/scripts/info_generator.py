#!/usr/bin/env python3
"""
Info Generator for Finter Portfolio Strategies

Usage:
    python info_generator.py --title "Risk Parity Portfolio" --summary "..." --category risk_parity \\
        --universe kr_stock --investable \\
        --evaluation "Works well in low correlation regimes" --lessons "Learned that..."

    python info_generator.py --title "Equal Weight Baseline" --summary "1/N allocation" \\
        --category equal_weight --universe kr_stock --not-investable \\
        --evaluation "Simple baseline, no optimization" --lessons "Good starting point"

Categories:
    equal_weight, risk_parity, mean_variance, min_variance, max_sharpe, hrp, custom

Universes:
    kr_stock, us_stock, vn_stock, id_stock, us_etf, btcusdt_spot_binance

Tags (examples):
    Weighting:  equal_weight, inverse_vol, risk_parity
    Optimization: mean_variance, min_variance, max_sharpe
    Rebalance:  daily, weekly, monthly, quarterly
    Method:     hrp, black_litterman, factor_based

Required Fields:
    - title: Portfolio name (converted to snake_case, max 34 chars before suffix)
              MUST be in English! Korean/non-ASCII characters will cause errors.
              Example: "Risk Parity Portfolio", "Equal Weight", "Max Sharpe Optimized"
    - summary: Brief description of the portfolio logic
    - category: One of the valid categories above
    - universe: Market universe (one of the valid universes above)
    - investable/not-investable: Whether portfolio is ready for real investment
    - evaluation: Portfolio assessment (strengths, weaknesses, when it works/fails)
    - lessons: Key learnings and insights from development
"""

import argparse
import json
import random
import re
import string
import sys
from datetime import datetime, timezone
from pathlib import Path

VALID_CATEGORIES = [
    # Basic allocation
    "equal_weight",  # 1/N equal allocation
    # Risk-based
    "risk_parity",   # Risk parity / inverse volatility
    "min_variance",  # Minimum variance portfolio
    # Return-based optimization
    "mean_variance", # Mean-variance optimization (Markowitz)
    "max_sharpe",    # Maximum Sharpe ratio portfolio
    # Hierarchical
    "hrp",           # Hierarchical Risk Parity
    # Other
    "custom",        # Custom weighting logic
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
        text: Portfolio title (MUST be in English)

    Returns:
        snake_case version of the title

    Raises:
        ValueError: If title contains non-ASCII characters (Korean, etc.)
    """
    # Check for non-ASCII characters (Korean, Chinese, etc.)
    if not text.isascii():
        raise ValueError(
            f"Title must be in English only. Got non-ASCII characters: '{text}'\n"
            "Examples: 'Risk Parity Portfolio', 'Equal Weight', 'Max Sharpe Optimized'"
        )

    text = re.sub(r"[-\s]+", "_", text)
    text = re.sub(r"[^a-zA-Z0-9_]", "", text)

    # Check if result is empty (all special characters)
    if not text:
        raise ValueError(
            "Title resulted in empty string after conversion. "
            "Use alphanumeric characters only."
        )

    return text.lower()


MAX_TITLE_LENGTH = 45  # DB varchar(45) limit
SUFFIX_LENGTH = 11  # _YYMMDDHH + 2 random chars
MAX_BASE_NAME_LENGTH = MAX_TITLE_LENGTH - SUFFIX_LENGTH  # 34 chars


def generate_model_title(base_title: str) -> str:
    """
    Generate portfolio title with datetime and random suffix.

    Args:
        base_title: Base portfolio title (will be converted to snake_case)

    Returns:
        Title with suffix: {snake_case_title}_{YYMMDDHH}{random_2_chars}
        Example: "Risk Parity Portfolio" -> "risk_parity_portfolio_25113014ab"

    Note:
        Total length is limited to 45 chars (DB constraint).
        Base name is truncated to 34 chars if needed.
    """
    base_name = to_snake_case(base_title)
    if len(base_name) > MAX_BASE_NAME_LENGTH:
        base_name = base_name[:MAX_BASE_NAME_LENGTH]
    datetime_suffix = datetime.now().strftime("%y%m%d%H")
    random_suffix = "".join(random.choices(string.ascii_lowercase, k=2))
    return f"{base_name}_{datetime_suffix}{random_suffix}"


def generate_info(
    title: str,
    summary: str,
    category: str,
    universe: str,
    investable: bool,
    evaluation: str,
    lessons: str,
    tags: list[str] | None = None,
) -> dict:
    """
    Generate info dictionary for portfolio strategy.

    Required fields:
        title: Portfolio name (will be converted to snake_case)
        summary: Brief description of the portfolio logic
        category: One of VALID_CATEGORIES
        universe: Market universe (one of VALID_UNIVERSES)
        investable: Whether portfolio is ready for real investment
        evaluation: Portfolio assessment (strengths, weaknesses, when it works/fails)
        lessons: Key learnings and insights from development

    Optional fields:
        tags: List of descriptive tags
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
        "model_type": "portfolio",
        "model_title": generate_model_title(title),
        "model_summary": summary,
        "model_category": category,
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
        description="Generate info.json for portfolio strategy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python info_generator.py --title "Risk Parity Portfolio" --summary "Inverse volatility weighting" \\
      --category risk_parity --universe kr_stock --investable \\
      --evaluation "Strong diversification, but sensitive to correlation regime" \\
      --lessons "Works best when correlations are stable"

  python info_generator.py --title "Equal Weight Baseline" --summary "1/N equal allocation" \\
      --category equal_weight --universe kr_stock --not-investable \\
      --evaluation "Simple baseline, no optimization, easy to implement" \\
      --lessons "Good starting point for comparison"
        """,
    )

    # Required arguments
    parser.add_argument("--title", required=True, help="Portfolio name")
    parser.add_argument(
        "--summary", required=True, help="Brief description of portfolio logic"
    )
    parser.add_argument(
        "--category", required=True, choices=VALID_CATEGORIES, help="Portfolio category"
    )
    parser.add_argument(
        "--evaluation",
        required=True,
        help="Portfolio assessment: strengths, weaknesses, conditions where it works/fails",
    )
    parser.add_argument(
        "--lessons", required=True, help="Key learnings and insights from development"
    )

    parser.add_argument(
        "--universe",
        required=True,
        choices=VALID_UNIVERSES,
        help="Market universe (required)",
    )

    # Investable: mutually exclusive required group
    investable_group = parser.add_mutually_exclusive_group(required=True)
    investable_group.add_argument(
        "--investable",
        action="store_true",
        dest="investable",
        help="Mark as ready for real investment",
    )
    investable_group.add_argument(
        "--not-investable",
        action="store_true",
        dest="not_investable",
        help="Mark as NOT ready for investment (experimental/research)",
    )

    # Optional arguments
    parser.add_argument("--tags", default="", help="Comma-separated tags")
    parser.add_argument("--output", default="info.json", help="Output file path")

    args = parser.parse_args()
    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []

    try:
        info = generate_info(
            title=args.title,
            summary=args.summary,
            category=args.category,
            universe=args.universe,
            investable=args.investable,  # True if --investable, False if --not-investable
            evaluation=args.evaluation,
            lessons=args.lessons,
            tags=tags,
        )
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    Path(args.output).write_text(json.dumps(info, ensure_ascii=False, indent=2))
    print(json.dumps(info, ensure_ascii=False, indent=2))
    print(f"\nSaved: {args.output}")


if __name__ == "__main__":
    main()
