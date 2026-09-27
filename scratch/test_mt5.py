import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

def test_pagination():
    if not mt5.initialize(path=r"C:\Program Files\MetaTrader 5\terminal64.exe"):
        print("Failed to initialize MT5")
        return
        
    all_rates = []
    dt = datetime.now()
    chunk_size = 5000
    
    for i in range(3):
        r = mt5.copy_rates_from("XAUUSD", mt5.TIMEFRAME_H1, dt, chunk_size)
        if r is None or len(r) == 0:
            break
        df = pd.DataFrame(r)
        df['timestamp'] = pd.to_datetime(df['time'], unit='s', utc=True)
        all_rates.append(df)
        
        # update dt to the oldest time in this chunk
        dt = df['timestamp'].min().replace(tzinfo=None)
        print(f"Chunk {i+1}: fetched {len(df)} bars. Oldest dt = {dt}")
        
    combined = pd.concat(all_rates).drop_duplicates(subset=['time']).sort_values('time').reset_index(drop=True)
    print(f"Total Combined (Deduplicated): {len(combined)}")
    mt5.shutdown()

if __name__ == "__main__":
    test_pagination()
