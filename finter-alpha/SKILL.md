---
name: finter-alpha
description: Quantitative trading alpha strategy development using the Finter Python library. Use when user requests to create, modify, or analyze alpha strategies (e.g., "create RSI strategy", "momentum alpha", "create momentum strategy", "combine value and momentum factors"). Supports the BaseAlpha framework with automated backtesting and result analysis.
---

# Finter Alpha Strategy Development

Develop quantitative trading alpha strategies using the Finter framework. This skill provides the complete workflow from strategy ideation to backtesting.

## Workflow

1. **Understand Requirements**: Clarify the strategy concept (momentum, mean reversion, multi-factor, etc.)
2. **Select Framework**: Use BaseAlpha framework for strategy development
3. **Implement Strategy**: Use templates from `assets/` and reference `references/` for API usage
4. **Backtest**: Run `scripts/backtest_runner.py` to evaluate performance
5. **Iterate**: Refine based on results and research guidelines

## Framework

### BaseAlpha
- **Use for**: Strategy development, prototypes, and production strategies
- **Template**: `assets/base_alpha_template.py`
- **Reference**: `references/base_alpha_guide.md`

## Quick Start

### Example Request: "RSI 전략 만들어줘"

1. **Load template**: Start with `assets/base_alpha_template.py`
2. **Implement logic**: Follow patterns in `references/alpha_examples.md`
3. **Run backtest**: Execute `scripts/backtest_runner.py --code alpha.py`
4. **Review results**: Analyze Sharpe ratio, drawdown, returns

## Best Practices

Before coding, review:
- `references/research_guidelines.md` - Research methodology and checklist
- `references/best_practices.md` - Common pitfalls and optimization tips
- `references/finter_api_reference.md` - Data access and API methods

## Key Rules

1. **Class name must be `Alpha`** (not CustomStrategy, MyAlpha, etc.)
2. **Always shift positions** to avoid look-ahead bias: `return positions.shift(1)`
3. **Position constraints**: Row sums ≤ 1e8 (total AUM)
4. **No future data**: Use only historical information in calculations

## Running Backtests

```bash
# Basic backtest
python scripts/backtest_runner.py --code alpha.py

# With custom date range
python scripts/backtest_runner.py --code alpha.py --start 20200101 --end 20241231

# Specific universe
python scripts/backtest_runner.py --code alpha.py --universe us_stock
```

## References

- `references/base_alpha_guide.md` - BaseAlpha framework documentation
- `references/alpha_examples.md` - Complete strategy implementations
- `references/finter_api_reference.md` - Data access and ContentFactory methods
- `references/research_guidelines.md` - Research process and validation
- `references/best_practices.md` - Performance tips and common mistakes
