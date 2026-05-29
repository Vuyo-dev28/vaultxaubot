import MetaTrader5 as mt5
import pandas as pd
import time

# =========================
# CONFIG
# =========================
SYMBOL = "XAUUSD"
LOT = 0.01
DEVIATION = 20
TIMEFRAME = mt5.TIMEFRAME_M5

EMA_FAST = 9
EMA_SLOW = 21
RSI_LEN = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

ATR_LEN = 14
CHECK_INTERVAL = 0.2  # fast but safe

ATR_SL_MULT = 1.5
ATR_TP_MULT = 5.0
BREAKEVEN_MULT = 1.0  # move SL to BE after 1R

MAGIC = 123456

# =========================
# INIT MT5
# =========================
if not mt5.initialize():
    print("MT5 init failed")
    quit()

print("⚡ FIXED MT5 BOT RUNNING...")

# =========================
# INDICATORS
# =========================
def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def rsi(series, period):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def macd(series):
    fast = ema(series, MACD_FAST)
    slow = ema(series, MACD_SLOW)
    macd_line = fast - slow
    signal = macd_line.ewm(span=MACD_SIGNAL, adjust=False).mean()
    return macd_line, signal

def atr(df):
    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)

    return tr.rolling(ATR_LEN).mean()

# =========================
# DATA (ONLY CLOSED CANDLES)
# =========================
def get_data():
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 250)
    df = pd.DataFrame(rates)

    # IMPORTANT: remove current forming candle
    df = df.iloc[:-1]

    return df

# =========================
# SIGNALS
# =========================
def compute_signals(df):
    close = df["close"]

    df["ema_fast"] = ema(close, EMA_FAST)
    df["ema_slow"] = ema(close, EMA_SLOW)
    df["rsi"] = rsi(close, RSI_LEN)
    df["macd"], df["signal"] = macd(close)
    df["atr"] = atr(df)

    df = df.dropna()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    buy = (
        prev.ema_fast <= prev.ema_slow and
        last.ema_fast > last.ema_slow and
        last.rsi > 50 and
        last.macd > last.signal
    )

    sell = (
        prev.ema_fast >= prev.ema_slow and
        last.ema_fast < last.ema_slow and
        last.rsi < 50 and
        last.macd < last.signal
    )

    return buy, sell, last

# =========================
# POSITION SYNC (IMPORTANT FIX)
# =========================
def get_position():
    pos = mt5.positions_get(symbol=SYMBOL)
    if pos:
        return pos[0]
    return None

# =========================
# ORDER
# =========================
def open_trade(direction, atr_value):
    tick = mt5.symbol_info_tick(SYMBOL)

    price = tick.ask if direction == "buy" else tick.bid

    sl_dist = atr_value * ATR_SL_MULT
    tp_dist = atr_value * ATR_TP_MULT

    if direction == "buy":
        sl = price - sl_dist
        tp = price + tp_dist
        order_type = mt5.ORDER_TYPE_BUY
    else:
        sl = price + sl_dist
        tp = price - tp_dist
        order_type = mt5.ORDER_TYPE_SELL

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": LOT,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": DEVIATION,
        "magic": MAGIC,
        "comment": "FIXED BOT",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    print("TRADE:", result)

# =========================
# CLOSE
# =========================
def close_position(pos):
    tick = mt5.symbol_info_tick(SYMBOL)

    close_type = mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY
    price = tick.bid if pos.type == 0 else tick.ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": pos.volume,
        "type": close_type,
        "position": pos.ticket,
        "price": price,
        "deviation": DEVIATION,
        "magic": MAGIC,
        "comment": "CLOSE",
    }

    mt5.order_send(request)

# =========================
# BREAKEVEN
# =========================
def breakeven():
    pos = get_position()
    if not pos:
        return

    tick = mt5.symbol_info_tick(SYMBOL)

    entry = pos.price_open
    current = tick.bid if pos.type == 0 else tick.ask

    atr_val = abs(entry - pos.sl) / ATR_SL_MULT

    profit_move = abs(current - entry)

    if profit_move >= atr_val * BREAKEVEN_MULT:
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": pos.ticket,
            "sl": entry,
            "tp": pos.tp,
        }
        mt5.order_send(request)

# =========================
# MAIN LOOP
# =========================
last_candle_time = None

while True:
    df = get_data()
    buy, sell, last = compute_signals(df)

    candle_time = last["time"]

    if candle_time != last_candle_time:
        last_candle_time = candle_time

        pos = get_position()

        print(f"\nPrice: {last.close:.2f} | ATR: {last.atr:.2f}")

        # ENTRY LOGIC
        if pos is None:
            if buy:
                print("🟢 BUY")
                open_trade("buy", last.atr)

            elif sell:
                print("🔴 SELL")
                open_trade("sell", last.atr)

        else:
            # reverse logic
            if (pos.type == 0 and sell) or (pos.type == 1 and buy):
                print("🔁 Reverse trade")
                close_position(pos)

        breakeven()

    time.sleep(CHECK_INTERVAL)