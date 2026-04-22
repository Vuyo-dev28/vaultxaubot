import csv
import os
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd

LOG_FILE = "trades_log.csv"

def log_trade(symbol, entry_price, exit_price, trade_type, pnl, balance, comment=""):
    """Logs trade details to a CSV file."""
    file_exists = os.path.isfile(LOG_FILE)
    
    with open(LOG_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(['Timestamp', 'Symbol', 'Type', 'Entry Price', 'Exit Price', 'P&L', 'Balance', 'Comment'])
        
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            symbol,
            trade_type,
            entry_price,
            exit_price,
            pnl,
            balance,
            comment
        ])

def plot_performance():
    """Generates a performance plot from the CSV log."""
    if not os.path.isfile(LOG_FILE):
        print("No log file found to plot.")
        return

    df = pd.read_csv(LOG_FILE)
    if df.empty:
        return

    df['P&L Cumulative'] = df['P&L'].cumsum()
    
    plt.figure(figsize=(10, 6))
    plt.plot(df['Timestamp'], df['P&L Cumulative'], marker='o', linestyle='-', color='g')
    plt.title('Portfolio Cumulative P&L over Time')
    plt.xlabel('Time')
    plt.ylabel('Cumulative P&L')
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('performance_plot.png')
    print("Performance plot saved as 'performance_plot.png'.")
