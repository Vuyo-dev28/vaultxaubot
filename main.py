"""
MT5 Trend Pullback Bot (PRO VERSION)

Strategy:
- 50 EMA / 200 EMA Trend
- Pullback to 50 EMA
- RSI confirmation (40–50 / 50–60)
- Structure-based SL/TP (1:2 RR)
"""

import time
import MetaTrader5 as mt5
from datetime import datetime, timezone
import pandas as pd
import requests
import matplotlib.pyplot as plt
import os
import csv
import sys
import io
from dotenv import load_dotenv

# Force UTF-8 for terminal emojis on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Load environment variables
load_dotenv()

# Supabase Setup
from supabase import create_client, Client
SUPABASE_URL = os.getenv("SUPABASE_URL")
# Use Service Role Key if available (bypasses RLS), fallback to Anon Key
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Auto-Discovery of USER_ID
user_id = os.getenv("USER_ID")
if not user_id:
    print("\n" + "="*50)
    print("🚀 XAUBOT SETUP: NO USER_ID FOUND")
    print("="*50)
    email = input("Enter your Supabase Email: ")
    password = input("Enter your Supabase Password: ")
    
    try:
        # We use a temporary client to sign in and get the UID
        temp_supabase = create_client(SUPABASE_URL, os.getenv("SUPABASE_KEY") or SUPABASE_KEY)
        auth_res = temp_supabase.auth.sign_in_with_password({"email": email, "password": password})
        if auth_res.user:
            user_id = auth_res.user.id
            from dotenv import set_key
            set_key(".env", "USER_ID", user_id)
            print(f"✅ Success! Linked to User: {user_id}")
            print("Your UID has been saved to .env automatically.\n")
        else:
            print("❌ Login failed. Please check credentials.")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error during login: {e}")
        sys.exit(1)

# ======================================================================
# CONFIG
# ======================================================================

SYMBOLS = [
    "XAUUSD",
    # "Volatility 75 Index",
    # "Volatility 25 Index",
    # "Volatility 50 Index",
]

TIMEFRAME = mt5.TIMEFRAME_M15   # 🔥 Better than M1 for consistency
MAGIC_NUMBER = 234000

RSI_PERIOD = 14

# Load dynamic settings from environment
MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", 1))
RISK_PERCENT = float(os.getenv("RISK_PERCENT", 1.0))

TRAILING_STOP_TRIGGER = 4.0  # Activate trailing when profit hits $4

SESSION_START = 0
SESSION_END = 24

# Trailing
TRAIL_POSITION = False
TRAIL_ACTIVATION = 50
TRAIL_DISTANCE = 30
TRAIL_STEP = 5

# Telegram Config
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID_HERE")
ENABLE_TELEGRAM = True

LOG_FILE = "trades_log.csv"

# ======================================================================
# LOGGING
# ======================================================================

