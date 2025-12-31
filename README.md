# Finter Skills for Claude Code

Skills for quant research with Finter platform in Claude Code.

## Quick Start

```bash
# 1. Clone this repo (once)
git clone git@github.com:Quantit-Github/finter-skills.git ~/finter-skills

# 2. Install in your project folder (uv + finter + skills all at once)
mkdir my-quant-project && cd my-quant-project
~/finter-skills/install.sh

# 3. Run Claude Code
claude
```

## What install.sh Does

```
my-quant-project/
├── .claude/
│   └── skills/
│       ├── finter-data/      # Data loading
│       ├── finter-alpha/     # Alpha strategies
│       ├── finter-portfolio/ # Portfolio optimization
│       └── ...
├── CLAUDE.md                 # Context for Claude
├── pyproject.toml            # uv project
└── .venv/                    # Python environment
```

## Usage Examples

```
> What data is available for Korean stocks?

> Create a momentum alpha for us_stock

> Backtest a BTC strategy with crypto_test universe

> Implement a value factor for kr_stock
```

## Universes

| Universe | Assets | Best For |
|----------|--------|----------|
| kr_stock | ~2,500 | Korean stocks (richest data) |
| us_stock | ~8,000 | US stocks |
| us_etf | ~6,700 | US ETFs |
| vn_stock | ~1,000 | Vietnam stocks |
| id_stock | ~1,000 | Indonesia stocks |
| crypto_test | ~378 | Crypto (2024 only, 10min candles) |

## Skills

| Skill | Description |
|-------|-------------|
| finter-data | Data loading, Symbol search, preprocessing |
| finter-alpha | BaseAlpha strategy, backtesting |
| finter-portfolio | Portfolio optimization |
| finter-insight | Research DB search (RAG) |
| finter-operations | Error recovery workflow |

## Requirements

- macOS / Linux
- Python 3.10+
- Claude Code CLI (`claude`)
