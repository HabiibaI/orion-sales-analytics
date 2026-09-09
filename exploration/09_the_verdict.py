import pandas as pd
from load_data import load_sales, load_forecast

df = pd.DataFrame(load_sales())
fc = pd.DataFrame(load_forecast())

# ---- first, meet the forecast file -------------------------------------
print("forecast.json - first rows")
print(fc.head().to_string(index=False))
print()
print("rows:", len(fc),
      "| years:", fc["Year"].unique().tolist(),
      "| countries:", fc["CountryRegion"].nunique(),
      "| brands:", fc["Brand"].nunique())

forecast_2009 = fc["Forecast"].sum()
print("TOTAL FORECAST 2009 : ", format(forecast_2009, ",.0f"))
print()

# ---- build the two columns we need -------------------------------------
df["SalesAmount"] = df["Quantity"] * df["Net Price"]
df["Year"] = df["OrderDate"].str.split("/").str[-1].astype(int)

# ---- the two competing options -----------------------------------------
keep = df.groupby("Year")["SalesAmount"].sum()
dedup = df.drop_duplicates().groupby("Year")["SalesAmount"].sum()

result = pd.DataFrame({"KEEP duplicates": keep, "DELETE duplicates": dedup})
print("REVENUE BY YEAR")
print("-" * 60)
print(result.map(lambda v: format(v, ",.0f")).to_string())
print()

print("2009 vs the forecast of", format(forecast_2009, ",.0f"))
print("-" * 60)
print("  KEEP   :", format(keep[2009], ",.0f"),
      " ->", round(keep[2009] / forecast_2009, 2), "x forecast")
print("  DELETE :", format(dedup[2009], ",.0f"),
      " ->", round(dedup[2009] / forecast_2009, 2), "x forecast")
      