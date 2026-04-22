import pandas as pd
import sys
import io

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

df = pd.read_csv("trades_log.csv")
closed = df[df['Status'] == 'CLOSED']
print(closed.tail())
