#!/usr/bin/env python3
"""Search past research for similar topics.

Usage:
    python scripts/search_research.py "momentum strategy on kr_stock"
    python scripts/search_research.py "volatility clustering" --top 5
    python scripts/search_research.py "value investing" --universe us_stock

This script searches the research ChromaDB for similar past research,
helping InsightAgent avoid duplicates and build on existing work.
"""

import argparse
import json
import os
import sys

# Add project root to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(script_dir))))
sys.path.insert(0, project_root)

from src.claude_agents.insight.research_db import get_research_db


def search_research(
    query: str,
    email: str | None = None,
    top_k: int = 5,
    universe: str | None = None,
    category: str | None = None,
    verdict: str | None = None,
    skip_sync: bool = False,
) -> list[dict]:
    """
    Search past research for similar topics.

    Args:
        query: Search query (topic, hypothesis, or keywords)
        email: User email for ChromaDB (uses env var if not provided)
        top_k: Number of results to return
        universe: Filter by universe (kr_stock, us_stock, etc.)
        category: Filter by category (momentum, value, etc.)
        verdict: Filter by verdict (DEPLOYED, FAILED)
        skip_sync: Skip S3 sync for faster search (use when DB already synced)

    Returns:
        List of similar research with similarity scores
    """
    if email is None:
        email = os.environ.get("FINTER_USER_EMAIL", "dhlee@quantit.io")

    db = get_research_db(email)

    # Sync from S3 first (unless skipped)
    if not skip_sync:
        try:
            stats = db.sync_from_s3(email)
            if stats["indexed"] > 0:
                print(f"[Synced {stats['indexed']} new research from S3]", file=sys.stderr)
        except Exception as e:
            print(f"[Sync warning: {e}]", file=sys.stderr)

    # Search
    results = db.search(
        query=query,
        n_results=top_k,
        universe=universe,
        category=category,
        verdict=verdict,
    )

    return results


def format_result(result: dict, index: int) -> str:
    """Format a single search result for display."""
    metadata = result.get("metadata", {})
    similarity = result.get("similarity", 0)

    lines = [
        f"\n{'='*60}",
        f"[{index}] {metadata.get('title', 'N/A')} (similarity: {similarity:.2f})",
        f"{'='*60}",
        f"Session: {metadata.get('session_id', 'N/A')[:12]}...",
        f"Universe: {metadata.get('universe', 'N/A')} | Category: {metadata.get('category', 'N/A')}",
        f"Verdict: {metadata.get('verdict', 'N/A')} | Sharpe: {metadata.get('sharpe', 0):.2f}",
        f"\n--- Summary ---",
        result.get("document", "N/A")[:500],
    ]

    if len(result.get("document", "")) > 500:
        lines.append("... [truncated]")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Search past research for similar topics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single query
  python search_research.py "momentum strategy"

  # Batch mode (multiple queries, one DB load)
  python search_research.py --batch "momentum" "value factor" "event driven"

  # With filters
  python search_research.py "event driven" --deployed-only --no-sync
  python search_research.py "high turnover" --failed-only --no-sync
""",
    )
    parser.add_argument("query", nargs="?", help="Search query (topic, hypothesis, or keywords)")
    parser.add_argument("--batch", nargs="+", help="Multiple queries in one call (faster)")
    parser.add_argument("--top", type=int, default=5, help="Number of results (default: 5)")
    parser.add_argument("--universe", help="Filter by universe (kr_stock, us_stock, etc.)")
    parser.add_argument("--category", help="Filter by category (momentum, value, etc.)")
    parser.add_argument("--email", help="User email (default: from env or dhlee@quantit.io)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--deployed-only", action="store_true", help="Show only DEPLOYED research (for IMPROVE SUCCESSES)")
    parser.add_argument("--failed-only", action="store_true", help="Show only FAILED research (for RESURRECT FAILURES)")
    parser.add_argument("--no-sync", action="store_true", help="Skip S3 sync (faster, use when DB already synced)")

    args = parser.parse_args()

    # Determine verdict filter
    verdict = None
    if args.deployed_only:
        verdict = "DEPLOYED"
    elif args.failed_only:
        verdict = "FAILED"

    # Handle batch mode
    if args.batch:
        queries = args.batch
    elif args.query:
        queries = [args.query]
    else:
        parser.error("Either query or --batch is required")
        return

    all_results = {}
    for query in queries:
        results = search_research(
            query=query,
            email=args.email,
            top_k=args.top,
            universe=args.universe,
            category=args.category,
            verdict=verdict,
            skip_sync=args.no_sync,
        )
        all_results[query] = results
        # Only sync once for batch
        args.no_sync = True

    if args.json:
        print(json.dumps(all_results if len(queries) > 1 else results, indent=2, ensure_ascii=False))
    elif len(queries) == 1:
        # Single query output
        results = all_results[queries[0]]
        if not results:
            print(f"\nNo similar research found for: '{queries[0]}'")
            print("This appears to be a NEW topic - no prior research exists.")
        else:
            print(f"\n🔍 Found {len(results)} similar research for: '{queries[0]}'")
            for i, result in enumerate(results, 1):
                print(format_result(result, i))

            # Summary
            print(f"\n{'='*60}")
            print("📋 SUMMARY FOR INSIGHT AGENT")
            print(f"{'='*60}")

            high_similarity = [r for r in results if r.get("similarity", 0) > 0.7]
            if high_similarity:
                print(f"⚠️  HIGH SIMILARITY ({len(high_similarity)} results > 0.7):")
                print("   - Consider IMPROVING existing research instead of new topic")
                print("   - Or differentiate clearly (different universe, approach, etc.)")
            else:
                print("✅ No highly similar research found.")
                print("   - This topic appears sufficiently novel")
                print("   - But review above results for useful context")
    else:
        # Batch mode output
        print(f"\n🔍 BATCH SEARCH RESULTS ({len(queries)} queries)")
        print("=" * 60)

        for query in queries:
            results = all_results[query]
            max_sim = max((r.get("similarity", 0) for r in results), default=0)
            top_match = results[0].get("metadata", {}).get("title", "N/A") if results else "None"

            # Status indicator
            if max_sim > 0.5:
                status = "⚠️ HIGH"
            elif max_sim > 0.3:
                status = "⚡ MED"
            else:
                status = "✅ LOW"

            print(f"\n[{query}]")
            print(f"  {status} (max_sim: {max_sim:.2f}) → {top_match[:50]}")

            # Show top 2 results briefly
            for r in results[:2]:
                sim = r.get("similarity", 0)
                title = r.get("metadata", {}).get("title", "N/A")[:40]
                verdict = r.get("metadata", {}).get("verdict", "?")
                print(f"    - {sim:.2f} [{verdict}] {title}")


if __name__ == "__main__":
    main()
