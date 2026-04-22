import MetaTrader5 as mt5
import config

import math

def get_valid_lot(symbol, desired_lot):
    """Clamps and aligns the lot size according to symbol volume rules."""
    info = mt5.symbol_info(symbol)
    if info is None:
        print(f"❌ No symbol info for {symbol}")
        return None

    min_lot = info.volume_min
    max_lot = info.volume_max
    step = info.volume_step

    # Clamp within range
    lot = max(min_lot, min(desired_lot, max_lot))

    # Align to step and handle floating point precision
    if step > 0:
        decimal_places = max(0, -int(math.log10(step))) if step < 1 else 0
        lot = round(math.floor(lot / step) * step, decimal_places)
    
    # Final clamp to ensure it's still within range after rounding
    lot = max(min_lot, min(lot, max_lot))

    # Special override for Gold (XAUUSD) as requested
    if symbol == "XAUUSD":
        lot = min(lot, 0.01)

    return lot

def calculate_lot(symbol, risk_percent=1.0):
    """Calculates lot size based on account balance, risk percentage, and symbol properties."""
    info = mt5.symbol_info(symbol)
    account = mt5.account_info()

    if info is None or account is None:
        return config.LOT_SIZE

    # Use manual balance if provided in scenarios, else use real balance
    balance = config.MANUAL_BALANCE if config.MANUAL_BALANCE > 0 else account.balance
    risk_amount = balance * (risk_percent / 100)

    # Get current price to calculate SL distance in points
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return config.LOT_SIZE
    
    entry_price = tick.ask
    if entry_price <= 0:
        return config.LOT_SIZE
    # Use consistent SL distance calculation, at least 1 tick
    tick_size = info.trade_tick_size if info.trade_tick_size > 0 else 0.01
    sl_dist_price = max(entry_price * config.STOP_LOSS_PCT, tick_size)
    
    # Tick calculations
    tick_size = info.trade_tick_size
    tick_value = info.trade_tick_value
    
    if tick_size == 0 or tick_value == 0 or sl_dist_price == 0:
        # Fallback to simple calculation if properties missing
        lot = risk_amount / 1000
    else:
        # Formula: Lot = RiskAmount / (SLDistance_in_ticks * TickValue)
        # SLDistance_in_ticks = sl_dist_price / tick_size
        lot = risk_amount / ((sl_dist_price / tick_size) * tick_value)

    # Ensure we use at least the minimum lot for aggressive growth on tiny accounts
    valid_lot = get_valid_lot(symbol, lot)
    
    # If the calculated lot is too small but we have balance, default to minimum lot for "flipping"
    if valid_lot < info.volume_min and balance > 0:
        valid_lot = info.volume_min
        
    return valid_lot

def check_limits(current_positions, daily_loss):
    """Validates if new trades are allowed based on risk limits."""
    if len(current_positions) >= config.MAX_TRADES:
        print("Max open trades limit reached.")
        return False
    
    if daily_loss >= config.DAILY_LOSS_LIMIT:
        print("Daily loss limit exceeded.")
        return False
    
    return True

def calculate_sl_tp(symbol, order_type, entry_price, include_sl=False):
    """Calculates stop-loss and take-profit prices. Optionally excludes SL."""
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        return None, None
        
    stops_level_points = getattr(symbol_info, 'trade_stops_level', 0)
    stops_level = stops_level_points * symbol_info.point
    
    # Ensure distance is at least stops_level + small buffer
    min_dist = stops_level + (symbol_info.point * 10)
    
    sl_dist = max(entry_price * config.STOP_LOSS_PCT, min_dist)
    tp_dist = max(entry_price * config.TAKE_PROFIT_PCT, min_dist)
    
    sl = None
    if include_sl:
        if order_type == mt5.ORDER_TYPE_BUY:
            sl = entry_price - sl_dist
        else:
            sl = entry_price + sl_dist
        sl = round(sl, symbol_info.digits)

    if order_type == mt5.ORDER_TYPE_BUY:
        tp = entry_price + tp_dist
    else:
        tp = entry_price - tp_dist
        
    return sl, round(tp, symbol_info.digits)


def check_exit_conditions(position, bb_mid):
    """Checks if a position should be closed based on strategy exit rules."""
    if not config.EXIT_ON_MID_BB:
        return False
        
    # Close Buy if price touches BB Mid from below
    if position.type == mt5.POSITION_TYPE_BUY:
        if position.price_current >= bb_mid:
            return True
    # Close Sell if price touches BB Mid from above
    elif position.type == mt5.POSITION_TYPE_SELL:
        if position.price_current <= bb_mid:
            return True
            
    return False