def log_to_csv(log_dict):
    file_exists = os.path.isfile(LOG_FILE)
    columns = ["Time", "Symbol", "Type", "Price", "SL", "TP", "Lots", "Profit", "Comment", "Status"]
    with open(LOG_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        if not file_exists:
            writer.writeheader()
        writer.writerow(log_dict)

def log_to_supabase(log_dict):
    try:
        data = {
            "trade_time": datetime.now().isoformat(),
            "symbol": log_dict.get("Symbol"),
            "type": log_dict.get("Type"),
            "price": float(log_dict.get("Price", 0)),
            "sl": float(log_dict.get("SL", 0)),
            "tp": float(log_dict.get("TP", 0)),
            "lots": float(log_dict.get("Lots", 0)),
            "profit": float(log_dict.get("Profit", 0)),
            "comment": log_dict.get("Comment"),
            "status": log_dict.get("Status"),
            "user_id": user_id
        }
        supabase.table("trades_log").insert(data).execute()
    except Exception as e:
        print(f"[ERROR] Supabase log failed: {e}")

def close_position(ticket, symbol, reason_msg):
    # Determine order type to close
    pos = mt5.positions_get(ticket=ticket)
    if not pos: return False
    pos = pos[0]
    
    order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": pos.volume,
        "type": order_type,
        "position": ticket,
        "magic": MAGIC_NUMBER,
        "comment": f"RSI Exit: {reason_msg}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request)
    if result.retcode == mt5.DONE:
        msg = f"🛡️ *RSI EXIT: {symbol}*\nReason: {reason_msg}\nPnL: ${pos.profit:.2f}"
        send_telegram_message(msg)
        print(f"[EXIT] {symbol} | {reason_msg} | PnL: ${pos.profit:.2f}".ljust(80))
        return True
    return False

def manage_positions():
    positions = mt5.positions_get()
    if not positions:
        return

    for pos in positions:
        # We no longer filter by magic number so that manual trades are ALSO trailed and protected
        
        symbol = pos.symbol
        df = get_rates(symbol)
        if df is None: continue
        
        # Get Current RSI
        sig = get_signals(df, symbol)
        rsi = sig['rsi']
        
        # BUY EXIT LOGIC
        if pos.type == mt5.ORDER_TYPE_BUY:
            if rsi < 30 or rsi > 65:
                close_position(pos.ticket, symbol, f"RSI {rsi:.1f} out of 30-65")
                continue
        
        # SELL EXIT LOGIC
        elif pos.type == mt5.ORDER_TYPE_SELL:
            if rsi < 35 or rsi > 70:
                close_position(pos.ticket, symbol, f"RSI {rsi:.1f} out of 35-70")
                continue # Moved to next position

        # =========================
        # TRAILING STOP LOGIC ($4 TRIGGER)
        # =========================
        price = mt5.symbol_info_tick(symbol).bid if pos.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).ask
        
        if pos.profit >= TRAILING_STOP_TRIGGER:
            from config import TRAILING_STOP_PCT
            
            if pos.type == mt5.ORDER_TYPE_BUY:
                # Calculate standard 0.1% trail
                trail_sl = round(price * (1 - TRAILING_STOP_PCT), 2)
                # Ensure we lock in at least $1.00 of profit (1.00 point on Gold)
                min_lock_in = round(pos.price_open + 1.00, 2)
                new_sl = max(trail_sl, min_lock_in)
                
                if new_sl > pos.sl + 0.05:
                    if modify_sl(pos.ticket, symbol, new_sl):
                        print(f"[TRAILING] {symbol} | Profit ${pos.profit:.2f} | SL Secured at {new_sl}")
            
            elif pos.type == mt5.ORDER_TYPE_SELL:
                # Calculate standard 0.1% trail
                trail_sl = round(price * (1 + TRAILING_STOP_PCT), 2)
                # Ensure we lock in at least $1.00 of profit
                min_lock_in = round(pos.price_open - 1.00, 2)
                new_sl = min(trail_sl, min_lock_in)
                
                if pos.sl == 0 or new_sl < pos.sl - 0.05:
                    if modify_sl(pos.ticket, symbol, new_sl):
                        print(f"[TRAILING] {symbol} | Profit ${pos.profit:.2f} | SL Secured at {new_sl}")
        else:
            # Monitoring progress toward $4 trigger
            if pos.profit > 0:
                print(f"[MONITOR] {symbol} | Profit: ${pos.profit:.2f} / ${TRAILING_STOP_TRIGGER:.2f} target", end="\r")

def send_telegram_message(message):
    if not ENABLE_TELEGRAM:
        return
    
    # Auto-fix Chat ID: Most groups/channels need -100 prefix
    chat_id = str(TELEGRAM_CHAT_ID)
    if not chat_id.startswith("-") and not chat_id.startswith("@") and len(chat_id) > 9:
        chat_id = f"-{chat_id}"
        
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code != 200:
            print(f"[ERROR] Telegram responded with {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[ERROR] Telegram failed: {e}")

def get_deal_reason(reason):
    if reason == mt5.DEAL_REASON_SL: return "Stop Loss 🛑"
    if reason == mt5.DEAL_REASON_TP: return "Take Profit 🎯"
    if reason == mt5.DEAL_REASON_CLIENT: return "Manual Exit 👤"
    return "Strategy Exit 🤖"

