# Finter Skills for Claude Code

Skills for quant research with Finter platform in Claude Code.

## Quick Start

```bash
# Clone and install
git clone git@github.com:Quantit-Github/finter-skills.git
cd finter-skills
./install.sh

# Start working
cd workspace
claude
```

## What install.sh Does

```
finter-skills/
├── finter-data/          # Skills (source)
├── finter-alpha/
├── finter-portfolio/
├── ...
├── install.sh
├── CLAUDE.md
└── workspace/            # <- Your working directory
    ├── .claude/
    │   └── skills/       # Symlinks to ../finter-*
    ├── CLAUDE.md
    ├── pyproject.toml
    └── .venv/
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
