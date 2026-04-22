import csv
import os

filename = "trades_log.csv"
header = ["Time", "Symbol", "Type", "Price", "SL", "TP", "Lots", "Profit", "Comment", "Status"]
rows = []

try:
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            first_row = next(reader)
        except StopIteration:
            first_row = []
            
        for row in reader:
            if not row: continue
            if len(row) == 10:
                rows.append(row)
            elif len(row) == 6:
                t, s, tp, pr, pnl, stat = row
                rows.append([t, s, tp, pr, 0, 0, 0, pnl, "", stat])
            else:
                rows.append(row + [""] * (10 - len(row)))

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"Successfully fixed {len(rows)} rows in {filename}")
except Exception as e:
    print(f"Error: {e}")
