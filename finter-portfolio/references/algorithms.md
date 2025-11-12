# Portfolio Weight Calculation Algorithms

Guide to different methods for calculating portfolio weights when combining alpha strategies.

## Algorithm Selection Guide

| Algorithm | Complexity | Use Case | Pros | Cons |
|-----------|-----------|----------|------|------|
| Equal Weight | Simple | Baseline, high correlation | Simple, robust | Ignores risk/performance |
| Risk Parity | Medium | Balanced risk | Risk-balanced, stable | Ignores returns |
| Mean-Variance | Complex | Maximize risk-adjusted return | Theory-backed | Unstable, estimation error |
| Minimum Correlation | Medium | Maximize diversification | Diversification-focused | Ignores returns |
| Return-based | Simple | Momentum/trend | Performance-weighted | Look-ahead risk |

**Recommendation**: Start with **Equal Weight** or **Risk Parity**, then iterate.

---

## 1. Equal Weight (1/N)

### Description
Allocate equal weight to all alphas regardless of performance or risk.

### Formula
```
weight_i = 1 / N
```
where N = number of alphas

### Implementation
```python
def weight(self, start: int, end: int) -> pd.DataFrame:
    # Load alpha returns
    preload_start = calculate_previous_start_date(start, 365)
    alpha_return_df = self.alpha_pnl_df('us_stock', preload_start, end)

    # Equal weight: 1/N
    n_alphas = len(self.alpha_list)
    weights = pd.DataFrame(
        1.0 / n_alphas,
        index=alpha_return_df.index,
        columns=alpha_return_df.columns
    )

    # Static weights: no shift needed
    return weights.loc[str(start):str(end)]
```

### When to Use
- **Baseline**: Always start here to establish baseline performance
- **High correlation**: When alphas are highly correlated (>0.7)
- **Uncertainty**: When unsure about alpha quality
- **Robustness**: When avoiding estimation errors

### Pros
- Simplest to implement
- Most robust (no estimation error)
- Often outperforms complex methods (1/N paradox)
- No look-ahead bias

### Cons
- Ignores risk differences
- Ignores performance differences
- May overweight risky alphas

---

## 2. Risk Parity (Inverse Volatility)

### Description
Weight alphas inversely proportional to their volatility, so each alpha contributes equal risk.

### Formula
```
weight_i = (1 / volatility_i) / Σ(1 / volatility_j)
```

### Implementation
```python
def weight(self, start: int, end: int) -> pd.DataFrame:
    # Load alpha returns with buffer (need 126+ days for rolling)
    preload_start = calculate_previous_start_date(start, 365)
    alpha_return_df = self.alpha_pnl_df('us_stock', preload_start, end)

    # Clean consecutive 1's
    find_1 = (alpha_return_df == 1) & (alpha_return_df.shift(1) == 1)
    alpha_return_df = alpha_return_df.mask(find_1, np.nan).ffill(limit=5)

    # Calculate rolling volatility (6-month = 126 trading days)
    lookback_days = 126
    volatility_df = alpha_return_df.rolling(
        window=lookback_days,
        min_periods=lookback_days
    ).std()

    # Calculate risk parity weights using inverse volatility
    adjusted_volatility = volatility_df.replace(0, np.nan)  # Avoid division by zero
    inv_volatility = 1 / adjusted_volatility

    # Normalize weights to sum to 1
    weights = inv_volatility.div(inv_volatility.sum(axis=1), axis=0)
    weights = weights.fillna(0)  # Handle NaN

    # Apply shift for safety
    return weights.shift(1).loc[str(start):str(end)]
```

### When to Use
- **Different risk profiles**: Alphas have significantly different volatilities
- **Risk management focus**: Want to balance risk contribution
- **Stable performance**: Need more stable weight allocation

### Pros
- Balances risk contribution across alphas
- More stable than return-based methods
- Simple to implement and understand
- Well-researched approach

### Cons
- Ignores expected returns
- May underweight high-return alphas
- Requires sufficient history for volatility estimation
- Volatility estimates can be noisy

### Parameters to Tune
- **Lookback window**: 60 (3mo), 126 (6mo), 252 (1yr)
  - Shorter: More responsive, noisier
  - Longer: More stable, slower to adapt
- **min_periods**: Usually same as window

---

## 3. Mean-Variance Optimization (MVO)

### Description
Maximize Sharpe ratio (or minimize variance) using Markowitz portfolio theory.

### Formula
Maximize: `(μ'w - r_f) / √(w'Σw)`
Subject to: `Σw_i = 1, w_i ≥ 0`

