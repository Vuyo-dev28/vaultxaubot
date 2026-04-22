import pandas as pd
from datetime import datetime

LOG_FILE = "trades_log.csv"

def update_analysis_reports():
    try:
        df = pd.read_csv(LOG_FILE, encoding='utf-8')
        df_closed = df[df['Status'] == 'CLOSED']
        
        if df_closed.empty:
            print("No closed trades found")
            return

        total_trades = len(df_closed)
        total_pnl = df_closed['Profit'].sum()
        wins = df_closed[df_closed['Profit'] > 0]
        win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
        
        symbol_stats = []
        for symbol, group in df_closed.groupby('Symbol'):
            s_pnl = group['Profit'].sum()
            s_trades = len(group)
            s_wins = len(group[group['Profit'] > 0])
            s_wr = (s_wins / s_trades * 100) if s_trades > 0 else 0
            symbol_stats.append({
                "Symbol": symbol,
                "Trades": s_trades,
                "PnL": round(s_pnl, 2),
                "WinRate": round(s_wr, 1)
            })

        pd.DataFrame(symbol_stats).to_csv("analysis_results.csv", index=False, encoding='utf-8')
        print(f"Updated analysis_results.csv with {total_trades} trades")

        with open("analysis_results.txt", "w", encoding='utf-8') as f:
            f.write("=== TRADING BOT ANALYSIS ===\n")
            f.write(f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Trades: {total_trades}\n")
            f.write(f"Total Profit/Loss: ${total_pnl:.2f}\n")
            f.write(f"Overall Win Rate: {win_rate:.2f}%\n\n")
            f.write("=== PERFORMANCE BY SYMBOL ===\n")
            for s in symbol_stats:
                f.write(f"{s['Symbol']}: {s['Trades']} trades | PnL: ${s['PnL']:.2f} | WR: {s['WinRate']}%\n")

    except Exception as e:
        print(f"[ERROR] Could not update analysis: {e}")

if __name__ == "__main__":
    update_analysis_reports()
