import pandas as pd
from load_data import load_sales

df = pd.DataFrame(load_sales())

# Build the column the source file doesn't have
df["SalesAmount"] = df["Quantity"] * df["Net Price"]

# Label every row: does this customer have a name or not?
df["HasName"] = df["Name"].notna()

summary = df.groupby("HasName").agg(
    customers=("CustomerKey", "nunique"),
    records=("SalesAmount", "size"),
    revenue=("SalesAmount", "sum"),
)

# Add percentage columns
for col in ["customers", "records", "revenue"]:
    summary[col + "_pct"] = (summary[col] / summary[col].sum() * 100).round(1)

pd.set_option("display.width", 140)
pd.set_option("display.float_format", lambda v: format(v, ",.1f"))
print(summary)

print()
print("Average revenue per customer")
print("-" * 40)
print((summary["revenue"] / summary["customers"]).round(0))