def send_deal_notification(deal):
    profit = deal.profit + deal.commission + deal.swap
    action = "PROFIT 💰" if profit >= 0 else "LOSS ❌"
    reason = get_deal_reason(deal.reason)
    
    msg = (
        f"<b>🏁 TRADE CLOSED: {deal.symbol}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>Result:</b> {action}\n"
        f"<b>Final Profit:</b> ${profit:.2f}\n"
        f"<b>Reason:</b> {reason}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )
    send_telegram_message(msg)
    
    # Log to CSV and Supabase
    log_data = {
        "Time": datetime.fromtimestamp(deal.time).strftime("%Y-%m-%d %H:%M:%S"),
        "Symbol": deal.symbol,
        "Type": "BUY" if deal.type == mt5.ORDER_TYPE_BUY else "SELL",
        "Price": deal.price,
        "SL": 0,
        "TP": 0,
        "Lots": deal.volume,
        "Profit": round(profit, 2),
        "Comment": reason,
        "Status": "CLOSED"
    }
    log_to_csv(log_data)
    log_to_supabase(log_data)
    print(f"[CLOSED] {deal.symbol} | {reason} | Profit: ${profit:.2f}")
    
    # Update analysis reports immediately after logging
    update_analysis_reports()

def send_telegram_chart(symbol, entry_price, timeframe, df):
    if not ENABLE_TELEGRAM:
        return
    
    try:
        # Create a professional chart
        plt.style.use('dark_background')
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [3, 1]})
        
        # Subplot 1: Price and EMAs
        ax1.plot(df.index, df['close'], label='Price', color='white', alpha=0.6)
        ax1.plot(df.index, df['ema50'], label='EMA 50', color='cyan', linewidth=1.5)
        ax1.plot(df.index, df['ema200'], label='EMA 200', color='magenta', linewidth=1.5)
        
        # Mark entry
        ax1.scatter(df.index[-1], entry_price, color='yellow', s=100, zorder=5, label='ENTRY')
        ax1.set_title(f"🚀 TRADE SETUP: {symbol} @ {entry_price:.2f}", color='yellow', fontsize=14)
        ax1.legend(loc='upper left')
        ax1.grid(alpha=0.2)
        
        # Subplot 2: RSI
        ax2.plot(df.index, df['rsi'], color='lime', label='RSI(14)')
        ax2.axhline(70, color='red', linestyle='--', alpha=0.5)
        ax2.axhline(30, color='green', linestyle='--', alpha=0.5)
        ax2.set_ylim(0, 100)
        ax2.legend(loc='upper left')
        ax2.grid(alpha=0.2)
        
        plt.tight_layout()
        
        filename = f"setup_{symbol}.png"
        plt.savefig(filename)
        plt.close()
        
        # Send to Telegram
        chat_id = str(TELEGRAM_CHAT_ID)
        if not chat_id.startswith("-") and len(chat_id) > 10:
            chat_id = f"-{chat_id}"
            
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        caption = f"📊 *Setup for {symbol}*\n💰 *Entry:* {entry_price:.2f}\n⏱ *Timeframe:* M1"
        
        with open(filename, 'rb') as photo:
            files = {'photo': photo}
            payload = {'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'}
            requests.post(url, data=payload, files=files, timeout=10)
            
        # Clean up
        if os.path.exists(filename):
            os.remove(filename)
            
    except Exception as e:
        print(f"[ERROR] Failed to send chart: {e}")

def modify_sl(ticket, symbol, new_sl):
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": symbol,
        "position": ticket,
        "sl": new_sl,
        "magic": MAGIC_NUMBER,
    }
    result = mt5.order_send(request)
    return result.retcode == mt5.DONE

# Track seen deals globally to avoid double-processing
_seen_deals = set()

def check_closed_trades(start_time):
    global _seen_deals
    now = datetime.now()
    # Always look back to ensure we catch everything
    deals = mt5.history_deals_get(start_time, now)
    if deals:
        for deal in deals:
            # Skip already-processed deals
            if deal.ticket in _seen_deals:
                continue
            
            # Only closing deals
            if deal.entry not in [mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_INOUT]:
                continue
                
            # We now record ALL closed trades (bot and manual) for complete analysis
            send_deal_notification(deal)
            _seen_deals.add(deal.ticket)
    
    # Always advance the timestamp
    return now

