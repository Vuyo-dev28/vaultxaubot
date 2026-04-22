import MetaTrader5 as mt5
from datetime import datetime, timedelta

if not mt5.initialize():
    print("MT5 init failed")
    exit()

now = datetime.now()
one_hour_ago = now - timedelta(hours=1)
deals = mt5.history_deals_get(one_hour_ago, now)

print(f"Local time now: {now}")
if deals:
    print(f"Found {len(deals)} deals in the last hour")
    last_deal = deals[-1]
    deal_time = datetime.fromtimestamp(last_deal.time)
    print(f"Last deal time (from timestamp): {deal_time}")
    print(f"Difference: {now - deal_time}")
else:
    print("No deals found in the last hour. Trying 24 hours.")
    one_day_ago = now - timedelta(days=1)
    deals = mt5.history_deals_get(one_day_ago, now)
if deals:
    print(f"Found {len(deals)} deals in the last 24 hours")
    closing_deals = [d for d in deals if d.entry in [mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_INOUT]]
    print(f"Of which {len(closing_deals)} are closing deals.")
    for d in closing_deals:
        print(f"Time: {datetime.fromtimestamp(d.time)}, Symbol: {d.symbol}, Profit: {d.profit}")
else:
        print("No deals found in the last 24 hours.")

mt5.shutdown()
