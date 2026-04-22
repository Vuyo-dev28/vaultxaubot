import pandas as pd

def analyze():
    df = pd.read_csv('trades_log.csv')
    # Filter only XAUUSD
    df = df[df['symbol'] == 'XAUUSD']
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')

    # split into first half and second half
    half = len(df) // 2
    first_half = df.iloc[:half]
    second_half = df.iloc[half:]
    
    with open('analysis_output_xau.txt', 'w') as f:
        f.write("=== XAUUSD DEEP DIVE ===\n")
        f.write(f"Total XAUUSD PnL: ${df['pnl'].sum():.2f}\n")
        
        f.write(f"\n--- First Half (Trades 1 to {half}) ---\n")
        f.write(f"PnL: ${first_half['pnl'].sum():.2f}\n")
        f.write(f"Win Rate: {(first_half['pnl'] > 0).mean() * 100:.1f}%\n")
        
        f.write(f"\n--- Second Half (Trades {half+1} to {len(df)}) ---\n")
        f.write(f"PnL: ${second_half['pnl'].sum():.2f}\n")
        f.write(f"Win Rate: {(second_half['pnl'] > 0).mean() * 100:.1f}%\n")
        
        f.write("\n--- Last 50 Trades ---\n")
        last_50 = df.iloc[-50:]
        f.write(f"PnL: ${last_50['pnl'].sum():.2f}\n")
        f.write(f"Win Rate: {(last_50['pnl'] > 0).mean() * 100:.1f}%\n")
        
        f.write("\n--- Break down by Direction ---\n")
        buy_df = df[df['direction'] == 'buy']
        sell_df = df[df['direction'] == 'sell']
        f.write(f"BUY: {len(buy_df)} trades, Win Rate: {(buy_df['pnl'] > 0).mean() * 100:.1f}%, PnL: ${buy_df['pnl'].sum():.2f}\n")
        f.write(f"SELL: {len(sell_df)} trades, Win Rate: {(sell_df['pnl'] > 0).mean() * 100:.1f}%, PnL: ${sell_df['pnl'].sum():.2f}\n")
        
        f.write("\n--- Win/Loss Sizes ---\n")
        wins = df[df['pnl'] > 0]
        losses = df[df['pnl'] < 0]
        f.write(f"Average Win: ${wins['pnl'].mean():.2f}\n")
        f.write(f"Average Loss: ${losses['pnl'].mean():.2f}\n")
        f.write(f"Max Win: ${wins['pnl'].max():.2f}\n")
        f.write(f"Max Loss: ${losses['pnl'].min():.2f}\n")

if __name__ == '__main__':
    analyze()
