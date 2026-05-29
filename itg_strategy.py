import pandas as pd
import numpy as np


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    # Wilder's smoothing via EMA with alpha = 1/period
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / (avg_loss.replace(0, np.nan))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def _macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    fast_ema = series.ewm(span=fast, adjust=False).mean()
    slow_ema = series.ewm(span=slow, adjust=False).mean()
    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line


def get_itg_signals(df: pd.DataFrame, config: dict):
    """
    Produces buy/sell readiness using:
    - Fast EMA crossover Slow EMA
    - RSI threshold (50)
    - MACD line vs Signal line

    Mirrors the Pine Script logic provided by the user.
    """
    if df is None or len(df) < 3:
        return None

    # Parameters (defaults mirror your Pine Script)
    ema_fast_len = int(config.get('ema_fast', 9))
    ema_slow_len = int(config.get('ema_slow', 21))
    rsi_len = int(config.get('rsi_len', 14))
    macd_fast = int(config.get('macd_fast', 12))
    macd_slow = int(config.get('macd_slow', 26))
    macd_sig = int(config.get('macd_sig', 9))

    close = df['close']

    ema_fast = _ema(close, ema_fast_len)
    ema_slow = _ema(close, ema_slow_len)
    rsi = _rsi(close, period=rsi_len)
    macd_line, signal_line = _macd(close, fast=macd_fast, slow=macd_slow, signal=macd_sig)

    last_idx = len(df) - 1
    prev_idx = len(df) - 2

    last_fast = ema_fast.iloc[last_idx]
    last_slow = ema_slow.iloc[last_idx]
    prev_fast = ema_fast.iloc[prev_idx]
    prev_slow = ema_slow.iloc[prev_idx]

    last_rsi = rsi.iloc[last_idx]
    last_macd = macd_line.iloc[last_idx]
    last_signal = signal_line.iloc[last_idx]

    # Crossover / Crossunder
    crossover = (prev_fast < prev_slow) and (last_fast > last_slow)
    crossunder = (prev_fast > prev_slow) and (last_fast < last_slow)

    buy_cond = crossover and (last_rsi > 50) and (last_macd > last_signal)
    sell_cond = crossunder and (last_rsi < 50) and (last_macd < last_signal)

    return {
        'price': float(close.iloc[last_idx]),
        'ema_fast': float(last_fast),
        'ema_slow': float(last_slow),
        'rsi': float(last_rsi),
        'macd': float(last_macd),
        'macd_signal': float(last_signal),
        'crossover': bool(crossover),
        'crossunder': bool(crossunder),
        'buy_ready': bool(buy_cond),
        'sell_ready': bool(sell_cond)
    }
