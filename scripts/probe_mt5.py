"""Read-only MT5 connection discovery; never sends or changes an order."""
import json
import argparse
import sys
from pathlib import Path
from datetime import datetime,timezone
import MetaTrader5 as mt5
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from qros.config.settings import Settings
parser=argparse.ArgumentParser();parser.add_argument('--path',default=Settings().mt5_path);args=parser.parse_args()
if not args.path:parser.error('Configure QROS_MT5_PATH or pass the intended terminal --path')
report={'observed_at':datetime.now(timezone.utc).isoformat(),'orders_submitted':0}
try:
    connected=mt5.initialize(path=args.path,timeout=15000)
    report['initialized']=bool(connected)
    if not connected:
        report['error']=list(mt5.last_error())
    else:
        terminal=mt5.terminal_info(); account=mt5.account_info()
        report['terminal_connected']=bool(terminal and terminal.connected)
        report['terminal_trade_allowed']=bool(terminal and terminal.trade_allowed)
        report['account_available']=account is not None
        if account:
            report['account']={'server':account.server,'company':account.company,'currency':account.currency,'is_demo':account.trade_mode==mt5.ACCOUNT_TRADE_MODE_DEMO,'trade_allowed':account.trade_allowed,'balance':account.balance,'equity':account.equity,'login_suffix':str(account.login)[-3:]}
        symbols=mt5.symbols_get() or ()
        wanted=['XAUUSD','EURUSD','GBPUSD','USDJPY','USDCHF','USDCAD','AUDUSD']
        matches={base:[s.name for s in symbols if s.name.upper().startswith(base)] for base in wanted}
        report['symbol_matches']=matches
        report['position_count']=None if mt5.positions_get() is None else len(mt5.positions_get())
        report['pending_order_count']=None if mt5.orders_get() is None else len(mt5.orders_get())
        report['quotes']={}
        for base,names in matches.items():
            if not names:continue
            symbol=base if base in names else names[0]
            mt5.symbol_select(symbol,True)
            info=mt5.symbol_info(symbol);tick=mt5.symbol_info_tick(symbol)
            if info and tick:
                report['quotes'][symbol]={'bid':tick.bid,'ask':tick.ask,'tick_time_utc':datetime.fromtimestamp(tick.time,timezone.utc).isoformat(),'point':info.point,'tick_size':info.trade_tick_size,'tick_value':info.trade_tick_value,'volume_min':info.volume_min,'volume_step':info.volume_step,'contract_size':info.trade_contract_size}
finally:
    mt5.shutdown()
    path=Path('var/readiness/mt5_connection.json');path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
print(json.dumps(report,indent=2,default=str))

