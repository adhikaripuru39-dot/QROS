# Connected account rules

The owner confirmed **2-Step Free Trial** on 2026-10-23. MT5 funding history
establishes initial simulated capital of USD 50,000; MT5 identifies a demo account.

The active profile uses a 5% daily loss amount ($2,500), measured against equity
with the daily floor anchored to the balance at midnight Europe/Prague. Maximum
loss is static at 10% of initial capital ($45,000 equity floor). Free Trial target
is 5%, with two minimum trading days and no consistency rule.

The trial simulates Challenge phase 1. Published evaluation exceptions permit
news trading and holding through overnight/weekend breaks. Internal risk limits
remain stricter. These settings must be reviewed if changing to a funded account.

Sources reviewed 2026-10-23:

- https://ftmo.com/en/ftmo-free-trial/
- https://ftmo.com/en/trading-objectives/
- https://ftmo.com/en/faq/can-i-trade-news/
- https://ftmo.com/en/faq/can-i-hold-positions-overnight-or-over-the-weekend/

Unverified items remain explicit: actual commission schedule, historical swap and
conversion costs, historical timestamp/session mapping, trial start/expiry, and
the first firm-midnight balance anchor. The configured $7 per lot round-trip
commission is a conservative modeling assumption, not an observed broker fee.
The published trial duration is 14 days; funding timestamps do not prove its expiry.

The profile does not approve any strategy or enable order submission.
