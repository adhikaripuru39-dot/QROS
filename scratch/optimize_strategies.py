"""Optimize update_order_blocks to scan incrementally range(max(2, last_count), len(df_h1))."""

# 1. Update strategy_ob_allday.py
with open("paper_trading/strategies/strategy_ob_allday.py", "r", encoding="utf-8") as f:
    content = f.read()

target = "        self.active_bull_obs.clear()\n        self.active_bear_obs.clear()\n\n        for i in range(2, len(df_h1)):"
replacement = "        start_idx = max(2, self.last_h1_count)\n        for i in range(start_idx, len(df_h1)):"
content = content.replace(target, replacement)
with open("paper_trading/strategies/strategy_ob_allday.py", "w", encoding="utf-8") as f:
    f.write(content)

# 2. Update strategy_ob_trend.py
with open("paper_trading/strategies/strategy_ob_trend.py", "r", encoding="utf-8") as f:
    content = f.read()
content = content.replace(target, replacement)
with open("paper_trading/strategies/strategy_ob_trend.py", "w", encoding="utf-8") as f:
    f.write(content)

# 3. Update strategy_fvg_overlap.py
with open("paper_trading/strategies/strategy_fvg_overlap.py", "r", encoding="utf-8") as f:
    content = f.read()
target_fvg = "        self.active_bull_gaps.clear()\n        self.active_bear_gaps.clear()\n\n        for i in range(2, len(df_h1)):"
replacement_fvg = "        start_idx = max(2, self.last_h1_count)\n        for i in range(start_idx, len(df_h1)):"
content = content.replace(target_fvg, replacement_fvg)
with open("paper_trading/strategies/strategy_fvg_overlap.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated strategies to incremental O(1) order block updates!")