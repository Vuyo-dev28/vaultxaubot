import pandas as pd

def analyze():
    try:
        df = pd.read_csv('trades_log.csv')
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    with open('analysis_output.txt', 'w') as f:
        f.write("=== OVERALL METRICS ===\n")
        total_trades = len(df)
        total_pnl = df['pnl'].sum()
        wins = df[df['pnl'] > 0]
        losses = df[df['pnl'] < 0]
        
        win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0
        avg_win = wins['pnl'].mean() if not wins.empty else 0
        avg_loss = losses['pnl'].mean() if not losses.empty else 0
        profit_factor = abs(wins['pnl'].sum() / losses['pnl'].sum()) if losses['pnl'].sum() != 0 else float('inf')

        f.write(f"Total Trades: {total_trades}\n")
        f.write(f"Total PnL: ${total_pnl:.2f}\n")
        f.write(f"Win Rate: {win_rate:.2f}% ({len(wins)}W / {len(losses)}L)\n")
        f.write(f"Average Win: ${avg_win:.2f}\n")
        f.write(f"Average Loss: ${avg_loss:.2f}\n")
        
        rr_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        f.write(f"Reward/Risk Ratio (Avg Win / Avg Loss): {rr_ratio:.2f}\n")
        f.write(f"Profit Factor: {profit_factor:.2f}\n\n")

        f.write("=== SUMMARY BY SYMBOL ===\n")
        # Filter symbols with more than 5 trades for meaningful stats
        symbol_counts = df['symbol'].value_counts()
        for sym, count in symbol_counts.items():
            sym_df = df[df['symbol'] == sym]
            sym_pnl = sym_df['pnl'].sum()
            sym_wins = sym_df[sym_df['pnl'] > 0]
            sym_win_rate = len(sym_wins)/count*100
            f.write(f"{sym}: {count} trades | PnL: ${sym_pnl:.2f} | Win Rate: {sym_win_rate:.1f}%\n")

        f.write("\n=== SUMMARY BY DIRECTION ===\n")
        for direction in ['buy', 'sell']:
            dir_df = df[df['direction'] == direction]
            if len(dir_df) > 0:
                dir_pnl = dir_df['pnl'].sum()
                dir_wins = dir_df[dir_df['pnl'] > 0]
                dir_win_rate = len(dir_wins)/len(dir_df)*100
                f.write(f"{direction.upper()}: {len(dir_df)} trades | PnL: ${dir_pnl:.2f} | Win Rate: {dir_win_rate:.1f}%\n")

if __name__ == '__main__':
    analyze()