def send_telegram_chart(symbol, entry_price, timeframe, df):
    if not ENABLE_TELEGRAM:
        return
    
    try:
        # Create a professional chart
        plt.style.use('dark_background')
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [3, 1]})
        
        # Subplot 1: Price and EMAs
        ax1.plot(df.index, df['close'], label='Price', color='white', alpha=0.6)
        ax1.plot(df.index, df['ema50'], label='EMA 50', color='cyan', linewidth=1.5)
        ax1.plot(df.index, df['ema200'], label='EMA 200', color='magenta', linewidth=1.5)
        
        # Mark entry
        ax1.scatter(df.index[-1], entry_price, color='yellow', s=100, zorder=5, label='ENTRY')
        ax1.set_title(f"🚀 TRADE SETUP: {symbol} @ {entry_price:.2f}", color='yellow', fontsize=14)
        ax1.legend(loc='upper left')
        ax1.grid(alpha=0.2)
        
        # Subplot 2: RSI
        ax2.plot(df.index, df['rsi'], color='lime', label='RSI(14)')
        ax2.axhline(70, color='red', linestyle='--', alpha=0.5)
        ax2.axhline(30, color='green', linestyle='--', alpha=0.5)
        ax2.set_ylim(0, 100)
        ax2.legend(loc='upper left')
        ax2.grid(alpha=0.2)
        
        plt.tight_layout()
        
        filename = f"setup_{symbol}.png"
        plt.savefig(filename)
        plt.close()
        
        # Send to Telegram
        chat_id = str(TELEGRAM_CHAT_ID)
        if not chat_id.startswith("-") and len(chat_id) > 10:
            chat_id = f"-{chat_id}"
            
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        caption = f"📊 *Setup for {symbol}*\n💰 *Entry:* {entry_price:.2f}\n⏱ *Timeframe:* M1"
        
        with open(filename, 'rb') as photo:
            files = {'photo': photo}
            payload = {'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'}
            requests.post(url, data=payload, files=files, timeout=10)
            
        # Clean up
        if os.path.exists(filename):
            os.remove(filename)
            
    except Exception as e:
        print(f"[ERROR] Failed to send chart: {e}")

