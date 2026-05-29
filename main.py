import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import time

# =========================
# CONFIG
# =========================
SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M1

LOT = 0.01
DEVIATION = 20

EMA_FAST = 9
EMA_SLOW = 21
RSI_LEN = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

ATR_PERIOD = 14
SL_MULTIPLIER = 2.0
TP_MULTIPLIER = 3.5

CHECK_INTERVAL = 0.2
COOLDOWN = 30

last_trade_time = 0

# =========================
# INIT MT5
# =========================
if not mt5.initialize():
    print("❌ MT5 initialization failed")
    quit()

print("⚡ BOT RUNNING (SL/TP ONLY MODE)")

# =========================
# INDICATORS
# =========================
def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def rsi(series, period):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def macd(series):
    fast = ema(series, MACD_FAST)
    slow = ema(series, MACD_SLOW)
    macd_line = fast - slow
    signal = macd_line.ewm(span=MACD_SIGNAL, adjust=False).mean()
    return macd_line, signal

def atr(df, period=14):
    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

# =========================
# DATA
# =========================
def get_data():
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 250)
    return pd.DataFrame(rates)

# =========================
# SIGNALS
# =========================
def compute(df):
    df = df.copy()

    close = df["close"]

    df["ema_fast"] = ema(close, EMA_FAST)
    df["ema_slow"] = ema(close, EMA_SLOW)
    df["rsi"] = rsi(close, RSI_LEN)
    df["macd"], df["signal"] = macd(close)
    df["atr"] = atr(df, ATR_PERIOD)

    df.dropna(inplace=True)

    if len(df) < 2:
        return False, False, 0, 0, 0

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

    strength = (
        abs(last.ema_fast - last.ema_slow) * 100 +
        abs(last.rsi - 50) +
        abs(last.macd - last.signal) * 50
    )

    strength = min(max(strength, 0), 100)

    atr_value = last.atr

    return buy, sell, strength, last.close, atr_value

# =========================
# POSITION CHECK
# =========================
def has_position():
    pos = mt5.positions_get(symbol=SYMBOL)
    return pos is not None and len(pos) > 0

# =========================
# ORDER (SL / TP ONLY)
# =========================
def order(direction, atr_value):
    if np.isnan(atr_value) or atr_value <= 0:
        print("❌ Invalid ATR, skipping trade")
        return

    tick = mt5.symbol_info_tick(SYMBOL)

    sl_distance = atr_value * SL_MULTIPLIER
    tp_distance = atr_value * TP_MULTIPLIER

    if direction == "buy":
        price = tick.ask
        sl = price - sl_distance
        tp = price + tp_distance
        order_type = mt5.ORDER_TYPE_BUY
    else:
        price = tick.bid
        sl = price + sl_distance
        tp = price - tp_distance
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
        "magic": 123456,
        "comment": "EMA RSI MACD ATR BOT",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    print("TRADE RESULT:", result)

# =========================
# MAIN LOOP
# =========================
while True:
    df = get_data()

    buy, sell, strength, price, atr_value = compute(df)

    print(f"\nPrice: {price:.2f} | ATR: {atr_value:.2f} | Strength: {strength:.2f}%")

    now = time.time()
    position_exists = has_position()
    cooldown = (now - last_trade_time) < COOLDOWN

    # =========================
    # ENTRY ONLY
    # =========================
    if not position_exists and not cooldown:

        if buy and strength > 30:
            print("🟢 BUY SIGNAL")
            order("buy", atr_value)
            last_trade_time = now

        elif sell and strength > 30:
            print("🔴 SELL SIGNAL")
            order("sell", atr_value)
            last_trade_time = now

    # =========================
    # WAIT WHILE TRADE IS ACTIVE
    # =========================
    elif position_exists:
        print("📊 Trade running (waiting for SL/TP)")

    elif cooldown:
        print("⏳ Cooldown active")

    time.sleep(CHECK_INTERVAL)