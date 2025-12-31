# PM Evaluation Guide

Detailed guidance for evaluating alphas across the four perspectives.

## 1. Rationale Alignment (가설-포지션 일치)

**Question**: "가설이 말하는 것과 실제 포지션이 일치하는가?"

### How to Assess

1. Read the ResearchSummary to understand the hypothesis
2. Review the alpha code to see actual position logic
3. Compare: Does the position actually implement the hypothesis?

### Examples

**Aligned**:
- Hypothesis: "High momentum stocks outperform"
- Position: Long stocks with highest 12-month returns
- Assessment: aligned - Position matches hypothesis

**Partial**:
- Hypothesis: "Momentum with quality filter"
- Position: Pure momentum, no quality filter
- Assessment: partial - Momentum implemented, quality missing

**Misaligned**:
- Hypothesis: "Value stocks with low P/E"
- Position: Long high-momentum stocks
- Assessment: misaligned - Position contradicts hypothesis

### Red Flags
- Strategy description doesn't match code
- "Momentum" strategy that holds value stocks
- Complex code that obscures the actual signal

---

## 2. Economic Sense (투자 논리)

**Question**: "이 투자 논리가 경제적으로 타당한가?"

### How to Assess

1. Can you explain WHY this strategy makes money?
2. WHO is the counterparty losing money?
3. Is this a known, persistent market inefficiency?

### Ratings

**Strong**:
- Well-documented academic factor (momentum, value, quality)
- Clear behavioral or structural explanation
- Long history of working across markets

**Moderate**:
- Reasonable hypothesis with some evidence
- May work in specific conditions
- Economic logic is plausible but not proven

**Weak**:
- Thin economic rationale
- Relies on data patterns without theory
- "It just works" reasoning

**Questionable**:
- No logical explanation
- Likely curve-fitting
- Too good to be true

### Examples

**Strong**: "12-month momentum - behavioral underreaction to news, documented in Jegadeesh & Titman 1993"

**Moderate**: "52-week high momentum - anchoring bias, some academic support"

**Weak**: "RSI threshold strategy - no clear economic reason why RSI=30 matters"

**Questionable**: "Complex multi-indicator combination - pattern mining without theory"

---

## 3. Portfolio Fit (포트폴리오 적합성)

**Question**: "기존 선택한 알파들과 차별화된 가치가 있는가?"

### How to Assess

1. Calculate correlation with already-selected alphas
2. Determine what role this alpha plays
3. Assess marginal contribution to portfolio

### Roles

**Core**:
- Strong standalone performance
- Low correlation with others
- Significant weight justified
- Example: "Main momentum strategy"

**Diversifier**:
- Moderate performance
- Low correlation - adds diversification
- Complements core strategies
- Example: "Value strategy when core is momentum"

**Hedge**:
- May have lower standalone Sharpe
- Negative correlation with core
- Provides downside protection
- Example: "Quality factor during drawdowns"

**Redundant**:
- High correlation (>0.7) with existing selection
- Marginal value is low
- Should be excluded unless much better
- Example: "Second momentum strategy"

### Correlation Thresholds

| Correlation | Assessment |
|-------------|------------|
| < 0.3 | Excellent diversification |
| 0.3 - 0.5 | Good diversification |
| 0.5 - 0.7 | Moderate overlap |
| > 0.7 | Redundant - needs justification |

---

## 4. Red Flags (경고 신호)

**Question**: "의심스러운 패턴이 있는가?"

### Common Red Flags

| Flag | Symptom | Severity |
|------|---------|----------|
| **High Sharpe** | Sharpe > 3.0 | Critical - likely bug or overfit |
| **Excessive Turnover** | > 30x annual | Critical - costs kill edge |
| **Perfect Backtest** | No drawdowns | Critical - likely bug |
| **Small Sample** | < 5 years data | Moderate - may not persist |
| **Concentrated** | < 10 holdings | Moderate - capacity issue |
| **Regime Dependent** | Only works in bull/bear | Moderate - conditional |
| **Data Snooping** | Complex parameter combinations | High - overfit |

### Sharpe Interpretation

| Sharpe | Interpretation |
|--------|----------------|
| < 0.5 | Below threshold |
| 0.5 - 1.0 | Acceptable |
| 1.0 - 2.0 | Good |
| 2.0 - 3.0 | Very good - verify |
| > 3.0 | Suspicious - check for bugs |

### Turnover Reality

Finter applies realistic costs. High turnover strategies rarely survive:

- Turnover 1-5x: Low frequency, costs manageable
- Turnover 5-15x: Monthly rebalance typical
- Turnover 15-30x: High, but can work with strong edge
- Turnover > 30x: Very high, needs exceptional edge

---

## Decision Framework

### When to SELECT

- [x] Rationale aligned
- [x] Economic sense strong or moderate
- [x] Portfolio contribution clear (core, diversifier, or hedge)
- [x] No critical red flags
- [x] Adds value vs existing selection

### When to EXCLUDE

- [ ] Rationale misaligned, OR
- [ ] Economic sense questionable, OR
- [ ] Redundant (correlation > 0.7 with existing), OR
- [ ] Critical red flags (Sharpe > 3, obvious bugs)

### When to REVIEW

- Mixed signals across criteria
- Edge cases requiring domain expertise
- New strategy types with limited precedent
- Borderline metrics that could go either way