def update_analysis_reports():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Read the current log
            df = pd.read_csv(LOG_FILE, encoding='utf-8')
            # We only want CLOSED trades for analysis
            df_closed = df[df['Status'] == 'CLOSED'].copy()
            
            if df_closed.empty:
                return

            # Overall Stats
            total_trades = len(df_closed)
            total_pnl = df_closed['Profit'].sum()
            wins = df_closed[df_closed['Profit'] > 0]
            losses = df_closed[df_closed['Profit'] < 0]
            win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
            
            # Symbol Stats
            symbol_stats = []
            for symbol, group in df_closed.groupby('Symbol'):
                s_pnl = group['Profit'].sum()
                s_trades = len(group)
                s_wins = len(group[group['Profit'] > 0])
                s_wr = (s_wins / s_trades * 100) if s_trades > 0 else 0
                symbol_stats.append({
                    "Symbol": symbol,
                    "Trades": s_trades,
                    "PnL": round(s_pnl, 2),
                    "WinRate": round(s_wr, 1)
                })

            # Save to CSV Summary
            pd.DataFrame(symbol_stats).to_csv("analysis_results.csv", index=False, encoding='utf-8')

            # Save to Supabase
            try:
                user_id = os.getenv("USER_ID")
                if not user_id:
                    print("[ERROR] USER_ID missing in .env. Analysis NOT uploaded to Supabase.")
                    return

                for s in symbol_stats:
                    supabase.table("analysis_results").upsert({
                        "user_id": user_id,
                        "symbol": s["Symbol"],
                        "trades": s["Trades"],
                        "pnl": s["PnL"],
                        "win_rate": s["WinRate"],
                        "last_updated": datetime.now().isoformat()
                    }).execute()
            except Exception as se:
                print(f"[ERROR] Supabase analysis update failed: {se}")

            # Save to TXT Summary
            with open("analysis_results.txt", "w", encoding='utf-8') as f:
                f.write("=== TRADING BOT ANALYSIS ===\n")
                f.write(f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Trades: {total_trades}\n")
                f.write(f"Total Profit/Loss: ${total_pnl:.2f}\n")
                f.write(f"Overall Win Rate: {win_rate:.2f}%\n\n")
                f.write("=== PERFORMANCE BY SYMBOL ===\n")
                for s in symbol_stats:
                    f.write(f"{s['Symbol']}: {s['Trades']} trades | PnL: ${s['PnL']:.2f} | WR: {s['WinRate']}%\n")
            
            # If successful, break retry loop
            break

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            print(f"[ERROR] Could not update analysis after {max_retries} attempts: {e}")

def initialize_mt5():
    if not mt5.initialize():
        print("[ERROR] MT5 init failed:", mt5.last_error())
        return False
    print("[OK] MT5 Connected")
    return True

# ======================================================================
# DATA
# ======================================================================

def get_rates(symbol):
    rates = mt5.copy_rates_from_pos(symbol, TIMEFRAME, 0, 300)
    if rates is None:
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

# ======================================================================
# STRATEGY (🔥 NEW CORE)
# ======================================================================

def get_signals(df, symbol):
    if df is None or len(df) < 200:
        return None

    # =========================
    # EMA TREND
    # =========================
    df['ema50'] = df['close'].ewm(span=50).mean()
    df['ema200'] = df['close'].ewm(span=200).mean()

    # =========================
    # RSI
    # =========================
    delta = df['close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    curr = df.iloc[-1]
    prev = df.iloc[-2]

    price = curr['close']
    ema50 = curr['ema50']
    ema200 = curr['ema200']
    rsi = curr['rsi']
    prev_rsi = prev['rsi']

    # =========================
    # TREND
    # =========================
    uptrend = ema50 > ema200
    downtrend = ema50 < ema200

    # =========================
    # PULLBACK ZONE (tight)
    # =========================
    ema_dist = (price - ema50) / ema50

    pullback_buy = ema_dist <= 0.0009
    pullback_sell = ema_dist >= -0.0009

    # =========================
    # 🎯 RSI POINT TRIGGERS (SNIPER)
    # =========================
    buy_rsi_trigger = prev_rsi < 35 and rsi >= 35
    sell_rsi_trigger = prev_rsi > 54 and rsi <= 54

    # =========================
    # FINAL SIGNALS
    # =========================
    buy_signal = uptrend and pullback_buy and buy_rsi_trigger
    sell_signal = downtrend and pullback_sell and sell_rsi_trigger

    # =========================
    # TERMINAL FEEDBACK
    # =========================
    trend_type = "UP" if uptrend else "DOWN" if downtrend else "SIDE"
    ema_dist_pct = ema_dist * 100

    # Show RSI proximity to trigger
    if uptrend:
        rsi_status = f"{rsi:.1f} ({'🔥' if buy_rsi_trigger else f'→45:{45-rsi:.1f}'})"
    elif downtrend:
        rsi_status = f"{rsi:.1f} ({'🔥' if sell_rsi_trigger else f'→55:{rsi-55:.1f}'})"
    else:
        rsi_status = f"{rsi:.1f}"

    return {
        "price": price,
        "buy": buy_signal,
        "sell": sell_signal,
        "rsi": rsi,
        "reason": f"Trend:{trend_type} | EMA_Dist:{ema_dist_pct:+.3f}% | RSI:{rsi_status}"
    }
# ======================================================================
# SL / TP (STRUCTURE BASED)
# ======================================================================

def get_sl_tp(df, price, direction, symbol):
    # Get symbol info for precision and stops level
    info = mt5.symbol_info(symbol)
    if info is None:
        return None, None
    
    digits = info.digits
    stops_level = info.trade_stops_level * info.point
    
    # ATR for dynamic buffer
    atr = (df['high'] - df['low']).rolling(14).mean().iloc[-1]

    # Structure
    swing_low = df['low'].rolling(10).min().iloc[-1]
    swing_high = df['high'].rolling(10).max().iloc[-1]

    buffer = max(atr * 1.2, stops_level * 1.5)

    if direction == "buy":
        sl = swing_low - buffer
        # Ensure SL is below price and respects stops level
        if sl > price - stops_level:
            sl = price - stops_level - (info.point * 10)
        
        risk = price - sl
        tp = price + (risk * 1.5)
    else:
        sl = swing_high + buffer
        # Ensure SL is above price and respects stops level
        if sl < price + stops_level:
            sl = price + stops_level + (info.point * 10)
            
        risk = sl - price
        tp = price - (risk * 1.5)

    # Final rounding to symbol digits
    sl = round(sl, digits)
    tp = round(tp, digits)

    return sl, tp
# ======================================================================
# LOT SIZE
# ======================================================================

def get_lot(symbol, sl_points=None):
    info = mt5.symbol_info(symbol)
    if info is None:
        return 0.01
    
    # Calculate balance-based risk if SL is provided
    account = mt5.account_info()
    if account and sl_points and sl_points > 0:
        balance = account.balance
        risk_amount = balance * (RISK_PERCENT / 100)
        
        # Point value calculation
        # For Gold: 1 lot, 100 points = $100 profit/loss usually
        tick_value = info.trade_tick_value
        tick_size = info.trade_tick_size
        
        if tick_value and tick_size:
            # Lots = Risk / (SL_Points * Value_Per_Point)
            lot = risk_amount / (sl_points * (tick_value / tick_size) * info.point)
            
            # Floor to volume step
            step = info.volume_step
            lot = max(info.volume_min, round(lot / step) * step)
            return min(lot, info.volume_max)

    # Fallback to minimum lot if no SL info
    return info.volume_min

# ======================================================================
# FILL MODE FIX
# ======================================================================

def get_filling_mode(symbol):
    info = mt5.symbol_info(symbol)

    if info is None:
        return mt5.ORDER_FILLING_RETURN

    mode = info.filling_mode
    if mode & 1:
        return mt5.ORDER_FILLING_FOK
    elif mode & 2:
        return mt5.ORDER_FILLING_IOC
    else:
        return mt5.ORDER_FILLING_RETURN

# ======================================================================
# ORDER EXECUTION
# ======================================================================

def place_order(symbol, order_type, lot, sl, tp):
    tick = mt5.symbol_info_tick(symbol)

    price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
    filling = get_filling_mode(symbol)

    # Normalize price and stops
    info = mt5.symbol_info(symbol)
    digits = info.digits
    price = round(price, digits)
    sl = round(sl, digits)
    tp = round(tp, digits)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 30,
        "magic": MAGIC_NUMBER,
        "comment": "TREND_PULLBACK_BOT",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling,
    }

    result = mt5.order_send(request)

    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"[OK] TRADE {symbol} LOT:{lot}")
        
        # Format Telegram Message
        action_str = "BUY 🔵" if order_type == mt5.ORDER_TYPE_BUY else "SELL 🔴"
        tg_msg = (
            f"<b>🚀 NEW SIGNAL: {symbol}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<b>Direction:</b> {action_str}\n"
            f"<b>Entry Price:</b> {price}\n"
            f"<b>Stop Loss:</b> {sl}\n"
            f"<b>Take Profit:</b> {tp}\n"
            f"<b>Lot Size:</b> {lot}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<i>Trend Pullback Strategy</i>"
        )
        send_telegram_message(tg_msg)

        # CSV and Supabase Logging
        log_data = {
            "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Symbol": symbol,
            "Type": "BUY" if order_type == mt5.ORDER_TYPE_BUY else "SELL",
            "Price": price,
            "SL": sl,
            "TP": tp,
            "Lots": lot,
            "Profit": 0,
            "Comment": "ENTRY",
            "Status": "OPEN"
        }
        log_to_csv(log_data)
        log_to_supabase(log_data)
    else:
        print(f"[ERROR] ORDER FAILED {symbol}", result)

