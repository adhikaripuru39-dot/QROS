# Research and validation protocol

`qros.research.runner.run_research` executes the ten predeclared hypothesis families against supplied versioned real bid OHLC using `qros.backtest`. It creates no observations or profit numbers. Fixtures in tests are isolated deterministic examples and are never displayed as market results.

Call with `bars`, a versioned source `dataset_hash`, canonical `output_dir`, explicit `BacktestConfig`, and provenance. Metadata such as actual broker commission, swap schedule, spread conversion, source timeframe, terminal symbol and account conversion should accompany each run. Bars require absolute-price spread, **not MT5 spread points**. Ask OHLC remains modeled bid plus per-bar spread; full historical tick execution is not implemented.

```python
from qros.research.runner import run_research
report = run_research(
    bars, dataset_hash=manifest.sha256, output_dir="research_results",
    config=broker_cost_config,
    provenance={"coverage_verified": False,
                "broker_specs_verified": False,
                "execution_costs_verified": False,
                "independent_trade_assumption_reviewed": False},
    finalize_oos=False,
)
```

The source manifest's hash field name depends on the ingestion interface; use its actual immutable content hash. Do not set verification flags merely to obtain a passing result. In particular MT5 candle spreads do not verify historical ask, broker financing or slippage. The default state preserves OOS and reports failures explicitly.

The chronological split is 60% development / 20% validation / 20% escrow. A one-bar embargo is inserted at each boundary. Positions do not cross partitions. A trailing historical warmup is available for features without warmup entries. No current candidate fits model weights or hyperparameters. The fixed-rule walk-forward section verifies stability on subsequent windows; the separate `walk_forward_optimize` API supports training-only candidate selection for future parameter studies.

Development and validation may be inspected. A chosen candidate and all hashes are frozen before final OOS. OOS evaluation requires passing validation count, both trend/range stress, doubled spread/slippage, positive fixed-rule walk-forward folds, complete trial Sharpe distribution, and provenance gates. **The final holdout is consumed before evaluation begins**, so crashes and failures cannot authorize retries. The SQLite ledger keys actual holdout bar content independently of strategy/config. Keep one canonical ledger for the research program. Local filesystem audit discipline cannot stop an administrator from copying data or deleting the ledger.

Each report includes actual bar, source dataset, source code, config, protocol and provenance hashes. `report_hash` hashes the JSON object before adding `report_hash`. The `report_path` returned by the function is convenience metadata, outside the stored report. Reports are created exclusively and never overwritten. Hashes establish identity, not the truth of an externally asserted provenance flag.

Wilson win-rate intervals, a one-sided IID Student expectancy test, Welch comparison, PSR, DSR and a circular moving-block bootstrap report uncertainty. PSR/DSR follow Bailey and Lopez de Prado's unannualized definitions and account for nonnormal moments. DSR requires the entire comparable trial Sharpe distribution; undefined trial statistics prevent eligibility. PSR/DSR need independent comparable return horizons, which trade PnL generally cannot guarantee; provenance requires a deliberate independence review. More rigorous equal-horizon risk-adjusted return construction remains necessary where holding periods or exposures differ. Source: https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf

Monte Carlo reshuffles PnL to estimate additive sequence drawdown and budget-exhaustion risk. **Permutation preserves expectancy and does not establish an edge or produce a valid expectancy confidence interval.** Expectancy uncertainty instead uses the separate block bootstrap, with explicit stationarity assumptions. Simulations do not reveal unobserved tails.

Profile A requires at least 100 trades, 60–80% observed win rate, positive expectancy and hard stops. Profile B requires at least 100 trades and positive expectancy. Profile C requires at least 200 and additionally blocks eligibility unless portfolio independence and daily risk caps have been verified. These profiles are conservative filters, not guarantees of profitability. Pareto analysis maximizes expectancy, win rate and frequency while minimizing drawdown; it does not automatically promote strategies.

The H4-confirmation hypothesis produces no signals without genuine completed H4 context, and the liquidity proxy produces no signals without genuine tick volumes. Tick activity is explicitly not exchange order flow. The registry's ensemble is a fixed rule vote, not a fitted machine learning model. Feature characterization implements EWMA volatility, ATR ranks, Wilder ADX, directional efficiency, short-window R/S Hurst proxy, distribution moments, Jarque–Bera, lag-one autocorrelation and UTC session summaries. A fitted GARCH model and learned ensembles remain separate future research; they are not silently substituted.

Successful eligibility remains research evidence only. No report sets live approval or bypasses owner approval, execution reconciliation, broker protective stops, firm constraints, or the risk gate.
