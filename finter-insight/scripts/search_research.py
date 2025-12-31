#!/usr/bin/env python3
"""Search past research for similar topics.

Usage:
    python scripts/search_research.py "momentum strategy on kr_stock"
    python scripts/search_research.py "volatility clustering" --top 5
    python scripts/search_research.py --batch "momentum" "value" "quality"

This script searches the local ChromaDB for similar past research.
The DB is synced by InsightAgent at the start of each cycle.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# ChromaDB imports
try:
    import chromadb
    from chromadb.utils import embedding_functions
except ImportError:
    print("ERROR: chromadb not installed. Run: pip install chromadb", file=sys.stderr)
    sys.exit(1)

# Constants (must match research_db.py)
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
RESEARCH_CHROMADB_BASE = Path("./.research_chromadb")


def get_chromadb_path(email: str) -> Path:
    """Get ChromaDB path for user."""
    safe_email = email.replace("@", "_at_").replace(".", "_")
    return RESEARCH_CHROMADB_BASE / safe_email


def search_research(
    query: str,
    email: str,
    top_k: int = 5,
    universe: str | None = None,
    category: str | None = None,
    verdict: str | None = None,
) -> list[dict]:
    """
    Search past research for similar topics.

    Args:
        query: Search query (topic, hypothesis, or keywords)
        email: User email for ChromaDB path
        top_k: Number of results to return
        universe: Filter by universe (kr_stock, us_stock, etc.)
        category: Filter by category (momentum, value, etc.)
        verdict: Filter by verdict (DEPLOYED, FAILED)

    Returns:
        List of similar research with similarity scores
    """
    db_path = get_chromadb_path(email)

    if not db_path.exists():
        print(f"[No research DB found at {db_path}]", file=sys.stderr)
        return []

    try:
        # Initialize ChromaDB client
        client = chromadb.PersistentClient(path=str(db_path))

        # Embedding function (same as research_db.py)
        embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=DEFAULT_EMBEDDING_MODEL
        )

        # Get collection
        try:
            collection = client.get_collection(
                name="research_summaries",
                embedding_function=embed_fn,
            )
        except Exception:
            print("[Collection 'research_summaries' not found]", file=sys.stderr)
            return []

        # Build where filter
        where_filter = {}
        if universe:
            where_filter["universe"] = universe
        if category:
            where_filter["category"] = category
        if verdict:
            where_filter["verdict"] = verdict

        # Query
        query_kwargs = {
            "query_texts": [query],
            "n_results": top_k,
        }
        if where_filter:
            query_kwargs["where"] = where_filter

        results = collection.query(**query_kwargs)

        # Format results
        formatted = []
        if results and results.get("documents"):
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
            distances = results["distances"][0] if results.get("distances") else [0] * len(docs)

            for doc, meta, dist in zip(docs, metas, distances):
                # Convert distance to similarity (ChromaDB uses L2 distance)
                similarity = 1 / (1 + dist)
                formatted.append({
                    "document": doc,
                    "metadata": meta,
                    "similarity": round(similarity, 3),
                })

        return formatted

    except Exception as e:
        print(f"[Search error: {e}]", file=sys.stderr)
        return []


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
  python search_research.py "event driven" --deployed-only
  python search_research.py "high turnover" --failed-only
""",
    )
    parser.add_argument("query", nargs="?", help="Search query (topic, hypothesis, or keywords)")
    parser.add_argument("--batch", nargs="+", help="Multiple queries in one call (faster)")
    parser.add_argument("--top", type=int, default=5, help="Number of results (default: 5)")
    parser.add_argument("--universe", help="Filter by universe (kr_stock, us_stock, etc.)")
    parser.add_argument("--category", help="Filter by category (momentum, value, etc.)")
    parser.add_argument("--email", default=os.environ.get("FINTER_USER_EMAIL", "dhlee@quantit.io"),
                        help="User email (default: from env or dhlee@quantit.io)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--deployed-only", action="store_true", help="Show only DEPLOYED research")
    parser.add_argument("--failed-only", action="store_true", help="Show only FAILED research")

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
        )
        all_results[query] = results

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
                verdict_str = r.get("metadata", {}).get("verdict", "?")
                print(f"    - {sim:.2f} [{verdict_str}] {title}")


if __name__ == "__main__":
    main()
