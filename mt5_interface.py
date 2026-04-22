import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import config

def initialize_mt5():
    """Initializes MetaTrader 5 and logs in with credentials."""
    initialized = False
    
    # Try with path first if provided
    if config.MT5_PATH:
        print(f"Attempting MT5 initialization with path: {config.MT5_PATH}")
        initialized = mt5.initialize(path=config.MT5_PATH)
        if not initialized:
            print(f"MT5 initialization failed with path, error code: {mt5.last_error()}. Retrying with auto-find...")
            
    # Try without path if no path provided or if path-based init failed
    if not initialized:
        print("Searching for the default MT5 terminal...")
        initialized = mt5.initialize()
        
    if not initialized:
        print(f"MT5 initialization failed across all attempts, error code: {mt5.last_error()}")
        return False

    print(f"Logging in to server: {config.MT5_SERVER}...")
    authorized = mt5.login(
        login=config.MT5_ACCOUNT,
        password=config.MT5_PASSWORD,
        server=config.MT5_SERVER
    )

    if authorized:
        print("Successfully connected to MT5.")
        account_info = mt5.account_info()._asdict()
        print(f"Account: {account_info['login']}, Balance: {account_info['balance']}")
        return True
    else:
        print(f"MT5 login failed, error code: {mt5.last_error()}")
        return False

def get_rates(symbol, timeframe, count):
    """Fetches historical price data from MT5 and returns as a pandas DataFrame."""
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
    if rates is None:
        print(f"Failed to fetch rates for {symbol}, error code: {mt5.last_error()}")
        return pd.DataFrame()

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

def get_symbol_info(symbol):
    """Fetches details for a specific symbol."""
    info = mt5.symbol_info(symbol)
    if info is None:
        print(f"Symbol {symbol} not found.")
    return info

def get_filling_mode(symbol):
    """Determines the correct filling mode for a symbol."""
    info = mt5.symbol_info(symbol)
    if info is None:
        return mt5.ORDER_FILLING_IOC
        
    # Check flags (1 = FOK, 2 = IOC)
    if info.filling_mode & 1:
        return mt5.ORDER_FILLING_FOK
    elif info.filling_mode & 2:
        return mt5.ORDER_FILLING_IOC
    else:
        return mt5.ORDER_FILLING_RETURN

def place_order(symbol, order_type, lot, sl=None, tp=None, comment="Bot Trade"):
    """Places a market order via MT5."""
    # Build request dictionary
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"Failed to get info for {symbol}")
        return None
        
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"Failed to get tick for {symbol}")
        return None
        
    price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
    price = round(price, symbol_info.digits)
    
    filling_mode = get_filling_mode(symbol)
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(lot),
        "type": order_type,
        "price": price,
        "magic": config.MAGIC_NUMBER,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_mode,
    }

    if sl: request["sl"] = round(float(sl), symbol_info.digits)
    if tp: request["tp"] = round(float(tp), symbol_info.digits)

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Order failed [{symbol}], retcode: {result.retcode} ({mt5.last_error()})")
    else:
        print(f"Order placed: {order_type} {lot} {symbol} at {price}")
    
    return result

def modify_position_sl(ticket, sl):
    """Modifies the stop-loss of an open position."""
    position = mt5.positions_get(ticket=ticket)
    if not position:
        return None
        
    pos = position[0]
    symbol_info = mt5.symbol_info(pos.symbol)
    
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": pos.symbol,
        "position": ticket,
        "sl": round(float(sl), symbol_info.digits),
        "tp": round(float(pos.tp), symbol_info.digits),
        "magic": pos.magic
    }
    
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"SL modification failed for ticket {ticket}, retcode: {result.retcode}")
    else:
        print(f"SL updated for ticket {ticket} to {sl}")
    return result

def close_position(ticket, symbol, comment="Bot Exit"):
    """Closes an open position."""
    position = mt5.positions_get(ticket=ticket)
    if not position:
        return None
        
    pos = position[0]
    symbol_info = mt5.symbol_info(symbol)
    
    order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
    
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"Failed to get tick for closing {symbol}")
        return None
        
    price = tick.bid if pos.type == mt5.POSITION_TYPE_BUY else tick.ask
    price = round(price, symbol_info.digits)
    
    filling_mode = get_filling_mode(symbol)
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(pos.volume),
        "type": order_type,
        "position": ticket,
        "price": price,
        "magic": pos.magic,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_mode,
    }
    
    # Get profit for display
    position = mt5.positions_get(ticket=ticket)
    pnl = position[0].profit if position else 0.0
    
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Close failed for ticket {ticket}, retcode: {result.retcode}")
    else:
        status = "PROFIT" if pnl >= 0 else "LOSS"
        print(f"Position {ticket} closed at {price}. [{status}] {pnl:+.2f}")
    return result

def close_mt5():
    """Closes the MT5 connection."""
    mt5.shutdown()
