import pandas as pd
import numpy as np
from strategy import calculate_tema, calculate_macd

def get_itg_signals(df, config):
    """
    Implements ITG Scalper Buy/Sell signals based on Pine Script logic.
    
    Logic:
    - TEMA trend (Up if current >= previous, Down if current < previous)
    - MACD filter (Buy if MACD >= Signal, Sell if MACD < Signal)
    
    Returns a dictionary with signal information.
    """
    if df is None or len(df) < 30: # Need enough data for TEMA and MACD
        return None

    # 1. Calculate Indicators
    df = calculate_tema(df, length=config.get('tema_len', 14))
    df = calculate_macd(df, 
                        fast_period=config.get('macd_fast', 12), 
                        slow_period=config.get('macd_slow', 26), 
                        signal_period=config.get('macd_signal', 9))
    
    # 2. Get latest and previous bars
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 3. Triple EMA Trend Calculation
    ma_up = last['tema'] >= prev['tema']
    ma_down = last['tema'] < prev['tema']
    
    # 4. Filter Formula (MACD)
    f_buy = last['macd'] >= last['macd_signal']
    f_sell = last['macd'] < last['macd_signal']
    
    # 5. Entry signals
    # Note: Pine script uses 'last_tran' to only alert on changes.
    # In this bot, the main loop handles position management, so we return the state.
    
    buy_signal = ma_up and f_buy
    sell_signal = ma_down and f_sell
    
    return {
        'price': last['close'],
        'tema': last['tema'],
        'macd': last['macd'],
        'macd_signal': last['macd_signal'],
        'is_tema_up': ma_up,
        'is_tema_down': ma_down,
        'f_buy': f_buy,
        'f_sell': f_sell,
        'buy_ready': buy_signal,
        'sell_ready': sell_signal
    }
