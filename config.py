import os
from dotenv import load_dotenv
import MetaTrader5 as mt5

# Load environment variables
load_dotenv()

# MT5 Credentials
MT5_ACCOUNT_STR = os.getenv("MT5_ACCOUNT", "0")
try:
    MT5_ACCOUNT = int(MT5_ACCOUNT_STR)
except ValueError:
    print(f"Error: MT5_ACCOUNT (currently '{MT5_ACCOUNT_STR}') in your .env file must be a numeric account number.")
    MT5_ACCOUNT = 0

MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "")
MT5_PATH = os.getenv("MT5_PATH", "")

# Strategy Parameters
SYMBOLS_STR = os.getenv("SYMBOLS", "XAUUSD,EURUSD")
# Strip outer quotes if they exist and split
SYMBOLS_STR = SYMBOLS_STR.strip().strip('"').strip("'")
SYMBOLS = [s.strip() for s in SYMBOLS_STR.split(",") if s.strip()]

TIMEFRAME_STR = os.getenv("TIMEFRAME", "M1")
# Map timeframe string to MT5 constant
TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "H1": mt5.TIMEFRAME_H1
}
TIMEFRAME = TIMEFRAME_MAP.get(TIMEFRAME_STR, mt5.TIMEFRAME_M1)
BB_PERIOD = int(os.getenv("BB_PERIOD", "20"))
BB_STD = float(os.getenv("BB_STD", "1.5"))
MOMENTUM_PERIOD = int(os.getenv("MOMENTUM_PERIOD", "3"))

# Risk Management
LOT_SIZE = float(os.getenv("LOT_SIZE", "0.01"))
RISK_PERCENT = float(os.getenv("RISK_PERCENT", "1.0"))
MANUAL_BALANCE = float(os.getenv("MANUAL_BALANCE", "0.0")) # For scenarios
MAX_TRADES = int(os.getenv("MAX_TRADES", "20"))
DAILY_LOSS_LIMIT = float(os.getenv("DAILY_LOSS_LIMIT", "50.0"))
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "0.002"))
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "0.002"))
TRAILING_STOP_PCT = float(os.getenv("TRAILING_STOP_PCT", "0.001"))
EXIT_ON_MID_BB = os.getenv("EXIT_ON_MID_BB", "True").lower() == "true"
MAGIC_NUMBER = int(os.getenv("MAGIC_NUMBER", "123456"))

# Mapper for MetaTrader period constants
TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
}

TIMEFRAME = TIMEFRAME_MAP.get(TIMEFRAME_STR, mt5.TIMEFRAME_M1)
