# Research Standard

Every promoted result must use the same evidence contract.

## Information available at the decision time

- membership, sector and liquidity are effective-dated;
- features and news respect their publication timestamps;
- labels begin at the declared execution price;
- corporate actions and suspicious price gaps are audited; and
- missing or stale critical inputs stop the run.

## Temporal model evaluation

- expanding walk-forward folds replace random train-test shuffling;
- label horizons are purged from fold boundaries;
- imputation, transformation and feature selection remain inside training;
- early stopping uses a training-only chronological split;
- candidate models use common observations and tuning budgets; and
- design periods are never relabelled as untouched confirmation periods.

## Portfolio evaluation

- daily portfolio returns are reconstructed from exact overlapping sleeves;
- gross and declared-cost results are reported separately;
- SPY remains visible on the identical execution schedule;
- turnover, drawdown, CVaR and worst-day loss accompany return metrics;
- matched random, eligible-universe and neighbouring-rank controls challenge
  the model's selection contribution; and
- year, regime, sector and ticker attribution identify concentration.

## Promotion principle

The system advances only when the observed mechanism is credible. A profitable
result fails when it depends on look-ahead, inconsistent execution, one
unrepeatable contributor, unexplained accounting or risk outside the declared
contract.
