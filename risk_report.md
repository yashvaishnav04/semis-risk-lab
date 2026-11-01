# Semiconductor Portfolio Risk Report

Data period: 2016-01-05 to 2026-10-20 (daily returns). Last factor date: 2026-08-31.

## Portfolio weights

| Ticker | Weight |
|---|---|
| SNPS | 15.0% |
| CDNS | 15.0% |
| ASML | 12.0% |
| NVDA | 12.0% |
| TSM | 12.0% |
| AVGO | 10.0% |
| AMD | 8.0% |
| QCOM | 6.0% |
| MU | 5.0% |
| INTC | 5.0% |

## Summary

| Ticker | Volatility | Beta vs SOXX | Sharpe | Max drawdown | VaR 95% | ES 95% |
|---|---|---|---|---|---|---|
| NVDA | 49.1% | 1.09 | 1.26 | -66.3% | -4.5% | -6.6% |
| AMD | 60.1% | 1.20 | 1.07 | -65.4% | -5.4% | -7.7% |
| AVGO | 39.4% | 0.89 | 0.95 | -48.3% | -3.6% | -5.4% |
| QCOM | 39.3% | 0.85 | 0.50 | -44.3% | -3.5% | -5.7% |
| TSM | 34.2% | 0.78 | 0.98 | -56.5% | -3.2% | -4.6% |
| INTC | 44.8% | 0.89 | 0.43 | -70.8% | -3.9% | -6.3% |
| MU | 51.9% | 1.19 | 0.96 | -57.6% | -4.8% | -7.0% |
| ASML | 38.6% | 0.94 | 0.86 | -56.9% | -3.9% | -5.5% |
| SNPS | 35.1% | 0.66 | 0.72 | -43.0% | -3.3% | -5.0% |
| CDNS | 33.9% | 0.67 | 0.85 | -34.2% | -3.2% | -4.9% |
| SOXX | 34.2% | 1.00 | 0.90 | -45.8% | -3.5% | -5.0% |
| SPY | 17.7% | 0.41 | 0.76 | -33.7% | -1.7% | -2.7% |
| PORTFOLIO | 31.7% | 0.88 | 1.17 | -43.4% | -3.2% | -4.5% |

## Portfolio vs SOXX

- Tracking error: 11.2%
- Information ratio: 0.57

## Correlation matrix

|  | NVDA | AMD | AVGO | QCOM | TSM | INTC | MU | ASML | SNPS | CDNS |
|---|---|---|---|---|---|---|---|---|---|---|
| NVDA | 1.00 | 0.59 | 0.59 | 0.51 | 0.62 | 0.42 | 0.55 | 0.62 | 0.57 | 0.60 |
| AMD | 0.59 | 1.00 | 0.47 | 0.48 | 0.52 | 0.41 | 0.51 | 0.53 | 0.44 | 0.47 |
| AVGO | 0.59 | 0.47 | 1.00 | 0.55 | 0.63 | 0.45 | 0.58 | 0.64 | 0.49 | 0.56 |
| QCOM | 0.51 | 0.48 | 0.55 | 1.00 | 0.53 | 0.49 | 0.52 | 0.59 | 0.49 | 0.52 |
| TSM | 0.62 | 0.52 | 0.63 | 0.53 | 1.00 | 0.44 | 0.59 | 0.69 | 0.50 | 0.54 |
| INTC | 0.42 | 0.41 | 0.45 | 0.49 | 0.44 | 1.00 | 0.54 | 0.53 | 0.43 | 0.43 |
| MU | 0.55 | 0.51 | 0.58 | 0.52 | 0.59 | 0.54 | 1.00 | 0.62 | 0.44 | 0.47 |
| ASML | 0.62 | 0.53 | 0.64 | 0.59 | 0.69 | 0.53 | 0.62 | 1.00 | 0.56 | 0.60 |
| SNPS | 0.57 | 0.44 | 0.49 | 0.49 | 0.50 | 0.43 | 0.44 | 0.56 | 1.00 | 0.81 |
| CDNS | 0.60 | 0.47 | 0.56 | 0.52 | 0.54 | 0.43 | 0.47 | 0.60 | 0.81 | 1.00 |

## Method notes

- Returns are simple daily returns computed from adjusted closes.
- Volatility and the Sharpe ratio are annualised with 252 trading days.
- Beta is measured against SOXX, the sector benchmark.
- The Sharpe ratio uses the Fama French daily rf; after the last factor date the last known rf is carried forward.
- VaR and expected shortfall are one-day 95% historical figures.
- The portfolio uses fixed weights, rebalanced daily.
- The weights were chosen in 2026, so the backtest contains hindsight.
