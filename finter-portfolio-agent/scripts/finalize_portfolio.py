#!/usr/bin/env python3
"""Finalize portfolio evaluation and save results.

This script validates PM evaluations, calculates weights, and saves
the final portfolio_state.json and portfolio.py.

Usage:
    python finalize_portfolio.py --request-id REQUEST_ID --evaluations evaluations.json
    python finalize_portfolio.py --request-id REQUEST_ID --evaluations evaluations.json --generate-code

    # Submit portfolio to Finter
    python finalize_portfolio.py --request-id REQUEST_ID --submit --market vn_stock
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


# =============================================================================
# Model ID Conversion
# =============================================================================

def model_id_to_alpha_list_entry(model_id: str) -> str:
    """Convert Finter model_id to alpha_list entry format.

    Finter submission returns model_id like:
        alpha.vnm.fiintek.stock.ldh0127.Strategy_Name

    BasePortfolio's alpha_list expects format WITHOUT 'alpha.' prefix:
        vnm.fiintek.stock.ldh0127.Strategy_Name

    Args:
        model_id: Full model ID from Finter (starts with 'alpha.')

    Returns:
        Alpha list entry (without 'alpha.' prefix)
    """
    if model_id.startswith("alpha."):
        return model_id[6:]  # Strip "alpha." (6 chars)
    return model_id


def alpha_list_entry_to_model_id(entry: str) -> str:
    """Convert alpha_list entry back to full model_id.

    Args:
        entry: Alpha list entry (e.g., vnm.fiintek.stock.ldh0127.Name)

    Returns:
        Full model ID with 'alpha.' prefix
    """
    if not entry.startswith("alpha."):
        return f"alpha.{entry}"
    return entry


# =============================================================================
# Portfolio.py Generation
# =============================================================================

def generate_portfolio_code(
    alpha_entries: list[str],
    market: str = "vn_stock",
    weight_method: str = "equal",
) -> str:
    """Generate portfolio.py code from alpha list.

    Args:
        alpha_entries: List of alpha_list entries (WITHOUT alpha. prefix)
        market: Market type (kr_stock, us_stock, vn_stock, etc.)
        weight_method: Weight calculation method

    Returns:
        Portfolio class code as string
    """
    # Format alpha_list for code
    alpha_list_str = ",\n        ".join(f'"{e}"' for e in alpha_entries)

    code = f'''"""
Portfolio - Auto-generated from PM evaluation.

