import pandas as pd
import sys

def analyze():
    try:
        df = pd.read_csv('trades_log.csv')
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    print("=== OVERALL METRICS ===")
    total_trades = len(df)
    total_pnl = df['pnl'].sum()
    wins = df[df['pnl'] > 0]
    losses = df[df['pnl'] < 0]
    
    win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0
    avg_win = wins['pnl'].mean() if not wins.empty else 0
    avg_loss = losses['pnl'].mean() if not losses.empty else 0
    profit_factor = abs(wins['pnl'].sum() / losses['pnl'].sum()) if losses['pnl'].sum() != 0 else float('inf')

    print(f"Total Trades: {total_trades}")
    print(f"Total PnL: ${total_pnl:.2f}")
    print(f"Win Rate: {win_rate:.2f}% ({len(wins)}W / {len(losses)}L)")
    print(f"Average Win: ${avg_win:.2f}")
    print(f"Average Loss: ${avg_loss:.2f}")
    print(f"Reward/Risk Ratio (Avg Win / Avg Loss): {abs(avg_win / avg_loss):.2f}" if avg_loss != 0 else "N/A")
    print(f"Profit Factor: {profit_factor:.2f}")

    print("\n=== PERFORMANCE BY SYMBOL ===")
    symbol_group = df.groupby('symbol').agg(
        trades=('pnl', 'count'),
        total_pnl=('pnl', 'sum'),
        win_rate=('pnl', lambda x: (x > 0).mean() * 100)
    ).sort_values('total_pnl', ascending=False)
    
    print(symbol_group.to_string(formatters={'total_pnl': '${:.2f}'.format, 'win_rate': '{:.1f}%'.format}))

    print("\n=== PERFORMANCE BY DIRECTION ===")
    dir_group = df.groupby('direction').agg(
        trades=('pnl', 'count'),
        total_pnl=('pnl', 'sum'),
        win_rate=('pnl', lambda x: (x > 0).mean() * 100)
    ).sort_values('total_pnl', ascending=False)
    print(dir_group.to_string(formatters={'total_pnl': '${:.2f}'.format, 'win_rate': '{:.1f}%'.format}))

if __name__ == '__main__':
    analyze()