# ======================================================================
# POSITION MANAGEMENT (UNCHANGED CORE)
# ======================================================================

def manage_positions():
    positions = mt5.positions_get()
    if not positions:
        return

    for pos in positions:
        symbol = pos.symbol
        ticket = pos.ticket
        entry = pos.price_open
        sl = pos.sl
        tp = pos.tp
        type_ = pos.type

        info = mt5.symbol_info(symbol)
        tick = mt5.symbol_info_tick(symbol)

        curr_price = tick.bid if type_ == mt5.ORDER_TYPE_BUY else tick.ask
        point = info.point

        profit_points = abs(curr_price - entry) / point

        new_sl = sl

        if TRAIL_POSITION and profit_points >= TRAIL_ACTIVATION:
            if type_ == mt5.ORDER_TYPE_BUY:
                trail_sl = curr_price - (TRAIL_DISTANCE * point)
                if trail_sl > sl:
                    new_sl = trail_sl
            else:
                trail_sl = curr_price + (TRAIL_DISTANCE * point)
                if trail_sl < sl:
                    new_sl = trail_sl

        if new_sl != sl:
            new_sl = round(new_sl, info.digits)
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": symbol,
                "position": ticket,
                "sl": new_sl,
                "tp": tp,
            }
            mt5.order_send(request)