where:
- μ = expected returns
- Σ = covariance matrix
- w = weights
- r_f = risk-free rate (usually 0 for alpha portfolios)

### Implementation
```python
import numpy as np
from scipy.optimize import minimize

def weight(self, start: int, end: int) -> pd.DataFrame:
    # Load alpha returns with buffer
    preload_start = calculate_previous_start_date(start, 365)
    alpha_return_df = self.alpha_pnl_df('us_stock', preload_start, end)

    # Clean consecutive 1's
    find_1 = (alpha_return_df == 1) & (alpha_return_df.shift(1) == 1)
    alpha_return_df = alpha_return_df.mask(find_1, np.nan).ffill(limit=5)

    # Calculate rolling statistics
    lookback = 252  # 1 year
    weights_list = []

    for i in range(lookback, len(alpha_return_df)):
        window = alpha_return_df.iloc[i-lookback:i]

        # Calculate mean returns and covariance
        returns = window - 1.0  # Convert from 1.0 baseline to 0.0 baseline
        mu = returns.mean().values
        cov = returns.cov().values

        # Optimization
        n = len(mu)
        init_weights = np.ones(n) / n

        # Objective: negative Sharpe ratio
        def neg_sharpe(w):
            port_return = np.dot(w, mu)
            port_vol = np.sqrt(np.dot(w, np.dot(cov, w)))
            return -port_return / (port_vol + 1e-6)  # Add epsilon to avoid division by zero

        # Constraints: sum to 1
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        bounds = tuple((0, 1) for _ in range(n))

        result = minimize(
            neg_sharpe,
            init_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )

        if result.success:
            weights_list.append(result.x)
        else:
            # Fallback to equal weight on failure
            weights_list.append(np.ones(n) / n)

    # Create weights DataFrame
    weights_df = pd.DataFrame(
        weights_list,
        index=alpha_return_df.index[lookback:],
        columns=alpha_return_df.columns
    )

    # Already lagged by construction (using past data), but shift for safety
    return weights_df.shift(1).loc[str(start):str(end)]
```

### When to Use
- **Low correlation**: Alphas have low correlation (<0.3)
- **Theory-driven**: Want theory-backed optimal allocation
- **Performance focus**: Maximize risk-adjusted returns

### Pros
- Theory-backed (Nobel Prize)
- Optimal under assumptions
- Accounts for both risk and return
- Considers correlations

### Cons
- **Very unstable**: Small input changes → large weight changes
- **Estimation error**: Garbage in, garbage out
- **Computational cost**: Slower than simple methods
- **Corner solutions**: Often extreme weights (0 or 100%)

### Tips to Stabilize
1. **Regularization**: Add penalty for extreme weights
2. **Weight constraints**: Limit max/min weights (e.g., 0.1 to 0.5)
3. **Longer lookback**: Use 2-3 years of data
4. **Shrinkage**: Shrink covariance towards diagonal
5. **Rebalancing cost**: Add turnover penalty

---

## 4. Minimum Correlation (Maximum Diversification)

### Description
Weight alphas to minimize average pairwise correlation, maximizing diversification benefit.

### Implementation
```python
def weight(self, start: int, end: int) -> pd.DataFrame:
    # Load alpha returns with buffer
    preload_start = calculate_previous_start_date(start, 365)
    alpha_return_df = self.alpha_pnl_df('us_stock', preload_start, end)

    # Clean consecutive 1's
    find_1 = (alpha_return_df == 1) & (alpha_return_df.shift(1) == 1)
    alpha_return_df = alpha_return_df.mask(find_1, np.nan).ffill(limit=5)

    # Calculate rolling correlation
    lookback = 126
    corr_df = alpha_return_df.rolling(lookback).corr()

    # Calculate diversification score (inverse of avg correlation)
    weights_list = []
    for date in alpha_return_df.index[lookback:]:
        # Get correlation matrix for this date
        corr_matrix = corr_df.loc[date]

        # Calculate average correlation for each alpha
        avg_corr = corr_matrix.mean(axis=1)

        # Inverse correlation → higher weight for low correlation alphas
        div_score = 1 / (avg_corr + 0.1)  # Add 0.1 to avoid division by zero

        # Normalize to sum to 1
        w = div_score / div_score.sum()
        weights_list.append(w.values)

    weights_df = pd.DataFrame(
        weights_list,
        index=alpha_return_df.index[lookback:],
        columns=alpha_return_df.columns
    )

    return weights_df.shift(1).loc[str(start):str(end)]
```

