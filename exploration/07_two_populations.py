import pandas as pd
from load_data import load_sales

df = pd.DataFrame(load_sales())

# Collapse to ONE row per customer
cust = df.groupby("CustomerKey").agg(
    code=("Customer Code", "first"),
    name=("Name", "first"),
).reset_index()

cust["HasName"] = cust["name"].notna()

print("=" * 60)
print("SIGNAL 2 - do the two groups use different ID ranges?")
print("=" * 60)
print(cust.groupby("HasName")["CustomerKey"].agg(["count", "min", "max"]))

print()
print("=" * 60)
print("SIGNAL 3 - do they use different Customer Code formats?")
print("=" * 60)
print("no name  :", cust.loc[~cust["HasName"], "code"].head(8).tolist())
print("has name :", cust.loc[cust["HasName"], "code"].head(8).tolist())