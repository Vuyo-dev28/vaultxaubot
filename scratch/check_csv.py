import pandas as pd
try:
    df = pd.read_csv("trades_log.csv")
    print("Success")
    print(df['Status'].value_counts())
    df_closed = df[df['Status'] == 'CLOSED']
    print(f"Total CLOSED trades: {len(df_closed)}")
except Exception as e:
    print(f"Error: {e}")