### When to Use
- **Diversification focus**: Want maximum diversification benefit
- **Correlation regime**: Correlations vary over time
- **Risk-averse**: Prefer stability over performance

### Pros
- Maximizes diversification
- Reduces portfolio concentration
- Intuitive approach

### Cons
- Ignores returns completely
- May underweight high-performing alphas
- Correlation estimates can be noisy

---

## 5. Return-based (Momentum/Performance)

### Description
Weight alphas based on recent performance (momentum approach).

### Implementation
```python
def weight(self, start: int, end: int) -> pd.DataFrame:
    # Load alpha returns with buffer
    preload_start = calculate_previous_start_date(start, 365)
    alpha_return_df = self.alpha_pnl_df('us_stock', preload_start, end)

    # Clean consecutive 1's
    find_1 = (alpha_return_df == 1) & (alpha_return_df.shift(1) == 1)
    alpha_return_df = alpha_return_df.mask(find_1, np.nan).ffill(limit=5)

    # Calculate rolling returns (60-day momentum)
    lookback = 60
    returns = alpha_return_df - 1.0  # Convert to 0-baseline
    rolling_return = returns.rolling(lookback).mean()

    # Only positive returns get weight (momentum effect)
    positive_returns = rolling_return.clip(lower=0)

    # Normalize weights to sum to 1
    weights = positive_returns.div(positive_returns.sum(axis=1), axis=0)
    weights = weights.fillna(1.0 / len(self.alpha_list))  # Equal weight if all negative

    # CRITICAL: MUST shift for return-based weights
    return weights.shift(1).loc[str(start):str(end)]
```

### When to Use
- **Momentum belief**: Believe performance persists
- **Performance-driven**: Want to overweight winners
- **Dynamic allocation**: Need adaptive weights

### Pros
- Rewards recent performance
- Simple and intuitive
- Automatically reduces exposure to poor performers

### Cons
- **High look-ahead risk**: MUST shift(1)!
- Can be unstable (chasing performance)
- May buy high, sell low
- Ignores risk

---

## 6. Hybrid Approaches

### Risk-Adjusted Return
Combine risk parity with return weighting:

```python
# Calculate both
volatility_df = alpha_return_df.rolling(126).std()
rolling_return = alpha_return_df.rolling(60).mean() - 1.0

# Sharpe-like score
sharpe_score = rolling_return / (volatility_df + 1e-6)

# Positive scores only
positive_sharpe = sharpe_score.clip(lower=0)

# Normalize
weights = positive_sharpe.div(positive_sharpe.sum(axis=1), axis=0)
weights = weights.fillna(1.0 / len(self.alpha_list))

return weights.shift(1).loc[str(start):str(end)]
```

### Constrained Optimization
Add constraints to MVO:

```python
# Max weight: 40%
bounds = tuple((0, 0.4) for _ in range(n))

# Min weight: 10% (no zeros)
bounds = tuple((0.1, 0.5) for _ in range(n))

# Additional constraint: L2 penalty for extreme weights
def objective_with_penalty(w):
    sharpe = -neg_sharpe(w)
    penalty = 0.1 * np.sum((w - 1/n)**2)  # Penalty for deviating from equal weight
    return -(sharpe - penalty)
```

---

## Practical Recommendations

### Start Simple → Iterate

1. **Baseline**: Equal weight (1/N)
2. **Risk-balanced**: Risk parity
3. **If needed**: Hybrid or optimization

### Key Considerations

**Rebalancing Frequency**:
- Daily: Very responsive, high turnover
- Weekly: Balanced
- Monthly: Stable, low turnover
- **Recommendation**: Match to alpha rebalancing frequency

**Lookback Period**:
- Short (20-60 days): Responsive, noisy
- Medium (60-126 days): Balanced
- Long (252+ days): Stable, slow
- **Recommendation**: 126 days (6 months) for most cases

**Stability vs Performance**:
- High stability → Equal weight, risk parity
- High performance → Optimization, return-based
- **Recommendation**: Start stable, add complexity if justified by out-of-sample tests

### Backtest Before Deploying

Always backtest multiple algorithms and compare:
- Total return
- Sharpe ratio
- Max drawdown
- Turnover (transaction costs!)
- Stability (weight changes)

---

## Next Steps

- **See examples**: Check `templates/examples/` for complete implementations
- **Data preprocessing**: Read `preprocessing.md` for data cleaning
- **Troubleshooting**: Read `troubleshooting.md` for common issues
