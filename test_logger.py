import math
from unittest.mock import MagicMock
import sys
import os

# Mock MT5 and Config before importing logger
sys.modules['MetaTrader5'] = MagicMock()
sys.modules['config'] = MagicMock()
sys.modules['matplotlib.pyplot'] = MagicMock()
sys.modules['pandas'] = MagicMock()

import logger

def test_logger():
    print("Testing logger.log_trade...")
    
    # Path where script is run
    log_file = "test_trades_log.csv"
    logger.LOG_FILE = log_file
    
    if os.path.exists(log_file):
        os.remove(log_file)
        
    # Log an entry
    logger.log_trade("XAUUSD", 4700.0, 0, "buy", 0, 10000.0, "Entry TEST")
    
    # Log an exit
    logger.log_trade("XAUUSD", 4700.0, 4710.0, "exit", 10.0, 10010.0, "Exit TEST")
    
    # Read file and verify columns
    with open(log_file, "r") as f:
        lines = f.readlines()
        
    for i, line in enumerate(lines):
        cols = line.strip().split(",")
        print(f"Line {i+1} columns: {len(cols)} - {cols}")
        if i == 0:
            assert len(cols) == 8
            assert "Balance" in cols
        else:
            assert len(cols) == 8
            
    print("All logger tests passed!")
    os.remove(log_file)

if __name__ == "__main__":
    test_logger()
