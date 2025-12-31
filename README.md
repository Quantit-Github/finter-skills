# Finter Skills for Claude Code

Claude Code에서 Finter 데이터/알파/포트폴리오 작업을 바로 할 수 있게 해주는 스킬 모음.

## Installation

### 1. Clone this repo

```bash
git clone https://github.com/quantit/finter-skills.git
```

### 2. Install finter package

```bash
pip install finter
# or
uv add finter
```

### 3. Setup skills in your project

```bash
cd your-project
/path/to/finter-skills/install.sh
```

This creates:
```
your-project/
├── .claude/
│   └── skills/
│       ├── finter-data/
│       ├── finter-alpha/
│       ├── finter-portfolio/
│       └── ...
└── CLAUDE.md
```

### 4. Run Claude Code

```bash
claude
```

## Usage Examples

```
> finter에 한국주식 PER 데이터 있어?

> us_stock에서 momentum alpha 만들어줘

> crypto 데이터 어떻게 로드해?

> kr_stock universe로 value factor 백테스트 해줘
```

## What's Included

| Skill | Description |
|-------|-------------|
| finter-data | Data loading, Symbol search, preprocessing |
| finter-alpha | BaseAlpha strategy implementation |
| finter-portfolio | Portfolio optimization |
| finter-insight | Research database search (RAG) |
| finter-operations | Error recovery workflows |

## Universes

| Universe | Assets | Best For |
|----------|--------|----------|
| kr_stock | ~2,500 | Korean stocks (richest data) |
| us_stock | ~8,000 | US stocks |
| us_etf | ~6,700 | US ETFs (market data only) |
| vn_stock | ~1,000 | Vietnam stocks |
| id_stock | ~1,000 | Indonesia stocks |
| crypto_test | ~378 | Crypto (2024 only, 10min candles) |

## Requirements

- Python 3.10+
- `finter` package
- Claude Code CLI
