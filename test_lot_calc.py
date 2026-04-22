import math
from unittest.mock import MagicMock
import sys
import os

# Mock MT5 and Config before importing risk_manager
sys.modules['MetaTrader5'] = MagicMock()
sys.modules['config'] = MagicMock()

import MetaTrader5 as mt5
import risk_manager

def test_get_valid_lot():
    print("Testing get_valid_lot...")
    
    # Mock symbol info
    mock_info = MagicMock()
    mock_info.volume_min = 0.1
    mock_info.volume_max = 100.0
    mock_info.volume_step = 0.1
    mt5.symbol_info.return_value = mock_info

    # Case 1: Below minimum
    res = risk_manager.get_valid_lot("SYM", 0.05)
    print(f"Below min (0.1): {res} (Exp: 0.1)")
    assert res == 0.1

    # Case 2: Above maximum
    res = risk_manager.get_valid_lot("SYM", 150.0)
    print(f"Above max (100.0): {res} (Exp: 100.0)")
    assert res == 100.0

    # Case 3: Between steps
    res = risk_manager.get_valid_lot("SYM", 0.24)
    print(f"Between steps (0.24, step 0.1): {res} (Exp: 0.2)")
    assert res == 0.2

    # Case 4: Different step (e.g. 0.01)
    mock_info.volume_min = 0.01
    mock_info.volume_step = 0.01
    res = risk_manager.get_valid_lot("SYM", 0.015)
    print(f"Step 0.01 (0.015): {res} (Exp: 0.02)")
    assert res == 0.02
    
    print("All tests passed!")

if __name__ == "__main__":
    test_get_valid_lot()
