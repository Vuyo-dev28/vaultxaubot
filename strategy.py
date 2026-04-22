import pandas as pd
import numpy as np

def calculate_bollinger_bands(df, period=20, std_dev=1.5):
    """Adds Bollinger Bands columns to the DataFrame."""
    sma = df['close'].rolling(window=period).mean()
    std = df['close'].rolling(window=period).std()
    
    df['bb_mid'] = sma
    df['bb_upper'] = sma + (std * std_dev)
    df['bb_lower'] = sma - (std * std_dev)
    
    return df

def calculate_momentum(df, period=3):
    """Calculates momentum based on percentage change over a specified period."""
    # (Current Price - Price N periods ago) / Price N periods ago
    df['momentum'] = df['close'].pct_change(periods=period) * 100
    return df

def calculate_tema(df, length=14):
    """Calculates Triple Exponential Moving Average (TEMA)."""
    ema1 = df['close'].ewm(span=length, adjust=False).mean()
    ema2 = ema1.ewm(span=length, adjust=False).mean()
    ema3 = ema2.ewm(span=length, adjust=False).mean()
    
    df['tema'] = 3 * (ema1 - ema2) + ema3
    return df

def calculate_macd(df, fast_period=12, slow_period=26, signal_period=9):
    """Calculates Moving Average Convergence Divergence (MACD)."""
    fast_ema = df['close'].ewm(span=fast_period, adjust=False).mean()
    slow_ema = df['close'].ewm(span=slow_period, adjust=False).mean()
    
    df['macd'] = fast_ema - slow_ema
    df['macd_signal'] = df['macd'].rolling(window=signal_period).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    return df

def get_signals_info(df):
    """Returns detailed information about signal conditions and proximity."""
    if df.empty or len(df) < 20:
        return {}

    latest_bar = df.iloc[-1]
    
    # Distance to bands in points/percentage
    dist_to_upper = latest_bar['bb_upper'] - latest_bar['close']
    dist_to_lower = latest_bar['close'] - latest_bar['bb_lower']
    
    info = {
        "price": latest_bar['close'],
        "bb_mid": latest_bar['bb_mid'],
        "bb_upper": latest_bar['bb_upper'],
        "bb_lower": latest_bar['bb_lower'],
        "dist_to_upper": dist_to_upper,
        "dist_to_lower": dist_to_lower,
        "momentum": latest_bar['momentum'],
        "is_oversold": latest_bar['close'] < latest_bar['bb_lower'],
        "is_overbought": latest_bar['close'] > latest_bar['bb_upper'],
        "momentum_buy_ok": latest_bar['momentum'] < 0,
        "momentum_sell_ok": latest_bar['momentum'] > 0
    }
    
    return info
