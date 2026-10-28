Backtest API and boundaries
===========================

`BacktestEngine().run(bars, strategy, BacktestConfig(...))` accepts chronological
unique `Bar(time,open,high,low,close,spread)` bid bars. Spread is required in
absolute price units. A zero value is accepted only as an explicit caller input.
All prices/spreads must be finite, valid and positive/nonnegative respectively.

`strategy(tuple_of_completed_bars)` returns `Signal(side,lots,stop_distance,
take_distance)` or None. The engine calls it after processing a completed bar;
any entry occurs at the next bar's open. Only one position is supported. No new
signals are requested while a position is open. A final position closes at the
last bar's close. Callback code must itself avoid consulting external future data.

Modeled ask OHLC equals bid OHLC plus each bar's supplied spread. Long entry uses
ask and exit bid; short entry uses bid and exit ask. Slippage is adverse in price
units on entries/exits. If both stop and target are inside a bar the stop wins.
Stops gapping through their price execute at the worse open. Targets receive no
favorable gap improvement. Volumes and available entry margin are checked.
An adverse bar extreme that reaches the configured margin threshold triggers
conservative liquidation unless the stop is also hit (stop takes precedence).

Contract size, leverage, commission per lot per side, quote-to-account conversion,
swap debit per lot per elapsed 24h, volume bounds/step and margin threshold are
explicit assumptions. Commission is charged on both sides. Swap is an elapsed
time approximation using bar-open timestamps; actual rollover, triple-swap and
changing conversion rates require broker-specific extensions. Account values
must use a consistent currency. This is not a full exchange futures/option margin
engine. Portfolio netting, order book liquidity, latency and partial fills are not
represented by OHLC bars. `run` does not consume observed tick archives.

Results include trades, cash, bar-end marked equity, rejected orders, assumptions
and bar-end `max_drawdown` (not a proven intrabar worst-case drawdown). Costs are
reported separately from gross P/L. Research results cannot establish broker
execution behavior or justify live deployment on their own.

Observed quote replay
--------------------

`run_ticks(bars,ticks,strategy,config,rollover=None,swap_records=(),cost_records=())`
consumes `Tick(time_msc,bid,ask)` in original chronological source order. Parent
bars define completed signal boundaries. The last parent bar is an explicit end
boundary sentinel and is never traded; quotes at/after that timestamp are ignored.
The callback sees `bars[:i]`, then its entry executes at the first observed quote
in parent interval i. Stop/target resolution follows actual observed bid/ask order,
including quote gaps and short positions exiting on ask. Missing intervals reject
entries rather than creating synthetic ticks or falling back silently. The caller
may explicitly choose the separately labeled adverse OHLC `run` simulation when
quote history is absent. Existing positions span unknown quote gaps until the next
actual quote; this does not prove stops could not trigger in the missing interval.

`RolloverSchedule` takes broker timezone (IANA, supports DST), rollover hour,
triple-swap weekday and separate long/short account-currency debits per lot.
Weekend charging is omitted and Wednesday is only the configurable default.
Alternatively sourced `SwapRecord(time_msc,debit_per_lot,source)` values represent
actual observed financing charges for the simulated position. Do not provide both.
These records require compatible instrument/account/volume semantics supplied by
the caller, not inferred from random account deals.

`CostRecord(time_msc,commission_per_lot_side,source)` is an as-of commission
observation. Entry/exit use the latest record available by event time, so a future
cost observation cannot change an earlier fill. Before the first record, explicit
config commission applies. Sources must identify the broker observation/export;
this API checks presence, not independent authenticity of user-provided evidence.

For both engines, slippage may include base absolute-price cost, `slippage_per_lot`
times size, and `slippage_volatility_fraction` times the prior completed bar range.
The current bar range is never used for entry costs. These are explicit models,
not an order book measurement or a guarantee of execution. Tick replay results
record execution evidence and always set `live_eligible=False`; historical quotes
cannot establish real fill quality, operational safety or portfolio readiness.
