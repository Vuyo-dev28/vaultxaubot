import csv
import os

input_file = "trades_log.csv"
output_file = "trades_log_fixed.csv"
header = ["Time", "Symbol", "Type", "Price", "SL", "TP", "Lots", "Profit", "Comment", "Status"]

with open(input_file, 'r', encoding='utf-8') as f_in, \
     open(output_file, 'w', newline='', encoding='utf-8') as f_out:
    
    reader = csv.reader(f_in)
    writer = csv.writer(f_out)
    
    first_row = next(reader) # Skip header or use it
    writer.writerow(header)
    
    for row in reader:
        if not row: continue
        if len(row) == 10:
            writer.writerow(row)
        elif len(row) == 6:
            # Format: Time, Symbol, Type, Price, Profit, Status
            t, s, tp, pr, pnl, stat = row
            # New format: Time, Symbol, Type, Price, SL, TP, Lots, Profit, Comment, Status
            new_row = [t, s, tp, pr, 0, 0, 0, pnl, "", stat]
            writer.writerow(new_row)
        else:
            # Other malformed rows? Just pad them
            new_row = row + [""] * (10 - len(row))
            writer.writerow(new_row[:10])

print("Finished fixing CSV")