# ======================================================================
# SESSION
# ======================================================================

def in_session():
    hour = datetime.now(timezone.utc).hour
    return SESSION_START <= hour < SESSION_END

# ======================================================================
# MAIN LOOP
# ======================================================================

def run_bot():
    if not initialize_mt5():
        return

    print("[INFO] Trend Pullback Bot Running")
    print(f"[INFO] Scanning: {', '.join(SYMBOLS)}")
    
    # Telegram Startup Test
    send_telegram_message("<b>🤖 BOT STARTED: Telegram Notifications Active</b>")

    # Time tracking for closed trades
    last_check = datetime.now()
    
    # Sync analysis reports on startup
    update_analysis_reports()

    try:
        while True:
            
            # Check for closed trades hits since last loop
            last_check = check_closed_trades(last_check)

            if not in_session():
                print(f"[WAIT] Outside session hours ({SESSION_START}:00 - {SESSION_END}:00). Waiting...", end="\r")
                time.sleep(5)
                continue

            manage_positions()
            positions = mt5.positions_get() or []

            for symbol in SYMBOLS:

                df = get_rates(symbol)
                if df is None:
                    print(f"[ERROR] No data for {symbol}. Make sure it is in Market Watch.", flush=True)
                    continue
                    
                sig = get_signals(df, symbol)

                if not sig:
                    continue

                # Professional scrolling logs
                now = datetime.now().strftime("%H:%M:%S")
                log_msg = f"[{now}] {symbol} | Price:{sig['price']:.2f} | {sig['reason']}"
                print(log_msg, flush=True)

                if len(positions) >= MAX_POSITIONS:
                    print(f"[{now}] {symbol} | [LIMIT] Max Positions ({MAX_POSITIONS}) reached", flush=True)
                    continue

                # Check if we already have a position for THIS symbol
                symbol_positions = [p for p in positions if p.symbol == symbol]

                if len(symbol_positions) >= 10:
                    print(f"[{now}] {symbol} | [LIMIT] Already have 10 {symbol} trades", flush=True)
                    continue

                if sig["buy"]:
                    sl, tp = get_sl_tp(df, sig["price"], "buy", symbol)
                    # Calculate SL distance in points
                    sl_points = abs(sig["price"] - sl) / mt5.symbol_info(symbol).point
                    lot = get_lot(symbol, sl_points)
                    
                    if place_order(symbol, mt5.ORDER_TYPE_BUY, lot, sl, tp):
                        send_telegram_chart(symbol, sig["price"], mt5.TIMEFRAME_M1, df)

                elif sig["sell"]:
                    sl, tp = get_sl_tp(df, sig["price"], "sell", symbol)
                    # Calculate SL distance in points
                    sl_points = abs(sig["price"] - sl) / mt5.symbol_info(symbol).point
                    lot = get_lot(symbol, sl_points)
                    
                    if place_order(symbol, mt5.ORDER_TYPE_SELL, lot, sl, tp):
                        send_telegram_chart(symbol, sig["price"], mt5.TIMEFRAME_M1, df)

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("Stopped")
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    run_bot()