Generated: {datetime.now().isoformat()}
Market: {market}
Weight Method: {weight_method}
Alpha Count: {len(alpha_entries)}
"""

from finter import BasePortfolio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def calculate_previous_start_date(start_date: int, lookback_days: int) -> int:
    """Calculate start date for preloading data."""
    start = datetime.strptime(str(start_date), "%Y%m%d")
    previous_start = start - timedelta(days=lookback_days)
    return int(previous_start.strftime("%Y%m%d"))


class Portfolio(BasePortfolio):
    """
    Portfolio combining {len(alpha_entries)} selected alphas.
    Weight method: {weight_method}
    """

    alpha_list = [
        {alpha_list_str}
    ]

    def weight(self, start: int, end: int) -> pd.DataFrame:
        """Calculate portfolio weights."""
        # Load alpha returns
        preload_start = calculate_previous_start_date(start, 365)
        alpha_return_df = self.alpha_pnl_df('{market}', preload_start, end)

        # Clean consecutive 1's (data artifacts)
        find_1 = (alpha_return_df == 1) & (alpha_return_df.shift(1) == 1)
        alpha_return_df = alpha_return_df.mask(find_1, np.nan).ffill(limit=5)

        # Equal weight: 1/N
        n_alphas = len(self.alpha_list)
        weights = pd.DataFrame(
            1.0 / n_alphas,
            index=alpha_return_df.index,
            columns=alpha_return_df.columns
        )

        # Static weights don't need shift(1)
        return weights.loc[str(start):str(end)]


if __name__ == "__main__":
    from finter.backtest import Simulator

    portfolio = Portfolio()
    end_date = int(datetime.now().strftime("%Y%m%d"))

    # Generate weights
    weights = portfolio.weight(20200101, end_date)
    print(f"Weights shape: {{weights.shape}}")
    print(f"Weight sum check: {{weights.sum(axis=1).describe()}}")

    # Backtest
    simulator = Simulator(market_type="{market}")
    result = simulator.run(position=portfolio.get(20200101, end_date))

    stats = result.statistics
    print(f"\\nPerformance:")
    print(f"  Sharpe: {{stats['Sharpe Ratio']:.2f}}")
    print(f"  Max DD: {{stats['Max Drawdown (%)']:.2f}}%")
'''
    return code


def load_evaluations(path: str) -> list[dict[str, Any]]:
    """Load PMEvaluation list from JSON file."""
    with open(path, "r") as f:
        return json.load(f)


def validate_evaluation(eval_dict: dict[str, Any]) -> list[str]:
    """Validate a single PMEvaluation.

    Returns list of validation errors (empty if valid).
    """
    errors = []

    # Required fields
    required = ["session_id", "recommendation"]
    for field in required:
        if field not in eval_dict:
            errors.append(f"Missing required field: {field}")

    # Validate enum values
    if eval_dict.get("rationale_alignment") not in ["aligned", "partial", "misaligned", None]:
        errors.append(f"Invalid rationale_alignment: {eval_dict.get('rationale_alignment')}")

    if eval_dict.get("economic_sense") not in ["strong", "moderate", "weak", "questionable", None]:
        errors.append(f"Invalid economic_sense: {eval_dict.get('economic_sense')}")

    if eval_dict.get("portfolio_contribution") not in ["core", "diversifier", "hedge", "redundant", None]:
        errors.append(f"Invalid portfolio_contribution: {eval_dict.get('portfolio_contribution')}")

    if eval_dict.get("recommendation") not in ["select", "exclude", "review"]:
        errors.append(f"Invalid recommendation: {eval_dict.get('recommendation')}")

    return errors


def calculate_equal_weights(selected_session_ids: list[str]) -> dict[str, float]:
    """Calculate equal weights for selected alphas."""
    if not selected_session_ids:
        return {}

    n = len(selected_session_ids)
    weight = 1.0 / n
    return {sid: weight for sid in selected_session_ids}


def build_portfolio_state(
    request_id: str,
    evaluations: list[dict[str, Any]],
    weight_method: str = "equal",
) -> dict[str, Any]:
    """Build PortfolioState from evaluations.

    Args:
        request_id: Request ID
        evaluations: List of PMEvaluation dicts
        weight_method: Weight calculation method

    Returns:
        PortfolioState as dict
    """
    # Categorize by recommendation
    selected = [e["session_id"] for e in evaluations if e.get("recommendation") == "select"]
    needs_review = [e["session_id"] for e in evaluations if e.get("recommendation") == "review"]

    # Calculate weights
    if weight_method == "equal":
        weights = calculate_equal_weights(selected)
    else:
        # Future: risk parity, etc.
        weights = calculate_equal_weights(selected)

    return {
        "request_id": request_id,
        "portfolio_version": 1,
        "updated_at": datetime.now().isoformat(),
        "evaluations": evaluations,
        "selected_alphas": selected,
        "weights": weights,
        "weight_method": weight_method,
        "combined_sharpe": None,  # Calculated separately
        "combined_mdd": None,
        "avg_pairwise_correlation": None,
        "needs_review": needs_review,
    }


def print_summary(state: dict[str, Any]) -> None:
    """Print portfolio summary."""
    print("\n" + "=" * 60)
    print("PORTFOLIO SUMMARY")
    print("=" * 60)

    print(f"\nRequest ID: {state['request_id']}")
    print(f"Version: {state['portfolio_version']}")
    print(f"Updated: {state['updated_at']}")

    print(f"\n--- Selections ---")
    print(f"Selected: {len(state['selected_alphas'])}")
    print(f"Needs Review: {len(state['needs_review'])}")
    excluded = len(state['evaluations']) - len(state['selected_alphas']) - len(state['needs_review'])
    print(f"Excluded: {excluded}")

    if state['selected_alphas']:
        print(f"\n--- Selected Alphas ---")
        for sid in state['selected_alphas']:
            weight = state['weights'].get(sid, 0)
            print(f"  {sid}: {weight:.2%}")

    if state['needs_review']:
        print(f"\n--- Needs Human Review ---")
        for sid in state['needs_review']:
            # Find the evaluation
            for e in state['evaluations']:
                if e['session_id'] == sid:
                    reason = e.get('final_reasoning', 'No reason provided')
                    print(f"  {sid}: {reason[:50]}...")
                    break

    print("\n" + "=" * 60)


# =============================================================================
# Portfolio Submission
# =============================================================================

def extract_user_prefix(email: str) -> str:
    """Extract user prefix from email for model_id.

    Examples:
        dhlee@quantit.io -> ldh0127 (simplified: first letter + last 4)
        test@example.com -> test

    For simplicity, we use the part before @ as the user prefix.
    """
    if not email:
        return "user"
    local_part = email.split("@")[0]
    # Sanitize: only alphanumeric and underscore
    import re
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "", local_part)
    return sanitized[:20] if sanitized else "user"


def load_portfolio_state_from_file(path: str) -> dict[str, Any] | None:
    """Load portfolio_state.json from file."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading portfolio_state.json: {e}")
        return None


