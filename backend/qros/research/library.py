"""Curated research templates; source descriptions are not claims of profitability."""
from qros.research.registry import registry_dicts

AQR = 'https://www.aqr.com/insights/research/journal-article/a-century-of-evidence-on-trend-following-investing'
SCHWAB = 'https://www.schwab.com/learn/story/ins-and-outs-swing-trade'
FIDELITY = 'https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/bollinger-band-width'

def library():
    registry = {s['id']: s for s in registry_dicts()}
    choices = [
        ('momentum', 'Session impulse continuation', 'H1', ['XAUUSD','USDJPY','USDCAD'],
         'Broad research support for diversified trend following; filtered to NY session displacement aligned with 50-bar trend.',
         'Liquid instruments and slower turnover help capacity; correlated USD exposure and whipsaws limit scale.', AQR,
         {'atr_period':14,'stop_atr_multiple':2.5,'target_atr_multiple':3.0}),
        ('trend_pullback', 'Trend pullback continuation', 'M15', ['XAUUSD','GBPUSD','USDCAD'],
         'A systematic interpretation of trend/bounce trading, requiring multi-bar pullback and active-session reclaim.',
         'Moderate turnover; trend reversals and missed fills require stress testing.', SCHWAB,
         {'atr_period':14,'stop_atr_multiple':2.0,'target_atr_multiple':3.0}),
        ('mean_reversion', 'Range mean reversion', 'M15', ['XAUUSD','GBPUSD','USDJPY'],
         'Band displacement with a 40-bar efficiency filter and rejection candle confirmation during active sessions.',
         'Capacity is sensitive to spreads and trend transitions; no averaging down or martingale.', FIDELITY,
         {'atr_period':14,'stop_atr_multiple':2.5,'target_atr_multiple':2.5}),
        ('squeeze', 'Volatility squeeze breakout', 'H1', ['USDCAD','GBPUSD','XAUUSD'],
         'Band-width contraction motivates the hypothesis; requires expansion bar breaking 10-bar channel in direction of 50-SMA.',
         'Expansion can worsen slippage; simultaneous breakouts share portfolio risk.', FIDELITY,
         {'atr_period':14,'stop_atr_multiple':2.5,'target_atr_multiple':3.0}),
        ('failed_breakout', 'Failed-breakout reversal', 'H1', ['XAUUSD','EURUSD','USDJPY'],
         'London-close exhaustion reversal after stretched 4-bar displacement away from 20-bar mean.',
         'Fast reversals, spread spikes and genuine breakouts limit capacity.', SCHWAB,
         {'atr_period':14,'stop_atr_multiple':2.0,'target_atr_multiple':3.0}),
    ]
    return [{**registry[sid], 'title': title, 'default_timeframe': tf,
             'suggested_symbols': symbols, 'evidence': evidence, 'scaling_limits': scaling,
             'sources': [source], 'template_version': 1,
             'default_runtime': runtime,
             'optimization_policy': 'Fork a research version; entry rules fixed in v1. Test stop/target/ATR/timeframe changes on development data; never tune the final holdout.'}
            for sid,title,tf,symbols,evidence,scaling,source,runtime in choices]
