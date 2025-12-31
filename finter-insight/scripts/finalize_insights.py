#!/usr/bin/env python3
"""
Finalize Insights - Validate and output insights.json

This script MUST be run after generating hypotheses.
It validates the JSON structure and saves to the correct location.

Usage:
    # From hypothesis data (inline JSON)
    python finalize_insights.py --json '[{"topic": "...", "universe": "crypto_test", ...}]'

    # From a draft file
    python finalize_insights.py --file draft_insights.json

    # With categories
    python finalize_insights.py --improve '[...]' --resurrect '[...]' --new '[...]'

Output:
    - insights.json (validated, in current directory)
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Valid universes - must match agents/config/universes.py
VALID_UNIVERSES = [
    "kr_stock", "us_stock", "us_etf", "vn_stock", "id_stock", "crypto_test",
]

VALID_CATEGORIES = [
    "momentum", "value", "quality", "growth", "size", "low_vol",
    "technical", "macro", "stat_arb", "event", "ml", "composite",
]


def validate_hypothesis(h: dict, category: str) -> list[str]:
    """Validate a single hypothesis dict. Returns list of errors."""
    errors = []

    # Required fields
    required = ["topic", "universe", "hypothesis"]
    for field in required:
        if field not in h or not h[field]:
            errors.append(f"Missing required field: {field}")

    # Universe check
    universe = h.get("universe", "")
    if universe and universe not in VALID_UNIVERSES:
        errors.append(f"Invalid universe: {universe}. Valid: {VALID_UNIVERSES}")

    # Category check for new ideas
    if category == "completely_new":
        cat = h.get("category", "")
        if cat and cat not in VALID_CATEGORIES:
            errors.append(f"Invalid category: {cat}. Valid: {VALID_CATEGORIES}")

    # related_research check
    if "related_research" not in h:
        errors.append("Missing related_research field (run search_research.py first)")
    else:
        rr = h.get("related_research", {})
        if not rr.get("checked"):
            errors.append("related_research.checked must be true")

    return errors


def validate_improve_hypothesis(h: dict) -> list[str]:
    """Validate improve_successes hypothesis."""
    errors = validate_hypothesis(h, "improve_successes")

    # Check for base_research
    if "base_research" not in h:
        errors.append("improve_successes requires base_research field")
    else:
        br = h.get("base_research", {})
        if "session_id" not in br:
            errors.append("base_research must have session_id")

    # Check for improvement plan
    if "improvement" not in h:
        errors.append("improve_successes requires improvement field")

    return errors


def validate_resurrect_hypothesis(h: dict) -> list[str]:
    """Validate resurrect_failures hypothesis."""
    errors = validate_hypothesis(h, "resurrect_failures")

    # Check for base_research
    if "base_research" not in h:
        errors.append("resurrect_failures requires base_research field")
    else:
        br = h.get("base_research", {})
        if "session_id" not in br:
            errors.append("base_research must have session_id")
        if "failure_reason" not in br:
            errors.append("base_research must have failure_reason")

    # Check for new approach
    if "new_approach" not in h:
        errors.append("resurrect_failures requires new_approach field")

    return errors


def validate_new_hypothesis(h: dict) -> list[str]:
    """Validate completely_new hypothesis."""
    errors = validate_hypothesis(h, "completely_new")

    # Check for approach
    if "approach" not in h:
        errors.append("completely_new requires approach field")

    # Check for novelty_score
    if "novelty_score" not in h:
        errors.append("completely_new requires novelty_score (1-10)")
    else:
        score = h.get("novelty_score", 0)
        if not isinstance(score, (int, float)) or score < 1 or score > 10:
            errors.append("novelty_score must be 1-10")

    return errors


def build_insights_json(
    improve: list[dict],
    resurrect: list[dict],
    new: list[dict],
) -> dict:
    """Build the final insights.json structure."""
    return {
        "improve_successes": improve,
        "resurrect_failures": resurrect,
        "completely_new": new,
        "gap_analysis": {
            "underexplored_categories": [],
            "notes": "",
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Finalize and validate insights.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Input options
    parser.add_argument("--json", help="JSON array of hypotheses (all go to completely_new)")
    parser.add_argument("--file", help="Path to draft JSON file")
    parser.add_argument("--improve", help="JSON array for improve_successes")
    parser.add_argument("--resurrect", help="JSON array for resurrect_failures")
    parser.add_argument("--new", help="JSON array for completely_new")

    # Output
    parser.add_argument("--output", default="insights.json", help="Output filename")
    parser.add_argument("--force", action="store_true", help="Skip validation errors")

    args = parser.parse_args()

    print("=" * 60)
    print("  FINALIZE INSIGHTS")
    print("=" * 60)

    # Parse input
    improve = []
    resurrect = []
    new = []

    if args.file:
        # Load from file
        try:
            with open(args.file) as f:
                data = json.load(f)
            improve = data.get("improve_successes", [])
            resurrect = data.get("resurrect_failures", [])
            new = data.get("completely_new", [])
            print(f"  Loaded from: {args.file}")
        except Exception as e:
            print(f"  ✗ Failed to load file: {e}")
            sys.exit(1)
    elif args.json:
        # Simple JSON array -> all go to completely_new
        try:
            new = json.loads(args.json)
            print(f"  Loaded {len(new)} hypotheses from --json")
        except Exception as e:
            print(f"  ✗ Failed to parse JSON: {e}")
            sys.exit(1)
    else:
        # Category-specific inputs
        if args.improve:
            try:
                improve = json.loads(args.improve)
            except Exception as e:
                print(f"  ✗ Failed to parse --improve: {e}")
                sys.exit(1)
        if args.resurrect:
            try:
                resurrect = json.loads(args.resurrect)
            except Exception as e:
                print(f"  ✗ Failed to parse --resurrect: {e}")
                sys.exit(1)
        if args.new:
            try:
                new = json.loads(args.new)
            except Exception as e:
                print(f"  ✗ Failed to parse --new: {e}")
                sys.exit(1)

    total = len(improve) + len(resurrect) + len(new)
    if total == 0:
        print("  ✗ No hypotheses provided")
        print("  Usage: finalize_insights.py --json '[{...}]' or --file draft.json")
        sys.exit(1)

    print(f"  Total hypotheses: {total}")
    print(f"    improve_successes: {len(improve)}")
    print(f"    resurrect_failures: {len(resurrect)}")
    print(f"    completely_new: {len(new)}")

    # Validate
    print()
    print("─" * 60)
    print("  Validation")
    print("─" * 60)

    all_errors = []

    for i, h in enumerate(improve):
        errors = validate_improve_hypothesis(h)
        if errors:
            all_errors.append(f"improve_successes[{i}]: {errors}")

    for i, h in enumerate(resurrect):
        errors = validate_resurrect_hypothesis(h)
        if errors:
            all_errors.append(f"resurrect_failures[{i}]: {errors}")

    for i, h in enumerate(new):
        errors = validate_new_hypothesis(h)
        if errors:
            all_errors.append(f"completely_new[{i}]: {errors}")

    if all_errors:
        print("  ⚠ Validation issues:")
        for err in all_errors:
            print(f"    - {err}")
        if not args.force:
            print()
            print("  Use --force to save anyway")
            sys.exit(1)
        print("  Continuing with --force...")
    else:
        print("  ✓ All hypotheses valid")

    # Build output
    insights = build_insights_json(improve, resurrect, new)

    # Save
    print()
    print("─" * 60)
    print("  Output")
    print("─" * 60)

    output_path = Path(args.output)
    try:
        with open(output_path, "w") as f:
            json.dump(insights, f, ensure_ascii=False, indent=2)
        print(f"  ✓ Saved: {output_path}")
    except Exception as e:
        print(f"  ✗ Failed to save: {e}")
        sys.exit(1)

    # Summary
    print()
    print("=" * 60)
    print("  ✅ FINALIZE COMPLETE")
    print("=" * 60)

    # Show topics
    print()
    print("  Topics generated:")
    for h in improve:
        print(f"    [IMPROVE] {h.get('topic', 'N/A')} on {h.get('universe', 'N/A')}")
    for h in resurrect:
        print(f"    [RESURRECT] {h.get('topic', 'N/A')} on {h.get('universe', 'N/A')}")
    for h in new:
        print(f"    [NEW] {h.get('topic', 'N/A')} on {h.get('universe', 'N/A')}")
    print()


if __name__ == "__main__":
    main()
