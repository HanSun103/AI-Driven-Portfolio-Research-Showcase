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

## Architecture

```mermaid
flowchart TD
    CONTRACT["Experiment contract<br/>universe, dates, horizon, model,<br/>costs, controls and promotion gates"]

    subgraph TEXT["Text and news ingestion"]
        LIVE_NEWS["Incremental financial news<br/>RSS, NewsAPI and Alpha Vantage"]
        HISTORY_NEWS["Historical news archives<br/>selective and resumable imports"]
        RAW_NEWS["Deduplicated raw-news store<br/>source, ticker and publication time"]
        NLP["FinBERT pipeline<br/>entity linking, sentiment and events"]
        CLOCK["Decision-time news clock<br/>close cutoff or next-session availability"]

        LIVE_NEWS --> RAW_NEWS
        HISTORY_NEWS --> RAW_NEWS
        RAW_NEWS --> NLP --> CLOCK
    end

    subgraph MARKET["Market, macro and universe ingestion"]
        PRICES["Adjusted OHLCV<br/>Yahoo with provider fallbacks"]
        MACRO["SPY, VIX, rates and regime inputs"]
        MEMBERS["Point-in-time membership and sectors<br/>lagged liquid top 250"]
        CACHE["Incremental market cache<br/>fetch only missing history"]
        PRICE_AUDIT["Corporate-action and price-gap audit<br/>suspicious histories are replaced or rejected"]

        PRICES --> CACHE --> PRICE_AUDIT
        MACRO --> CACHE
        MEMBERS --> PRICE_AUDIT
    end

    subgraph FEATURES["Leakage-safe research panel"]
        QUANT["Technical, cross-sectional,<br/>sector-relative and macro features"]
        SENTIMENT["Lagged sentiment, event<br/>and recency features"]
        LABELS["Exact next-open labels<br/>20-session return and 40-session rank"]
        STORE["Ticker-date feature store<br/>availability and quality metadata"]

        PRICE_AUDIT --> QUANT --> STORE
        CLOCK --> SENTIMENT --> STORE
        PRICE_AUDIT --> LABELS --> STORE
    end

    subgraph MODELS["Opportunity, risk and portfolio policy"]
        TEMPORAL["Purged expanding folds<br/>fold-local preprocessing and selection"]
        RIDGE20["20-session Ridge<br/>continuous-return head"]
        RIDGE40["40-session Ridge<br/>cross-sectional rank head"]
        RISK["Downside quantile, severe-loss<br/>and uncertainty diagnostics"]
        CONTROLLER["Constrained controller<br/>fixed policy remains the benchmark"]
        SLEEVES["One-stock weekly sleeves<br/>equal capital across active vintages"]

        STORE --> TEMPORAL
        TEMPORAL --> RIDGE20 --> RISK
        TEMPORAL --> RIDGE40 --> RISK
        RISK --> CONTROLLER --> SLEEVES
    end

    subgraph EVALUATION["Execution, evaluation and controls"]
        REPLAY["Exact daily replay<br/>next-open entry and scheduled exit"]
        COSTS["Gross and net accounting<br/>fees, spread, slippage and turnover"]
        CONTROLS["SPY, eligible universe,<br/>next-rank and sector-matched controls"]
        STRESS["Ticker removal, year, regime,<br/>drawdown, CVaR and cost stress tests"]
        LIVE_MONITOR["Immutable live-forward monitor<br/>signals, prices and matured outcomes"]
        PILOT["Approximately $4,000 pilot<br/>actual fills and operational reconciliation"]
        SCALE["Gradual scaling gate<br/>behaviour first, profit second"]
        OUTPUT["Reports, experiment logs<br/>and sanitized research evidence"]

        SLEEVES --> REPLAY --> COSTS --> STRESS --> OUTPUT
        CONTROLS --> STRESS
        SLEEVES --> LIVE_MONITOR --> OUTPUT
        LIVE_MONITOR --> PILOT --> SCALE
        PILOT --> OUTPUT
    end

    CONTRACT --> STORE
    CONTRACT --> TEMPORAL
    CONTRACT --> REPLAY
    CONTRACT --> LIVE_MONITOR
```

| Module | Responsibility |
|---|---|
| Market and news ingestion | Refresh adjusted prices and timestamped news; retain effective-dated membership, sector and source metadata |
| Data integrity | Audit freshness, corporate actions, missing histories, decision-time availability and survivorship controls |
| Leakage-safe research panel | Build the lagged liquid universe, features and exact next-open horizon labels |
| Model development | Run purged temporal folds, fold-local preprocessing and feature selection, training-only early stopping and Optuna TPE |
| Portfolio construction | Convert frozen scores into holdings while tracking exposure, liquidity, turnover, downside and uncertainty |
| Execution replay | Apply exact entry timing, overlapping sleeves, costs, cash and schedule-matched SPY |
| Monitoring and evidence | Preserve immutable forecasts, mature outcomes without look-ahead and publish sanitized diagnostics |

The implementation, production configuration, trained models, data, current
selections and live execution records are intentionally private.

## Evidence gallery

| Interim finalist replay | Dominant-ticker stress test |
|---|---|
| ![20-session, 40-session and SPY declared-cost backtest summary](assets/horizon_finalist_backtest.svg) | ![Top-one concentration stress test](assets/concentration_stress.svg) |

The finalist replay reports the strongest candidate's 31.23% declared-cost
net CAGR alongside the 40-session candidate and SPY. It remains interim
development evidence and will be complemented by live-forward results as the
new portfolios mature.

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