def load_portfolio_code(path: str) -> str | None:
    """Load portfolio.py code from file."""
    try:
        with open(path, "r") as f:
            return f.read()
    except Exception as e:
        print(f"Error loading portfolio.py: {e}")
        return None


def submit_portfolio_to_finter(
    portfolio_code: str,
    portfolio_name: str,
    market: str,
    email: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Submit portfolio to Finter.

    Args:
        portfolio_code: Portfolio code (portfolio.py content)
        portfolio_name: Portfolio name (e.g., VN_QualityMomentum_14Alpha)
        market: Market type (vn_stock, kr_stock, etc.)
        email: User email (for user_prefix extraction)
        api_key: Finter API key (uses env var if not provided)

    Returns:
        dict with success, model_id, version, error
    """
    # Get API key from env if not provided
    if not api_key:
        api_key = os.environ.get("FINTER_API_KEY")
        if not api_key:
            return {"success": False, "error": "FINTER_API_KEY not set"}

    # Extract user prefix
    user_prefix = extract_user_prefix(email) if email else "user"

    try:
        # Import here to avoid circular imports
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
        from agents.integrations.submit import (
            submit_portfolio,
            get_universe_prefix,
            get_next_portfolio_version,
            sanitize_model_name,
        )

        # Get universe prefix and version
        universe_prefix = get_universe_prefix(market)
        sanitized_name = sanitize_model_name(portfolio_name, max_length=20)
        version = get_next_portfolio_version(universe_prefix, user_prefix, sanitized_name)

        print(f"\n--- Submitting Portfolio ---")
        print(f"  Name: {sanitized_name}")
        print(f"  Version: v{version}")
        print(f"  Market: {market}")
        print(f"  User: {user_prefix}")

        # Submit
        result = submit_portfolio(
            code=portfolio_code,
            universe=market,  # type: ignore
            finter_api_key=api_key,
            portfolio_name=portfolio_name,
            version=version,
            user_prefix=user_prefix,
        )

        if result.success:
            print(f"\n  ✓ Submitted: {result.model_id}")
            print(f"  Log URL: {result.log_url}")
            return {
                "success": True,
                "model_id": result.model_id,
                "version": version,
                "log_url": result.log_url,
            }
        else:
            print(f"\n  ✗ Failed: {result.error}")
            return {"success": False, "error": result.error}

    except Exception as e:
        print(f"\n  ✗ Exception: {e}")
        return {"success": False, "error": str(e)}


def update_portfolio_state_after_submit(
    state_path: str,
    model_id: str,
    version: int,
    status: str = "success",
) -> None:
    """Update portfolio_state.json with submit results.

    Args:
        state_path: Path to portfolio_state.json
        model_id: Submitted model ID
        version: Version number
        status: Submit status (success/failed)
    """
    try:
        with open(state_path, "r") as f:
            state = json.load(f)

        state["model_id"] = model_id
        state["portfolio_version"] = version
        state["submit_status"] = status
        state["submitted_at"] = datetime.now().isoformat()
        state["updated_at"] = datetime.now().isoformat()

        with open(state_path, "w") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

        print(f"\n  ✓ Updated {state_path}")

    except Exception as e:
        print(f"\n  Warning: Could not update portfolio_state.json: {e}")


def main():
    parser = argparse.ArgumentParser(description="Finalize portfolio evaluation")
    parser.add_argument("--request-id", required=False, help="Request ID")
    parser.add_argument("--evaluations", required=False, help="Path to evaluations JSON")
    parser.add_argument("--weight-method", default="equal", choices=["equal"],
                        help="Weight calculation method")

    # Submit options
    parser.add_argument("--submit", action="store_true",
                        help="Submit portfolio to Finter after generation")
    parser.add_argument("--email", help="User email (for model_id prefix)")
    parser.add_argument("--api-key", help="Finter API key (uses FINTER_API_KEY env if not set)")
    parser.add_argument("--portfolio-name", help="Override portfolio name for submission")
    parser.add_argument("--output", default="portfolio_state.json", help="Output file")
    parser.add_argument("--generate-code", action="store_true",
                        help="Generate portfolio.py code file")
    parser.add_argument("--market", default="vn_stock",
                        choices=["kr_stock", "us_stock", "vn_stock", "id_stock", "us_etf"],
                        help="Market type for portfolio.py")
    parser.add_argument("--code-output", default="portfolio.py",
                        help="Output path for portfolio.py")
    args = parser.parse_args()

    # Submit-only mode: if --submit without --evaluations, just submit existing portfolio
    if args.submit and not args.evaluations:
        print("=" * 60)
        print("PORTFOLIO SUBMISSION (Submit-only mode)")
        print("=" * 60)

        # Load existing portfolio_state.json
        state = load_portfolio_state_from_file(args.output)
        if not state:
            print(f"\nError: Cannot load {args.output}. Create with --evaluations first.")
            sys.exit(1)

        # Load portfolio code
        portfolio_code = load_portfolio_code(args.code_output)
        if not portfolio_code:
            print(f"\nError: Cannot load {args.code_output}. Generate with --generate-code first.")
            sys.exit(1)

        # Get portfolio name
        portfolio_name = args.portfolio_name or state.get("portfolio_name", "")
        if not portfolio_name:
            n_selected = len(state.get("selected_alphas", []))
            portfolio_name = f"{args.market.upper().replace('_', '')}_{n_selected}Alpha"

        print(f"\nPortfolio: {portfolio_name}")
        print(f"Market: {args.market}")
        print(f"Selected alphas: {len(state.get('selected_alphas', []))}")

        # Submit
        result = submit_portfolio_to_finter(
            portfolio_code=portfolio_code,
            portfolio_name=portfolio_name,
            market=args.market,
            email=args.email,
            api_key=args.api_key,
        )

        if result.get("success"):
            update_portfolio_state_after_submit(
                state_path=args.output,
                model_id=result.get("model_id", ""),
                version=result.get("version", 1),
                status="success",
            )
            print("\n✓ Portfolio submitted successfully!")
            sys.exit(0)
        else:
            print(f"\n✗ Submission failed: {result.get('error')}")
            sys.exit(1)

    # Regular mode: requires --evaluations
    if not args.evaluations:
        print("Error: --evaluations is required (or use --submit without it for submit-only mode)")
        sys.exit(1)

    print(f"Loading evaluations from: {args.evaluations}")
    evaluations = load_evaluations(args.evaluations)
    print(f"Loaded {len(evaluations)} evaluations")

    # Validate all evaluations
    print("\nValidating evaluations...")
    all_errors = []
    for i, e in enumerate(evaluations):
        errors = validate_evaluation(e)
        if errors:
            all_errors.append(f"Evaluation {i} ({e.get('session_id', 'unknown')}): {errors}")

    if all_errors:
        print("\nValidation FAILED:")
        for err in all_errors:
            print(f"  - {err}")
        sys.exit(1)

    print("All evaluations valid!")

    # Build portfolio state
    print(f"\nBuilding portfolio state with {args.weight_method} weights...")
    state = build_portfolio_state(args.request_id, evaluations, args.weight_method)

    # Print summary
    print_summary(state)

    # Save portfolio_state.json
    with open(args.output, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

    print(f"\nPortfolio state saved to: {args.output}")

    # Generate portfolio.py if requested
    n_selected = len(state['selected_alphas'])
    n_review = len(state['needs_review'])

    if args.generate_code and n_selected > 0:
        print(f"\n--- Generating portfolio.py ---")

        # Get model_ids for selected alphas
        selected_model_ids = []
        for e in evaluations:
            if e.get("recommendation") == "select" and e.get("model_id"):
                selected_model_ids.append(e["model_id"])

        if selected_model_ids:
            # Convert to alpha_list format (strip alpha. prefix)
            alpha_entries = [model_id_to_alpha_list_entry(mid) for mid in selected_model_ids]

            print(f"  Alpha count: {len(alpha_entries)}")
            print(f"  Market: {args.market}")
            print(f"  Weight method: {args.weight_method}")

            # Generate code
            code = generate_portfolio_code(
                alpha_entries=alpha_entries,
                market=args.market,
                weight_method=args.weight_method,
            )

            # Save to file
            with open(args.code_output, "w") as f:
                f.write(code)

            print(f"  Portfolio code saved to: {args.code_output}")
        else:
            print("  WARNING: No model_ids found in selected evaluations. Skipping code generation.")

    if n_selected == 0:
        print("\nWARNING: No alphas selected! Portfolio is empty.")
        if n_review > 0:
            print(f"Consider reviewing the {n_review} alphas marked for review.")

    # Submit portfolio if requested
    if args.submit and n_selected > 0:
        print("\n" + "=" * 60)
        print("PORTFOLIO SUBMISSION")
        print("=" * 60)

        # Load portfolio code
        portfolio_code = load_portfolio_code(args.code_output)
        if not portfolio_code:
            print(f"\nError: Cannot submit without portfolio.py. Generate with --generate-code first.")
            sys.exit(1)

        # Get portfolio name from state or args
        portfolio_name = args.portfolio_name or state.get("portfolio_name", "")
        if not portfolio_name:
            # Generate default name from request_id
            portfolio_name = f"{args.market.upper().replace('_', '')}_{n_selected}Alpha"

        # Submit to Finter
        submit_result = submit_portfolio_to_finter(
            portfolio_code=portfolio_code,
            portfolio_name=portfolio_name,
            market=args.market,
            email=args.email,
            api_key=args.api_key,
        )

        # Update portfolio_state.json
        if submit_result.get("success"):
            update_portfolio_state_after_submit(
                state_path=args.output,
                model_id=submit_result.get("model_id", ""),
                version=submit_result.get("version", 1),
                status="success",
            )
            print("\n✓ Portfolio submitted successfully!")
        else:
            update_portfolio_state_after_submit(
                state_path=args.output,
                model_id="",
                version=0,
                status="failed",
            )
            print(f"\n✗ Submission failed: {submit_result.get('error')}")
            sys.exit(1)

    elif args.submit and n_selected == 0:
        print("\nERROR: Cannot submit empty portfolio (no alphas selected)")
        sys.exit(1)

    print("\n--- Next Steps ---")
    if n_review > 0:
        print(f"1. Review {n_review} alphas that need human attention")
    if not args.submit:
        print("2. Upload portfolio_state.json to S3")
        if not args.generate_code and n_selected > 0:
            print("3. Run with --generate-code to generate portfolio.py")
        elif args.generate_code and n_selected > 0:
            print("3. Run with --submit to submit portfolio to Finter")
    else:
        print("2. Monitor submission status in Finter")


def main_submit_only():
    """Simplified entry point for submit-only mode (no evaluations needed)."""
    parser = argparse.ArgumentParser(description="Submit portfolio to Finter")
    parser.add_argument("--portfolio", required=True, help="Path to portfolio.py")
    parser.add_argument("--state", default="portfolio_state.json", help="Path to portfolio_state.json")
    parser.add_argument("--market", required=True,
                        choices=["kr_stock", "us_stock", "vn_stock", "id_stock", "us_etf"],
                        help="Market type")
    parser.add_argument("--email", help="User email (for model_id prefix)")
    parser.add_argument("--api-key", help="Finter API key")
    parser.add_argument("--name", help="Portfolio name (uses portfolio_state.json if not set)")
    args = parser.parse_args()

    # Load portfolio code
    portfolio_code = load_portfolio_code(args.portfolio)
    if not portfolio_code:
        print(f"Error: Cannot load {args.portfolio}")
        sys.exit(1)

    # Load portfolio state for name
    state = load_portfolio_state_from_file(args.state) or {}
    portfolio_name = args.name or state.get("portfolio_name", "Portfolio")

    print("=" * 60)
    print("PORTFOLIO SUBMISSION")
    print("=" * 60)

    # Submit
    result = submit_portfolio_to_finter(
        portfolio_code=portfolio_code,
        portfolio_name=portfolio_name,
        market=args.market,
        email=args.email,
        api_key=args.api_key,
    )

    if result.get("success"):
        # Update state file
        update_portfolio_state_after_submit(
            state_path=args.state,
            model_id=result.get("model_id", ""),
            version=result.get("version", 1),
            status="success",
        )
        print("\n✓ Portfolio submitted successfully!")
    else:
        print(f"\n✗ Submission failed: {result.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
