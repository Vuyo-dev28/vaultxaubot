import MetaTrader5 as mt5

def check_symbol(symbol):
    if not mt5.initialize():
        print("Initialize failed")
        return
    
    info = mt5.symbol_info(symbol)
    if info:
        print(f"Symbol: {symbol}")
        print(f"  Digits: {info.digits}")
        print(f"  Point: {info.point}")
        print(f"  Stop Level: {info.trade_stops_level}")
        print(f"  Volume Min: {info.volume_min}")
        print(f"  Volume Step: {info.volume_step}")
        
    mt5.shutdown()

if __name__ == "__main__":
    check_symbol("Volatility 100 Index")
    print("-" * 20)
    check_symbol("XAUUSD")
