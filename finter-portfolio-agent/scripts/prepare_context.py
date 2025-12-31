#!/usr/bin/env python3
"""Prepare alpha context for Portfolio Manager evaluation.

This script loads eligible alphas from alpha_pool and prepares context
for PM evaluation in Jupyter.

Usage:
    python prepare_context.py --request-id REQUEST_ID [--email EMAIL]
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class AlphaContext:
    """Context for a single alpha candidate."""

    session_id: str
    model_id: str | None

    # Research Summary
    hypothesis: str
    findings: str
    conclusion: str

    # Backtest Metrics
    sharpe: float | None
    mdd: float | None
    turnover: float | None
    cagr: float | None
    hit_ratio: float | None

    # Status
    status: str
    finter_submit_status: str | None
    finter_prod_status: str | None

    # Paths
    code_path: str | None
    nav_path: str | None

    def is_eligible(self) -> bool:
        """Check if alpha is eligible for PM evaluation."""
        return (
            self.status == "deployed"
            and self.finter_submit_status == "success"
            and self.finter_prod_status == "success"
        )


def load_alpha_pool(request_id: str, email: str | None = None) -> list[dict[str, Any]]:
    """Load alpha pool from local file or S3.

    Args:
        request_id: Request ID
        email: User email for S3 path

    Returns:
        List of alpha pool entries
    """
    # Try local file first
    local_path = Path(f"./alpha_pool_{request_id}.json")
    if local_path.exists():
        with open(local_path, "r") as f:
            return json.load(f)

    # Try workspace path
    workspace_path = Path(f"./portfolio/alpha_pool.json")
    if workspace_path.exists():
        with open(workspace_path, "r") as f:
            return json.load(f)

    print(f"Warning: alpha_pool not found locally. You may need to download from S3.")
    print(f"S3 path: s3://ark.quantit.ai/expert/research/{email}/requests/{request_id}/alpha_pool.json")
    return []


def load_research_summary(session_id: str, request_id: str) -> dict[str, str]:
    """Load research summary from workflow_state.

    Args:
        session_id: Session ID
        request_id: Request ID

    Returns:
        Dict with hypothesis, findings, conclusion
    """
    # Try local file
    local_path = Path(f"./sessions/{session_id}/workflow_state.json")
    if local_path.exists():
        with open(local_path, "r") as f:
            state = json.load(f)
            summary = state.get("research_summary", {})
            return {
                "hypothesis": summary.get("topic", ""),
                "findings": summary.get("what_worked", []),
                "conclusion": summary.get("conclusion", ""),
            }

    return {"hypothesis": "", "findings": "", "conclusion": ""}


def prepare_contexts(request_id: str, email: str | None = None) -> list[AlphaContext]:
    """Prepare evaluation contexts for all eligible alphas.

    Args:
        request_id: Request ID
        email: User email

    Returns:
        List of AlphaContext objects for eligible alphas
    """
    pool = load_alpha_pool(request_id, email)
    contexts = []

    for entry in pool:
        session_id = entry.get("session_id", "")
        summary = load_research_summary(session_id, request_id)

        # Extract metrics
        metrics = entry.get("backtest_metrics", {})

        context = AlphaContext(
            session_id=session_id,
            model_id=entry.get("model_id"),
            hypothesis=summary["hypothesis"],
            findings=str(summary["findings"]),
            conclusion=summary["conclusion"],
            sharpe=metrics.get("sharpe"),
            mdd=metrics.get("max_drawdown"),
            turnover=metrics.get("turnover"),
            cagr=metrics.get("cagr"),
            hit_ratio=metrics.get("hit_ratio"),
            status=entry.get("status", ""),
            finter_submit_status=entry.get("finter_submit_status"),
            finter_prod_status=entry.get("finter_prod_status"),
            code_path=f"./sessions/{session_id}/alpha.py",
            nav_path=f"./portfolio/nav_{session_id}.parquet",
        )

        contexts.append(context)

    return contexts


def main():
    parser = argparse.ArgumentParser(description="Prepare alpha context for PM evaluation")
    parser.add_argument("--request-id", required=True, help="Request ID")
    parser.add_argument("--email", help="User email for S3 paths")
    parser.add_argument("--output", default="alpha_contexts.json", help="Output file")
    args = parser.parse_args()

    print(f"Loading alpha pool for request: {args.request_id}")
    contexts = prepare_contexts(args.request_id, args.email)

    # Filter eligible only
    eligible = [c for c in contexts if c.is_eligible()]

    print(f"\n=== Summary ===")
    print(f"Total alphas: {len(contexts)}")
    print(f"Eligible for evaluation: {len(eligible)}")

    if not eligible:
        print("\nNo eligible alphas found. Eligibility requires:")
        print("  - status == 'deployed'")
        print("  - finter_submit_status == 'success'")
        print("  - finter_prod_status == 'success'")
        sys.exit(0)

    print(f"\n=== Eligible Alphas ===")
    for ctx in eligible:
        sharpe_str = f"{ctx.sharpe:.2f}" if ctx.sharpe else "N/A"
        print(f"  {ctx.session_id}: Sharpe={sharpe_str}, Hypothesis: {ctx.hypothesis[:50]}...")

    # Save to file
    output_data = [asdict(c) for c in eligible]
    with open(args.output, "w") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\nContext saved to: {args.output}")
    print("\nNext steps:")
    print("1. Load this file in Jupyter")
    print("2. Analyze each alpha (correlation, code review, metrics)")
    print("3. Output PMEvaluation for each alpha")
    print("4. Run finalize_portfolio.py to save results")


if __name__ == "__main__":
    main()
