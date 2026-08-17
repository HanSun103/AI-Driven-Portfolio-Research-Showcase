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

| Portfolio and execution diagnostics | Signal diagnostics |
|---|---|
| ![Backtest and execution diagnostics](assets/backtest_diagnostics.svg) | ![Signal diagnostics](assets/signal_diagnostics.svg) |

| Horizon attribution | Tail-control experiment |
|---|---|
| ![Horizon attribution](assets/horizon_attribution.svg) | ![Tail-control diagnostics](assets/tail_control_diagnostics.svg) |

These figures use the frozen 20-session Ridge-return finalist that produced a
34.84% gross CAGR. Signal diagnostics use temporal out-of-sample predictions;
portfolio charts use exact daily overlapping-sleeve accounting.

## From research to capital

| Stage | Purpose | Promotion requirement |
|---|---|---|
| Historical development | Find and challenge a repeatable signal | Temporal OOS controls, exact execution replay and stress tests |
| Live-forward monitoring | Observe frozen decisions for at least two months | Signals, assumed prices, turnover, risk and accounting agree with the backtest |
| Small pilot | Test the operational path with approximately $4,000 | Real fills, slippage, costs and interventions stay within frozen tolerances |
| Gradual scaling | Increase capital carefully | Operational agreement continues; profit alone cannot unlock scaling |

Read the [research standard](docs/RESEARCH_STANDARD.md) and
[live validation plan](docs/LIVE_VALIDATION_PLAN.md).

### Five-stream prospective monitoring pipeline

The next monitoring phase separates weekday entry timing from model training. All
five streams share the same approved model artifact for each arm, while every
vintage keeps its own immutable decision, execution and benchmark record.

```mermaid
flowchart TD
    A["Daily local scheduler"] --> B["NYSE calendar and actual close-time check"]
    B --> C{"Eligible session for its weekday stream?"}
    C -- "No" --> D["Record holiday or nonsession skip"]
    C -- "Yes" --> E["Resolve stream and frozen monitoring registry"]

    E --> F["Refresh inputs once"]
    F --> G["Construct one current feature and eligible-universe snapshot"]

    G --> H["Global model coordinator"]
    H --> I["Load current approved h20 Ridge-return artifact"]
    H --> J["Load current approved h40 Ridge-rank artifact"]
    H --> K["Refit each arm once only when 130-session clock expires"]

    I --> L["Score scheduled stream"]
    J --> L
    L --> M["Stage both arm forecasts transactionally"]
    M --> N{"Both required arms valid?"}
    N -- "No" --> O["Preserve failure ledger; exclude incomplete decision bundle"]
    N -- "Yes" --> P["Freeze and register two immutable vintages"]

    Q["Imported Wednesday and Friday v3 artifacts"] --> R["Read-only registry references"]
    P --> S["Unified vintage index"]
    R --> S

    S --> T["Group by stream_id, family and horizon"]
    T --> U["Independent stream accounting and same-window SPY"]
    T --> V["Partial, in-progress and matured vintage outcomes"]
    U --> W["Private five-stream dashboard"]
    V --> W
    W --> X["Explicit public allowlist"]
    X --> Y["Lightweight public price marking and Pages deployment"]

    S --> Z["Two-month review"]
    Z --> AA["Week-clustered and block-bootstrap evidence"]
    Z --> AB["Weekday and duplicate-ticker sensitivity"]
    Z --> AC["Frozen historical percentile comparison"]
```

The holding-period clock is now explicit: `20 sessions` and `40 sessions` mean
completed NYSE open-to-open intervals, not calendar days or generic business
days. The decision session does not count; entry is the next actual NYSE open;
weekends and full-market holidays do not count; and a valid early-close session
does count. The stock and SPY always use the same entry and maturity opens.

A named weekday stream runs only when that civil weekday is an actual NYSE
session. If the exchange is closed, that week's vintage is recorded as skipped
and is never shifted, backfilled, or silently inserted on another weekday. An
early close may be scored only after the actual close plus the settlement
buffer. Missing required stock or SPY opens fail closed, and partial marks never
enter mature horizon statistics.

This also corrects a legacy expectation: generic business-day arithmetic placed
the August 12 and August 14 seed maturities one NYSE session too early across
Labor Day. Their immutable source files remain unchanged; the monitoring
registry records corrected h20 maturities of September 11 and September 15,
and h40 maturities of October 9 and October 13, 2026.

The first completed interval can validate pipeline operation, but not model
effectiveness. All five streams can be operationally checked after roughly one
eligible week; the first h20 outcome needs about four to five calendar weeks;
and the two-month review is still only preliminary for h20 and early-stage for
h40. The first formal gate requires 60 mature outcomes—about 16 calendar weeks
at five decisions per week after the maturity lag—with an effective sample size
smaller than the raw count because vintages overlap.

The current one-interval checkpoint therefore makes no profitability claim:
there are zero mature outcomes. It records APP h20 at +1.89% active versus SPY
and BAC h40 at -2.25% active versus SPY as diagnostics only. The legacy
Wednesday and Friday seeds also have different model hashes, so the
same-artifact comparison begins only after the shared model coordinator is
deployed prospectively.

### Fastest code-validation and pilot schedule

This schedule is for implementation reconciliation, not accelerated proof of
profitability. It assumes the provenance-enabled code and shared-model
coordinator are deployed before the relevant decision close and every
fail-closed check passes.

| Date | Checkpoint | Evidence allowed |
|---|---|---|
| August 17, 2026, after NYSE close plus buffer | Freeze the first provenance-enabled Monday h20/h40 bundle | Exact feature, eligibility, model, configuration and calendar hashes |
| August 18, 2026, market open | Reconcile the declared next-open entry and schedule-matched SPY prices | Entry-path and broker/data plumbing validation |
| August 19, 2026, market open | Reconcile the first completed open-to-open interval | Provenance portion of the implementation-parity gate may pass |
| Approximately one eligible week | Observe every weekday stream with one shared model artifact per arm | Five-stream operational gate may pass |
| September 11, 2026 | First corrected h20 seed maturity | One complete h20 lifecycle; not profitability proof |
| October 9, 2026 | First corrected h40 seed maturity | One complete h40 lifecycle; not profitability proof |

No old forecast is backfilled with evidence that was not frozen when it was
created. A tiny controlled execution canary may be considered only after the
provenance, shared-model, coordinated-stream, next-open, duplicate-order, capital
limit and kill-switch checks all pass. Broader pilot or scaling decisions remain
subject to the predeclared performance and risk gates.


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
