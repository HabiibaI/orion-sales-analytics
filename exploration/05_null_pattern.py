import pandas as pd
from load_data import load_sales

df = pd.DataFrame(load_sales())

# For each customer: how many rows, and how many of them have a name?
per_customer = df.groupby("CustomerKey").agg(
    total_rows=("Name", "size"),       # size  = counts every row
    rows_with_name=("Name", "count"),  # count = ignores nulls
)
per_customer["rows_without_name"] = (
    per_customer["total_rows"] - per_customer["rows_with_name"]
)

always = (per_customer["rows_without_name"] == 0).sum()
never = (per_customer["rows_with_name"] == 0).sum()
mixed = (
    (per_customer["rows_with_name"] > 0) & (per_customer["rows_without_name"] > 0)
).sum()

print("Total customers                  :", format(len(per_customer), ","))
print("-" * 55)
print("ALWAYS have a name (every row)   :", format(always, ","))
print("NEVER have a name (no row)       :", format(never, ","))
print("MIXED (some rows yes, some no)   :", format(mixed, ","))