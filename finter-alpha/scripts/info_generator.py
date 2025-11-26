#!/usr/bin/env python3
"""
Info Generator for Finter Alpha Strategies

Usage:
    python info_generator.py --title "Momentum Top 10" --summary "..." --category momentum
    python info_generator.py --title "..." --category composite --not-investable --lessons "..."

Categories:
    momentum, value, quality, growth, technical, macro, stat_arb, ml, composite

Tags (examples):
    Selection:  top_k, bottom_k, threshold, long_short
    Weighting:  equal_weight, market_cap_weight, score_weight
    Rebalance:  daily, weekly, monthly, quarterly
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
    """Convert text to snake_case."""
    text = re.sub(r"[-\s]+", "_", text)
    text = re.sub(r"[^a-zA-Z0-9_]", "", text)
    return text.lower()


def generate_info(
    title: str,
    summary: str,
    category: str,
    tags: list[str] | None = None,
    universe: str = "kr_stock",
    investable: bool = True,
    evaluation: str | None = None,
    lessons: str | None = None,
) -> dict:
    """Generate info dictionary for alpha strategy."""
    if category not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category: {category}")
    if universe not in VALID_UNIVERSES:
        raise ValueError(f"Invalid universe: {universe}")

    info = {
        "alpha_title": to_snake_case(title),
        "alpha_summary": summary,
        "alpha_category": category,
        "tags": tags or [],
        "universe": universe,
        "investable": investable,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if evaluation:
        info["evaluation"] = evaluation
    if lessons:
        info["lessons"] = lessons

    return info


def main():
    parser = argparse.ArgumentParser(
        description="Generate info.json for alpha strategy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python info_generator.py --title "Momentum Top 10" --summary "Top 10 by 20d momentum" --category momentum
  python info_generator.py --title "Value Quality" --summary "Low PBR + high ROE" --category composite --not-investable
        """,
    )

    parser.add_argument("--title", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--category", required=True, choices=VALID_CATEGORIES)
    parser.add_argument("--tags", default="", help="Comma-separated tags")
    parser.add_argument("--universe", default="kr_stock", choices=VALID_UNIVERSES)
    parser.add_argument("--not-investable", action="store_true", dest="not_investable")
    parser.add_argument("--evaluation", default=None)
    parser.add_argument("--lessons", default=None)
    parser.add_argument("--output", default="info.json")

    args = parser.parse_args()
    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []

    try:
        info = generate_info(
            title=args.title,
            summary=args.summary,
            category=args.category,
            tags=tags,
            universe=args.universe,
            investable=not args.not_investable,
            evaluation=args.evaluation,
            lessons=args.lessons,
        )
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    Path(args.output).write_text(json.dumps(info, ensure_ascii=False, indent=2))
    print(json.dumps(info, ensure_ascii=False, indent=2))
    print(f"\nSaved: {args.output}")


if __name__ == "__main__":
    main()
