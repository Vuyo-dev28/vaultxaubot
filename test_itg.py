import pandas as pd
import numpy as np
import sys
import os

# Add the project directory to sys.path
sys.path.append(os.getcwd())

from itg_strategy import get_itg_signals

def test_itg_signals():
    # Create mock data (100 bars)
    np.random.seed(42)
    close_prices = np.cumsum(np.random.randn(100)) + 100
    df = pd.DataFrame({
        'close': close_prices,
        'high': close_prices + 0.1,
        'low': close_prices - 0.1,
        'open': close_prices - 0.05
    })
    
    config = {
        'tema_len': 14,
        'macd_fast': 12,
        'macd_slow': 26,
        'macd_signal': 9
    }
    
    print("Testing ITG Signals with mock data...")
    result = get_itg_signals(df, config)
    
    if result:
        print(f"Signal Result: {result}")
        print("\n✅ get_itg_signals executed successfully.")
        
        # Check if indicators are present
        if 'tema' in result and 'macd' in result:
            print("✅ Indicators (TEMA, MACD) calculated.")
        else:
            print("❌ Indicators missing in result.")
            
        # Check signal conditions
        print(f"TEMA UP: {result['is_tema_up']}")
        print(f"MACD BUY: {result['f_buy']}")
        print(f"BUY READY: {result['buy_ready']}")
    else:
        print("❌ get_itg_signals returned None.")

if __name__ == "__main__":
    test_itg_signals()
