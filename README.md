# AI-Driven Stock Selection Research Showcase

> Can a machine-learning model identify future stock-market winners without
> relying on one lucky ticker, one favourable period, or a backtest assumption
> that disappears in live operation?

![Research status](https://img.shields.io/badge/status-live--forward_monitoring-d97706)
![Research period](https://img.shields.io/badge/development_period-2013--2023-3157d5)
![Validation](https://img.shields.io/badge/validation-309_tests-0f9f8d)

## The result that moved the project forward

The current research candidate opens one new stock sleeve each week and holds
each selection for an exact horizon. In the corrected ten-year development
replay, the strongest candidate produced a 34.84% gross CAGR. When its three
largest historical contributors were excluded before selection, the frozen
model chose the next eligible candidates and still produced a 23.03% gross
CAGR.

| Development CAGR | Ex-ante exclusion CAGR | Weekly OOS decisions | Automated checks |
|---:|---:|---:|---:|
| **34.84%** | **23.03%** | **520** | **309** |
| Strongest finalist | Dominant contributors unavailable | December 2013 to December 2023 | Data, model, execution and publishing |

![Full backtest summary](assets/horizon_finalist_backtest.svg)

The result is promising because the ranking signal survives a direct attack on
its strongest winners. It is not yet ready to scale: its drawdown and tail
losses remain larger than SPY. The project has therefore moved from historical
development to live-forward monitoring.

## How the project evolved

The first version combined return prediction, technical indicators, sentiment,
portfolio optimization and pair trading. Successively stricter experiments
changed the direction:

1. point-in-time, execution and corporate-action audits removed results that
   could not be reproduced safely;
2. selecting relative winners proved more useful than forecasting an exact
   return;
3. simple linear models remained difficult for complex rankers to beat on a
   common temporal evaluation;
4. average broad-portfolio signals did not adequately control drawdown and
   tail losses;
5. breadth analysis found the strongest information near the very top of the
   ranking; and
6. an ex-ante contributor-exclusion test showed that the model could move to
   its next candidate rather than depending entirely on a few historical
   winners.

## Full development comparison

Every portfolio below uses the same daily calendar, overlapping-sleeve
accounting and SPY reference.

| Metric | 20-session return model | 40-session rank model | SPY |
|---|---:|---:|---:|
| Gross cumulative return | 3,508.26% | 1,487.79% | 339.19% |
| Gross CAGR | 34.84% | 25.92% | 13.13% |
| Gross annualized volatility | 46.83% | 38.80% | 16.87% |
| Gross Sharpe | 0.864 | 0.784 | 0.816 |
| Gross maximum drawdown | -49.24% | -46.16% | -32.05% |
| Daily CVaR 95% | -5.76% | -5.14% | -2.64% |
| Worst day | -15.18% | -20.92% | -8.80% |
| Net cumulative return | 2,504.88% | 1,180.08% | 339.19% |
| Net CAGR | 31.23% | 23.68% | 13.13% |
| Net Sharpe | 0.806 | 0.737 | 0.816 |
| Net maximum drawdown | -49.74% | -46.43% | -32.05% |

Net results use a declared-cost sensitivity with $1 million starting capital,
8 basis points of one-way execution cost and $10 per order. Both candidates
compound faster than SPY in development, but SPY retains the strongest net
Sharpe and materially smaller drawdown.

## Does the signal survive without its best winners?

![Dominant contributor stress test](assets/concentration_stress.svg)

The exclusion test supports a ranking relationship, not a safety claim. After
the dominant contributors were made unavailable, gross CAGR remained 23.03%,
but Sharpe fell to 0.761 and maximum drawdown remained -49.87%.

## Trade and hold, not daily replacement

![Weekly overlapping sleeves](assets/overlapping_sleeves.svg)

The strategy makes one decision each week, enters at the declared execution
time, and holds that sleeve until its exact exit. A 20-session strategy builds
toward four concurrent weekly sleeves; a 40-session strategy builds toward
eight. Capital is divided across active sleeve slots, so each weekly selection
contributes without being counted as a separate fully invested portfolio.

## Research architecture

```mermaid
flowchart TD
    DATA["Point-in-time market, universe and news inputs"]
    AUDIT["Timestamp, coverage and corporate-action audits"]
    PANEL["Leakage-safe features and exact forward labels"]
    MODEL["Opportunity, downside and uncertainty estimates"]
    POLICY["Constrained stock selection and sleeve construction"]
    REPLAY["Exact execution replay with costs and SPY"]
    STRESS["Ticker, year, regime, turnover and tail-risk stress tests"]
    LIVE["Immutable live-forward monitoring"]
    PILOT["Small real-money execution pilot"]
    SCALE["Gradual scaling only after operational agreement"]

    DATA --> AUDIT --> PANEL --> MODEL --> POLICY
    POLICY --> REPLAY --> STRESS
    POLICY --> LIVE --> PILOT --> SCALE
```

The implementation, production configuration, trained models, data, current
selections and live execution records are intentionally private.

## Evidence gallery

| Portfolio and execution diagnostics | Signal diagnostics |
|---|---|
| ![Backtest and execution diagnostics](assets/backtest_diagnostics.svg) | ![Signal diagnostics](assets/signal_diagnostics.svg) |

| Horizon attribution | Tail-control experiment |
|---|---|
| ![Horizon attribution](assets/horizon_attribution.svg) | ![Tail-control diagnostics](assets/tail_control_diagnostics.svg) |

## From research to capital

| Stage | Purpose | Promotion requirement |
|---|---|---|
| Historical development | Find and challenge a repeatable signal | Temporal OOS controls, exact execution replay and stress tests |
| Live-forward monitoring | Observe frozen decisions for at least two months | Signals, assumed prices, turnover, risk and accounting agree with the backtest |
| Small pilot | Test the operational path with approximately $4,000 | Real fills, slippage, costs and interventions stay within frozen tolerances |
| Gradual scaling | Increase capital carefully | Operational agreement continues; profit alone cannot unlock scaling |

Read the [research standard](docs/RESEARCH_STANDARD.md) and
[live validation plan](docs/LIVE_VALIDATION_PLAN.md).

## What this public repository intentionally excludes

- source code and production configurations;
- feature lists, model parameters and policy thresholds;
- raw or processed datasets and licensed inputs;
- trained models, Optuna studies and prediction panels;
- current holdings, scores, weights and rebalance targets;
- brokerage records, credentials and operational logs; and
- stock-level live evidence before it is safe to disclose.

## Disclaimer

This repository presents educational research evidence. Backtests and
live-forward observations are not investment advice and do not guarantee future
performance.
